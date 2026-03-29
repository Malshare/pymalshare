# MalShare pymalshare

Python backend for MalShare — handles sample processing and export generation that PHP can't do efficiently.

## Tech Stack

- Python 3.14 (generate_daily) / 3.10 (upload_handler)
- MariaDB (`mariadb` package) for generate_daily, `pymysql` for upload_handler
- boto3 for S3/Wasabi storage
- yara-python, python-magic, ssdeep for sample analysis
- Black (120 char lines) + isort for formatting

## Project Structure

```
generate_daily.py              # Daily hash export generator (run-once job)
upload_handler.py              # Long-running daemon for sample processing
lib/
  db.py                        # MariaDB database layer (queries tbl_samples)
  storage.py                   # S3/Wasabi abstraction (boto3)
  pymalshare.py                # Core class: YARA setup, sample processing, DB updates
docker/
  Docker.generate_daily        # Container for daily export (lightweight, mariadb only)
  Dockerfile.upload_handler    # Container for upload handler (heavier, yara/ssdeep/magic)
Makefile                       # Build and run shortcuts
requirements.txt               # All Python dependencies
pyproject.toml                 # Black/isort config
```

## Components

### generate_daily.py
Generates daily hash export files for public/partner consumption:
- Queries DB for all samples from the first sample date to yesterday
- Per day, creates 4 files: `.all.txt` (tab-separated MD5/SHA1/SHA256), `.txt` (MD5), `.sha1.txt`, `.sha256.txt`
- Creates `hashes.txt` with SHA256 checksums of the export files
- Copies the most recent day's files to the output root as `malshare.current.*`
- Skips dates that already have all 4 files (idempotent)
- Output dir set via `OUTPUT_DIR` env var

### upload_handler.py
Long-running daemon that processes pending malware samples:
- Polls DB every 10 seconds for pending samples
- Downloads binary from S3, detects file type (libmagic), computes ssdeep hash
- Runs YARA rules (5 rulesets from `/Yaggy/rules/`, 30s timeout each)
- Updates DB with results and marks sample as processed

## Environment Variables

### Database (both scripts)
- `MALSHARE_DB_HOST`, `MALSHARE_DB_USER`, `MALSHARE_DB_PASS`
- `MALSHARE_DB_DATABASE` (optional, default: `malshare_db`)

### S3 Storage (upload_handler only)
- `WASABI_BUCKET`, `WASABI_KEY`, `WASABI_SECRET`, `WASABI_ENDPOINT`

### Output (generate_daily only)
- `OUTPUT_DIR` — directory for generated hash lists

## YARA Rules

Loaded from `/Yaggy/rules/` with 5 hardcoded rule sets in `lib/pymalshare.py`:
- CuckooSandbox, YRP, FlorianRoth, KevTheHermit, BamfDetect

The `Yaggy` directory must be available at build time for the upload_handler container.

## Building

```bash
# generate_daily
make build-generate-daily

# upload_handler
make build
```

The Makefile uses `--env-file .env` for credentials. Create a `.env` file with the DB and S3 variables listed above. Do not commit `.env`.

## Deployment

The `generate-daily` service runs in the conf repo's `docker-compose.yml` alongside the frontend. It uses a sleep loop to run once daily. The output is stored in a `daily_exports` Docker named volume.

The upload_handler runs as a separate daemonized container (`docker run -d`).

Both images should eventually be built and pushed to GHCR via CI, following the same pattern as Frontend and Offline (build → push → trigger conf dispatch).

## Database

Queries `malshare_db.tbl_samples` primarily:
- `md5`, `sha1`, `sha256` — sample hashes
- `added` — Unix timestamp, used for date range queries in generate_daily
- `pending` — flag for upload_handler to pick up unprocessed samples
- `ssdeep`, `ftype`, `yara` — populated by upload_handler after processing

Also uses `tbl_yara` (rule catalog) and `tbl_matches` (sample-to-rule mapping).

## Known Issues / Notes

- `lib/db.py` hardcodes port 3306 — no `MALSHARE_DB_PORT` support
- `upload_handler.py` uses `pymysql` while `generate_daily.py` uses `mariadb` — two different DB drivers
- The Makefile `run-generate-daily` target uses `--env-file .env` — ensure `.env` exists locally

## Maintenance

Keep this CLAUDE.md up-to-date when adding features, fixing bugs, or learning new things about the project. Also update `CLAUDE.md` in the `Malshare/conf` repo when changes affect deployment or cross-repo architecture.
