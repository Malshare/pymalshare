#!/usr/bin/env python3
import time
from datetime import datetime

import requests

import lib.pymalshare as MalShare

SOCKS_PROXY = "socks5h://127.0.0.1:9050"
PROXIES = {"http": SOCKS_PROXY, "https": SOCKS_PROXY}
HEADERS = {"User-Agent": "Mozilla/5.0 MalShare Crawler"}
TIMEOUT = 30
MAX_SIZE = 40_000_000


def process_tasks():
    ms = MalShare.MalShare()
    task = ms.get_url_pending()

    if task is None:
        ms.db_close()
        time.sleep(20)
        return

    t_id, t_url, t_created, t_started, t_finished, t_fetchall = task
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[url_task] Processing task {t_id}: {t_url}")
    ms.db_url_update(t_id, "started_at", now)

    if "malshare" in t_url:
        print(f"[url_task] Skipping self-referential URL: {t_url}")
        ms.db_url_update(t_id, "finished_at", now)
        ms.db_close()
        return

    try:
        resp = requests.get(t_url, proxies=PROXIES, headers=HEADERS, timeout=TIMEOUT)
        if not resp.ok:
            print(f"[url_task] HTTP {resp.status_code} for {t_url}")
        elif len(resp.content) > MAX_SIZE:
            print(f"[url_task] File too large ({len(resp.content)} bytes): {t_url}")
        else:
            print(f"[url_task] Downloaded {len(resp.content)} bytes from {t_url}")
            ms.submit_buffer(resp.content, t_url)
    except Exception as e:
        print(f"[url_task] Error downloading {t_url}: {e}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ms.db_url_update(t_id, "finished_at", now)
    ms.db_close()


def main():
    while True:
        try:
            process_tasks()
            time.sleep(5)
        except Exception as e:
            print(f"[url_task] Top-level error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
