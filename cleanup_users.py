#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

from lib.db import MalshareDB

NINETY_DAYS = 90 * 86400


def main():
    db = MalshareDB()
    try:
        cutoff = int(time.time()) - NINETY_DAYS
        count = db.cleanup_inactive_users(cutoff)
        print(f"[CLEANUP] Cleared data for {count} inactive users")
    finally:
        db.close()


if __name__ == "__main__":
    main()
