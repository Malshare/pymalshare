#!/usr/bin/env python3
import os

import magic
import pymysql
import ssdeep  # apt install ssdeep build-essential libffi-dev libfuzzy-dev && pip install ssdeep

from lib.storage import Storage


class MalShare(object):
    def __init__(self):
        self.sql_con = self.db_start()
        self.sample_partner_id = None
        self.storage = Storage()

    @staticmethod
    def db_start():
        try:
            malshare_db_host = os.getenv("MALSHARE_DB_HOST")
            malshare_db = os.getenv("MALSHARE_DB_DATABASE")
            print(f"[MYSQL] Connecting to {malshare_db_host}/{malshare_db}")
            sql_con = pymysql.connect(
                host=malshare_db_host,
                user=os.getenv("MALSHARE_DB_USER"),
                password=os.getenv("MALSHARE_DB_PASS"),
                db=malshare_db,
            )
            sql_con.autocommit(True)
            return sql_con
        except Exception as e:
            print(f"[MYSQL] Error: {e}")

    def db_ping(self):
        if self.sql_con is None:
            print("[MySQL] Reconnecting..")
            self.db_start()
        else:
            print(self.sql_con.ping(True))

    def db_close(self):
        self.sql_con.close()

    def get_pending(self):
        sql_query = """SELECT id, md5, sha256 from tbl_samples where pending = 1"""
        sql_ncur = self.sql_con.cursor()
        sql_ncur.execute(sql_query)
        return sql_ncur.fetchall()

    def db_url_update(self, r_id, r_time_key, r_time_value):
        insert_sql = "UPDATE tbl_url_download_tasks set " + r_time_key + " = %s WHERE id = %s"
        sql_cur = self.sql_con.cursor()
        sql_cur.execute(insert_sql, (r_time_value, r_id))
        return r_id

    def get_url_pending(self):
        sql_query = """
            SELECT id, url, created_at, started_at, finished_at, fetchall 
            FROM tbl_url_download_tasks
            WHERE started_at = '1970-01-01 01:00:01'
        """

        sql_cur = self.sql_con.cursor()
        sql_cur.execute(sql_query)
        return sql_cur.fetchone()

    def get_id(self, rhash):
        sql_query = """SELECT id from tbl_samples where md5 = %s"""
        sql_cur = self.sql_con.cursor()
        sql_cur.execute(sql_query, (rhash,))
        return sql_cur.fetchone()[0]

    def db_update(self, r_id, r_ssdeep, r_type):
        print("  [Mark Processed]")
        insert_sql = """UPDATE tbl_samples set ssdeep = %s, ftype = %s, pending=0 WHERE id = %s"""
        sql_cur = self.sql_con.cursor()
        sql_cur.execute(insert_sql, (r_ssdeep, r_type, r_id))
        return r_id

    def process_upload(self, r_id, sha256):
        _, fdata = self.storage.get_sampleobj(f"{sha256[0:3]}/{sha256[3:6]}/{sha256[6:9]}/{sha256}")

        if not _:
            print(f"[process_upload] Unable to download sample {sha256}")
            return False

        try:
            filetype = str(magic.from_buffer(fdata)).split(" ")[0]
        except Exception as e:
            print(f"[Magic Exception] {e}")
            filetype = ""

        r_ssdeep = ssdeep.hash(fdata)
        if "empty" == filetype:
            return

        print(f"  [Submit] Update with file type {filetype}")
        self.db_update(r_id, r_ssdeep, filetype)

        return
