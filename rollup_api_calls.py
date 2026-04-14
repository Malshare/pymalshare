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


def main():
    db = MalshareDB()
    try:
        now = int(time.time())

        deleted, aggregated = db.rollup_api_calls_to_daily(now - THIRTY_DAYS)
        print(f"[ROLLUP] Tier 1: aggregated {deleted} individual rows into {aggregated} daily summaries")

        deleted, aggregated = db.collapse_old_daily_api_calls(now - ONE_YEAR)
        print(f"[ROLLUP] Tier 2: collapsed {deleted} per-user rows into {aggregated} endpoint-only summaries")
    finally:
        db.close()


if __name__ == "__main__":
    main()
