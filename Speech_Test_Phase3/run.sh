#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run bash setup.sh once while online, then run this test offline.' >&2
  exit 1
fi
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
export PYTHONDONTWRITEBYTECODE=1
case "${1:-live}" in
  live|record|mic-test|menu)
    exec 9>.microphone.lock
    if ! flock -n 9; then
      echo 'The speech tester is already open. Close its terminal with Ctrl+C, then try again.' >&2
      exit 1
    fi
    ;;
esac
exec nice -n 10 .venv/bin/python -u speech_test.py "$@"
