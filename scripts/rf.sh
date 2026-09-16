#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
case "$1" in
  start)
    pgrep -f home_worker.py >/dev/null || nohup python3 scripts/home_worker.py >/tmp/rf_worker.log 2>&1 &
    pgrep -f "uvicorn app.ui.webapp" >/dev/null || { PYTHONPATH=. nohup .venv/bin/uvicorn app.ui.webapp:app --host 127.0.0.1 --port 8502 >/tmp/rf_engine.log 2>&1 & }
    sleep 3; echo "✅ started"; "$0" status;;
  stop)
    pkill -f home_worker.py; pkill -f "uvicorn app.ui.webapp"; echo "⛔ stopped";;
  restart) "$0" stop; sleep 2; "$0" start;;
  status)
    pgrep -f home_worker.py >/dev/null && echo "✅ worker running" || echo " worker stopped"
    pgrep -f "uvicorn app.ui.webapp" >/dev/null && echo "✅ private engine running (8502)" || echo "⛔ engine stopped";;
  logs) tail -30 /tmp/rf_engine.log;;
  *) echo "usage: rf start|stop|restart|status|logs";;
esac
