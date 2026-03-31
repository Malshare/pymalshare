#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

from lib.db import MalshareDB

NINETY_DAYS = 90 * 86400


def main():
    db = MalshareDB()
    try:
        cutoff = int(time.time()) - NINETY_DAYS
        cur = db._conn.cursor()
        cur.execute(
            "UPDATE tbl_users SET r_ip_address = '' WHERE last_login IS NOT NULL AND last_login < ? AND r_ip_address != ''",
            (cutoff,),
        )
        db._conn.commit()
        print(f"[CLEANUP] Cleared r_ip_address for {cur.rowcount} inactive users")
    finally:
        db.close()


if __name__ == "__main__":
    main()
