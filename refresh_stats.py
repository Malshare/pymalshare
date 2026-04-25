#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Precompute expensive sample statistics into tbl_stats_cache.

Runs hourly as a Docker service. The PHP stats page reads from the cache
table instead of running full table scans on every page load.
"""

from lib.db import MalshareDB


def main():
    db = MalshareDB()
    try:
        count = db.refresh_stats_cache()
        print(f"[STATS] Refreshed {count} cache entries")
    finally:
        db.close()


if __name__ == "__main__":
    main()
