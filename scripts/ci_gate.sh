#!/usr/bin/env bash

set -euo pipefail

syntax_check() {
  echo "==> backend-gate: Python syntax check"
  python -m py_compile main.py
  python -m py_compile server.py
  python -m py_compile src/config.py
  python -m py_compile src/auth.py
  python -m py_compile src/notification.py
  python -m py_compile src/scheduler.py
  python -m py_compile src/logging_config.py
  python -m py_compile src/md2img.py
  python -m py_compile src/formatters.py
  python -m py_compile src/services/ai_daily_digest.py
  python -m py_compile src/services/system_config_service.py
  python -m py_compile src/core/config_manager.py
  python -m py_compile src/core/config_registry.py
  python -m py_compile api/app.py
  python -m py_compile api/deps.py
  python -m py_compile api/v1/router.py
  for f in src/notification_sender/*.py api/v1/endpoints/*.py api/v1/schemas/*.py api/middlewares/*.py; do
    python -m py_compile "$f"
  done
}

flake8_checks() {
  echo "==> backend-gate: flake8 critical checks"
  flake8 main.py src/config.py src/notification.py src/scheduler.py src/services/ai_daily_digest.py --count --select=E9,F63,F7,F82 --show-source --statistics
}

run_all() {
  syntax_check
  flake8_checks
  echo "==> backend-gate: all checks passed"
}

phase="${1:-all}"

case "$phase" in
  all)
    run_all
    ;;
  syntax)
    syntax_check
    ;;
  flake8)
    flake8_checks
    ;;
  *)
    echo "Usage: $0 [all|syntax|flake8]" >&2
    exit 2
    ;;
esac
