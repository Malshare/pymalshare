#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime

import mariadb


class MalshareDB:
    def __init__(self):
        malshare_db_host = os.getenv("MALSHARE_DB_HOST")
        malshare_db = os.getenv("MALSHARE_DB_DATABASE", "malshare_db")
        malshare_user = os.getenv("MALSHARE_DB_USER")
        malshare_password = os.getenv("MALSHARE_DB_PASS")
        assert malshare_db_host
        assert malshare_user
        assert malshare_password
        self._conn = mariadb.connect(
            user=malshare_user,
            password=malshare_password,
            host=malshare_db_host,
            port=3306,
            database=malshare_db,
        )

    def close(self):
        self._conn.close()

    def db_added_between(self, start: datetime, end: datetime):
        sql_cur = self._conn.cursor()

        sql = "SELECT md5, sha1, sha256 FROM malshare_db.tbl_samples WHERE added >= ? AND added < ?"
        sql_cur.execute(sql, (int(start.timestamp()), int(end.timestamp())))

        for row in sql_cur:
            yield {"md5": row[0], "sha1": row[1], "sha256": row[2]}

    def first_date(self) -> datetime:
        sql_cur = self._conn.cursor()
        sql = "SELECT MIN(added) FROM malshare_db.tbl_samples"
        sql_cur.execute(sql)
        row = sql_cur.fetchone()

        return datetime.fromtimestamp(row[0])

    def cleanup_inactive_users(self, cutoff_ts):
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE tbl_users SET last_login_ip_address = '' WHERE last_login IS NOT NULL AND last_login < ? AND last_login_ip_address != ''",
            (cutoff_ts,),
        )
        self._conn.commit()
        return cur.rowcount

    def rollup_api_calls_to_daily(self, cutoff_ts):
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO tbl_api_calls_daily (day, endpoint, user_id, call_count)
            SELECT DATE(FROM_UNIXTIME(ts)), endpoint, user_id, COUNT(*)
            FROM tbl_api_calls
            WHERE ts < ?
            GROUP BY DATE(FROM_UNIXTIME(ts)), endpoint, user_id
            ON DUPLICATE KEY UPDATE call_count = call_count + VALUES(call_count)
            """,
            (cutoff_ts,),
        )
        aggregated = cur.rowcount
        cur.execute("DELETE FROM tbl_api_calls WHERE ts < ?", (cutoff_ts,))
        deleted = cur.rowcount
        self._conn.commit()
        return deleted, aggregated

    def collapse_old_daily_api_calls(self, cutoff_ts):
        cur = self._conn.cursor()
        cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff_ts))
        cur.execute(
            """
            INSERT INTO tbl_api_calls_daily (day, endpoint, user_id, call_count)
            SELECT day, endpoint, NULL, SUM(call_count)
            FROM tbl_api_calls_daily
            WHERE day < ? AND user_id IS NOT NULL
            GROUP BY day, endpoint
            ON DUPLICATE KEY UPDATE call_count = call_count + VALUES(call_count)
            """,
            (cutoff_date,),
        )
        aggregated = cur.rowcount
        cur.execute(
            "DELETE FROM tbl_api_calls_daily WHERE day < ? AND user_id IS NOT NULL",
            (cutoff_date,),
        )
        deleted = cur.rowcount
        self._conn.commit()
        return deleted, aggregated
