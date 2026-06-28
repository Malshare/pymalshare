#!/usr/bin/env python3
"""One-time backfill of tbl_samples.size from Wasabi object sizes.

Sweeps the whole bucket with ListObjectsV2 (Size is returned per object, no
HEAD requests), derives the sha256 from each key, and batch-updates rows whose
size is still NULL. Idempotent and resumable: re-running only fills gaps.
"""
import sys

from lib.storage import Storage
from lib.db import MalshareDB

BATCH = 500


def sha256_from_key(key):
    """Extract the sha256 from an S3 key shaped 'aaa/bbb/ccc/<sha256>'.

    Returns the lowercased 64-hex sha256, or None if the key doesn't match.
    """
    candidate = key.rsplit("/", 1)[-1].strip().lower()
    if len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate):
        return candidate
    return None


def _flush(cur, conn, batch):
    updated = 0
    for size, sha in batch:
        cur.execute(
            "UPDATE tbl_samples SET size = ? WHERE sha256 = ? AND size IS NULL",
            (size, sha),
        )
        updated += cur.rowcount
    conn.commit()
    return updated


def main():
    storage = Storage()
    db = MalshareDB()
    conn = db._conn
    cur = conn.cursor()

    paginator = storage.s3.get_paginator("list_objects_v2")
    pending = []
    total_seen = 0
    total_updated = 0

    for page in paginator.paginate(Bucket=storage.bucket):
        for obj in page.get("Contents", []):
            total_seen += 1
            sha = sha256_from_key(obj["Key"])
            if sha is None:
                continue
            pending.append((obj["Size"], sha))
            if len(pending) >= BATCH:
                total_updated += _flush(cur, conn, pending)
                pending.clear()
                print(f"  seen={total_seen} updated={total_updated}", flush=True)

    if pending:
        total_updated += _flush(cur, conn, pending)

    cur.close()
    db.close()
    print(f"Done. objects seen={total_seen}, rows updated={total_updated}")


if __name__ == "__main__":
    sys.exit(main())
