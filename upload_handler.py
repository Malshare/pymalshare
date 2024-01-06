#!/usr/bin/python
#Author: Silas


import time
import lib.pymalshare as MalShare

# Load vars from .env file
from dotenv import load_dotenv
load_dotenv()


def ParseNewFiles():
    ms = MalShare.MalShare()
    pending = ms.get_pending()
    missing = 0

    if len(pending) > 0:
        print(f"  [Upload Handler] Total Waiting {pending}")

    # Loop over each new sample and process additional details
    for pSample in pending:
        try:
            ms.process_upload(pSample[0], pSample[2])
        except Exception as e:
            print(f"pymalshare Exception: {e}")

    ms.db_close()
    print("Missing: %s" % missing)


def main():
    while True:
        try:
            ParseNewFiles()
            time.sleep(10)
        except Exception as e:
            print(f"-- top main Error: {e}")


if __name__ == "__main__":
    main()
    # ParseNewFiles()