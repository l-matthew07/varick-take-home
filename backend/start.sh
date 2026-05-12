#!/usr/bin/env sh
set -eu

echo "Waiting for PostgreSQL..."
attempt=1
until python -c "
import os, sys
url = os.environ['DATABASE_URL']
if url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
"; do
  if [ "$attempt" -ge 30 ]; then
    echo "PostgreSQL did not become available in time." >&2
    exit 1
  fi
  echo "Attempt $attempt/30..."
  attempt=$((attempt + 1))
  sleep 2
done

echo "PostgreSQL is ready."
python scripts/seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
