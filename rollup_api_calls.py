#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aggregate old tbl_api_calls rows into tbl_api_calls_daily.

Tier 1 (30+ days old): individual rows → per-user, per-endpoint, per-day summary
Tier 2 (365+ days old): per-user summaries → endpoint-only totals (user_id = NULL)
"""
import time

from lib.db import MalshareDB

THIRTY_DAYS = 30 * 86400
ONE_YEAR = 365 * 86400


def rollup_to_daily(db, cutoff_ts):
    """Tier 1: aggregate individual calls older than cutoff into daily summaries."""
    cur = db._conn.cursor()

    # Insert aggregated rows into tbl_api_calls_daily
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

    # Delete the original rows
    cur.execute("DELETE FROM tbl_api_calls WHERE ts < ?", (cutoff_ts,))
    deleted = cur.rowcount

    db._conn.commit()
    print(f"[ROLLUP] Tier 1: aggregated {deleted} individual rows into {aggregated} daily summaries")


def collapse_old_daily(db, cutoff_ts):
    """Tier 2: collapse per-user daily rows older than cutoff into endpoint-only totals."""
    cur = db._conn.cursor()

    cutoff_date = time.strftime("%Y-%m-%d", time.gmtime(cutoff_ts))

    # Aggregate per-user rows into endpoint-only totals
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

    # Delete the per-user rows that were just collapsed
    cur.execute(
        "DELETE FROM tbl_api_calls_daily WHERE day < ? AND user_id IS NOT NULL",
        (cutoff_date,),
    )
    deleted = cur.rowcount

    db._conn.commit()
    print(f"[ROLLUP] Tier 2: collapsed {deleted} per-user rows into {aggregated} endpoint-only summaries")


def main():
    db = MalshareDB()
    try:
        now = int(time.time())
        rollup_to_daily(db, now - THIRTY_DAYS)
        collapse_old_daily(db, now - ONE_YEAR)
    finally:
        db.close()


if __name__ == "__main__":
    main()
