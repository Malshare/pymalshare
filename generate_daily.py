#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import os
import shutil
from datetime import datetime, timedelta

from lib.db import MalshareDB

OUTPUT_DIR = os.getenv("OUTPUT_DIR")


def main():
    assert OUTPUT_DIR
    assert os.path.exists(OUTPUT_DIR)
    assert os.path.isdir(OUTPUT_DIR)
    now = datetime.now()
    last_midnight = datetime(year=now.year, month=now.month, day=now.day)
    db = MalshareDB()
    latest_all = latest_md5 = latest_sha1 = latest_sha256 = None
    try:
        current_date = db.first_date()
        while current_date < last_midnight:
            date_string = current_date.strftime("%Y-%m-%d")
            next_date = current_date + timedelta(days=1)

            date_path = os.path.join(OUTPUT_DIR, date_string)
            all_file_name = F"malshare_fileList.{date_string}.all.txt"
            md5_file_name = F"malshare_fileList.{date_string}.txt"
            sha1_file_name = F"malshare_fileList.{date_string}.sha1.txt"
            sha256_file_name = F"malshare_fileList.{date_string}.sha256.txt"

            all_path = os.path.join(date_path, all_file_name)
            md5_path = os.path.join(date_path, md5_file_name)
            sha1_path = os.path.join(date_path, sha1_file_name)
            sha256_path = os.path.join(date_path, sha256_file_name)
            if all(os.path.exists(p) for p in [all_path, md5_path, sha1_path, sha256_path]):
                latest_all = all_path
                latest_md5 = md5_path
                latest_sha1 = sha1_path
                latest_sha256 = sha256_path
                current_date = next_date
                continue

            all_h = hashlib.sha256()
            md5_h = hashlib.sha256()
            sha1_h = hashlib.sha256()
            sha256_h = hashlib.sha256()

            all_fp = md5_fp = sha1_fp = sha256_fp = None
            for row in db.db_added_between(current_date, next_date):
                if all_fp is None:
                    try:
                        os.mkdir(date_path)
                    except FileExistsError:
                        pass
                    all_fp = open(all_path, "w")
                    md5_fp = open(md5_path, "w")
                    sha1_fp = open(sha1_path, "w")
                    sha256_fp = open(sha256_path, "w")
                for line, fp, h in (
                        (F"{row['md5']}\t{row['sha1']}\t{row['sha256']}\n", all_fp, all_h),
                        (F"{row['md5']}\n", md5_fp, md5_h),
                        (F"{row['sha1']}\n", sha1_fp, sha1_h),
                        (F"{row['sha256']}\n", sha256_fp, sha256_h),
                ):
                    h.update(line.encode("utf-8"))
                    fp.write(line)

            for fp in (all_fp, md5_fp, sha1_fp, sha256_fp):
                if fp is not None:
                    fp.close()

            if all_fp is not None:
                with open(os.path.join(date_path, "hashes.txt"), "w") as fp:
                    fp.write(F"{all_h.hexdigest()}  {all_file_name}\n")
                    fp.write(F"{md5_h.hexdigest()}  {md5_file_name}\n")
                    fp.write(F"{sha1_h.hexdigest()}  {sha1_file_name}\n")
                    fp.write(F"{sha256_h.hexdigest()}  {sha256_file_name}\n")
                latest_all = all_path
                latest_md5 = md5_path
                latest_sha1 = sha1_path
                latest_sha256 = sha256_path

            current_date = next_date

    finally:
        db.close()
        if latest_all:
            shutil.copy(latest_all, os.path.join(OUTPUT_DIR, "malshare.current.all.txt"))
            shutil.copy(latest_sha256, os.path.join(OUTPUT_DIR, "malshare.current.sha256.txt"))
            shutil.copy(latest_sha1, os.path.join(OUTPUT_DIR, "malshare.current.sha1.txt"))
            shutil.copy(latest_md5, os.path.join(OUTPUT_DIR, "malshare.current.txt"))


if __name__ == '__main__':
    main()
