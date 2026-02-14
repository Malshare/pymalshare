#!/usr/bin/env python3

import json
import os

import magic
import pymysql
import ssdeep  # apt install ssdeep build-essential libffi-dev libfuzzy-dev && pip install ssdeep
import yara

from lib.storage import Storage


class MalShare(object):
    def __init__(self):
        self.yara_rules = self.yara_setup()
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

    def db_update(self, r_id, r_ssdeep, r_type, r_yara):
        print("  [Mark Processed]")
        insert_sql = """UPDATE tbl_samples set ssdeep = %s, ftype = %s, yara = %s, pending=0 WHERE id = %s"""
        sql_cur = self.sql_con.cursor()
        sql_cur.execute(insert_sql, (r_ssdeep, r_type, json.dumps(r_yara), r_id))
        self.db_submit_yara(r_id, r_yara.get("yara", []))
        return r_id

    def db_submit_yara(self, sample_id, yara_rule_names):
        for rule_name in yara_rule_names:
            yara_id = self.db_ensure_yara_rule_name(rule_name)
            sql = "SELECT id FROM tbl_matches WHERE (yara_id = %s) AND (sample_id = %s)"
            cur = self.sql_con.cursor()
            cur.execute(sql, (yara_id, sample_id))
            row = cur.fetchone()
            if row is None:
                sql = "INSERT INTO tbl_matches (yara_id, sample_id) VALUES(%s, %s)"
                cur = self.sql_con.cursor()
                cur.execute(sql, (yara_id, sample_id))

    def db_ensure_yara_rule_name(self, rule_name):
        sql = "SELECT id FROM tbl_yara WHERE (rule_name = %s)"
        cur = self.sql_con.cursor()
        cur.execute(sql, (rule_name,))
        row = cur.fetchone()
        if row is None:
            sql = "INSERT INTO tbl_yara (rule_name) VALUES (%s)"
            cur = self.sql_con.cursor()
            cur.execute(sql, (rule_name,))
            return cur.lastrowid
        else:
            return row[0]

    @staticmethod
    def yara_setup():
        ret = {}
        rule_config = {
            "CuckooSandbox": "./Yaggy/rules/CuckooSandbox",
            "YRP": "./Yaggy/rules/YRP",
            "FlorianRoth": "./Yaggy/rules/FlorianRoth",
            "KevTheHermit": "./Yaggy/rules/KevTheHermit",
            "BAMFDetect": "./Yaggy/rules/BamfDetect",
        }
        for key in rule_config.keys():
            try:
                ret[key] = yara.compile(rule_config[key])
            except Exception as e:
                print(f"[YARA] Error: {e}")
        return ret

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

        print("  [M - Upload Handler] Starting Yara Scan")
        detects = {"yara": []}
        for ySet in self.yara_rules:
            try:
                matches = self.yara_rules[ySet].match(data=fdata, timeout=30)
                for x in matches:
                    detects["yara"].append(ySet + "/" + x.rule)
            except Exception as e:
                print("  [Submit] Exception Scanning {ySet} - {e}")

        print("  [Submit] Update with file type %s with [%s]" % (filetype, ",".join(detects["yara"])))
        rid = self.db_update(r_id, r_ssdeep, filetype, detects)
        # if rid is not None:
        #     Unpacker(url_dl, rid)

        return
