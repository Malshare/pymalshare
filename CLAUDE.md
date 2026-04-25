# MalShare pymalshare

Python backend for MalShare — handles sample processing and export generation that PHP can't do efficiently.

## Tech Stack

- Python 3.14 (generate_daily) / 3.13 (upload_handler)
- MariaDB (`mariadb` package) for generate_daily, `pymysql` for upload_handler
- boto3 for S3/Wasabi storage
- python-magic, ssdeep for sample analysis
- Black (120 char lines) + isort for formatting

## Project Structure

```
generate_daily.py              # Daily hash export generator (run-once job)
rollup_api_calls.py            # Two-tier API call aggregation (run-once job)
refresh_stats.py               # Precompute expensive sample stats into tbl_stats_cache (run-once job)
cleanup_users.py               # Clear IP addresses for inactive users (run-once job)
upload_handler.py              # Long-running daemon for sample processing
url_task_handler.py            # Long-running daemon for URL downloads via Tor
lib/
  db.py                        # MariaDB database layer (queries tbl_samples, rollups, stats cache)
  storage.py                   # S3/Wasabi abstraction (boto3)
  pymalshare.py                # Core class: sample processing, DB updates
docker/
  Docker.generate_daily        # Container for daily export (lightweight, mariadb only)
  Dockerfile.rollup_api_calls  # Container for API call rollup
  Dockerfile.refresh_stats     # Container for stats cache refresh
  Dockerfile.cleanup_users     # Container for user IP cleanup
  Dockerfile.upload_handler    # Container for upload handler (ssdeep/magic)
  Dockerfile.url_task_handler  # Container for URL task handler (Tor)
  Dockerfile.base              # Shared base image for handlers
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
- In production, output goes to the `daily_exports` Docker volume, which is mounted read-only into the frontend container at `/var/www/html/daily/` and served as browsable directory listings at `/daily/`

### rollup_api_calls.py
Aggregates old `tbl_api_calls` rows into `tbl_api_calls_daily`:
- Tier 1 (30+ days old): individual rows → per-user, per-endpoint, per-day summaries
- Tier 2 (365+ days old): per-user summaries → endpoint-only totals (user_id = NULL)
- Deletes aggregated rows from the source table after rollup
- Run daily via Docker sleep loop

### refresh_stats.py
Precomputes expensive sample statistics into `tbl_stats_cache`:
- Runs the slow `COUNT(*)`, `GROUP BY YEAR(...)`, `GROUP BY ftype` queries on `tbl_samples` in the background
- Also computes all-time API call total (`COUNT(*)` on `tbl_api_calls` + `SUM` on `tbl_api_calls_daily`)
- Writes results as key-value pairs via `INSERT ... ON DUPLICATE KEY UPDATE`
- Cached keys: `total_samples`, `earliest_upload`, `latest_upload`, `uploads_by_year` (JSON), `file_type_breakdown` (JSON), `api_calls_all_time`
- The Frontend's `stats.php` and `admin.php` read from this table instead of running full table scans
- Run hourly via Docker sleep loop (3600s)
- **When adding new expensive queries to the stats page, add them here instead of running on page load**

### cleanup_users.py
Clears IP address history for users inactive 90+ days. Run daily via Docker sleep loop.

### upload_handler.py
Long-running daemon that processes pending malware samples:
- Polls DB every 10 seconds for pending samples
- Downloads binary from S3, detects file type (libmagic), computes ssdeep hash
- Updates DB with results and marks sample as processed

## Environment Variables

### Database (both scripts)
- `MALSHARE_DB_HOST`, `MALSHARE_DB_USER`, `MALSHARE_DB_PASS`
- `MALSHARE_DB_DATABASE` (optional, default: `malshare_db`)

### S3 Storage (upload_handler only)
- `WASABI_BUCKET`, `WASABI_KEY`, `WASABI_SECRET`, `WASABI_ENDPOINT`

### Output (generate_daily only)
- `OUTPUT_DIR` — directory for generated hash lists

## Building

```bash
# generate_daily
make build-generate-daily

# upload_handler
make build
```

The Makefile uses `--env-file .env` for credentials. Create a `.env` file with the DB and S3 variables listed above. Do not commit `.env`.

## Deployment

All services run in the conf repo's `docker-compose.yml` alongside the frontend:
- `generate-daily`, `rollup-api-calls`, `refresh-stats`, `cleanup-users` — run-once jobs with sleep loops (daily or hourly)
- `upload-handler`, `url-task-handler` — long-running daemons with polling loops

All images are built and pushed to GHCR via `.github/workflows/docker.yml` (build → push → trigger conf dispatch). Independent builds run in parallel; the conf dispatch fires after all succeed.

## Important: No secrets in Docker images

- **Never `COPY .env`** into a Docker image — secrets must come from `env_file` in docker-compose at runtime
- Environment variables are passed via docker-compose `env_file`, not baked into images

## Database

Queries `malshare_db.tbl_samples` primarily:
- `md5`, `sha1`, `sha256` — sample hashes
- `added` — Unix timestamp, used for date range queries in generate_daily
- `pending` — flag for upload_handler to pick up unprocessed samples
- `ssdeep`, `ftype` — populated by upload_handler after processing

## Known Issues / Notes

- `lib/db.py` hardcodes port 3306 — no `MALSHARE_DB_PORT` support
- `upload_handler.py` uses `pymysql` while `generate_daily.py` uses `mariadb` — two different DB drivers
- The Makefile `run-generate-daily` target uses `--env-file .env` — ensure `.env` exists locally

## Maintenance

Keep this CLAUDE.md up-to-date when adding features, fixing bugs, or learning new things about the project. Also update `CLAUDE.md` in the `Malshare/conf` repo when changes affect deployment or cross-repo architecture.
