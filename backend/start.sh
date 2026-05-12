#!/usr/bin/env sh
set -eu

python - <<'PY'
import os
import time

import psycopg

database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

for _ in range(30):
    try:
        with psycopg.connect(database_url):
            break
    except psycopg.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("Database did not become available in time.")
PY

python scripts/seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
