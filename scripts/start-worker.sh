#!/bin/bash
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)/backend:$(pwd)"
celery -A app.worker worker --loglevel=info
