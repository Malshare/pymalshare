#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
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
