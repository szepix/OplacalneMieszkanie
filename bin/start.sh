#!/bin/sh
# Free-tier launcher: RQ worker in the background, uvicorn in the foreground.
set -e
python -m worker.run &
exec uvicorn web.app:app --host 0.0.0.0 --port "${PORT:-8888}" --workers "${WEB_WORKERS:-1}"
