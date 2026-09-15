#!/bin/bash
cd ~/projects/revenue_forge
source .venv/bin/activate

case "$1" in
  start)
    # 1. Worker (home-IP search loop + cloud push)
    if [ -f scripts/home_worker.py ]; then
      PYTHONPATH=. nohup python3 scripts/home_worker.py > /tmp/rf_worker.log 2>&1 &
      echo $! > ~/.rf_worker.pid
    fi
    
    # 2. Engine (FastAPI on 8502)
    PYTHONPATH=. nohup uvicorn app.ui.webapp:app --host 127.0.0.1 --port 8502 > /tmp/rf_engine.log 2>&1 &
    echo $! > ~/.rf_engine.pid
    
    # 3. Local web (static files on 8600, bound to 127.0.0.1)
    nohup python3 -m http.server 8600 --bind 127.0.0.1 > /tmp/rf_web.log 2>&1 &
    echo $! > ~/.rf_web.pid
    
    echo "✅ started: worker + engine 8502 + web 8600"
    ;;
    
  stop)
    fuser -k 8502/tcp 2>/dev/null
    fuser -k 8600/tcp 2>/dev/null
    [ -f ~/.rf_worker.pid ] && kill $(cat ~/.rf_worker.pid) 2>/dev/null
    echo "✅ stopped all 3"
    ;;
    
  status)
    echo "worker: $([ -f ~/.rf_worker.pid ] && pgrep -P $(cat ~/.rf_worker.pid) >/dev/null 2>&1 && echo 'alive' || echo 'stopped')"
    echo "engine: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8502/api/ping)"
    echo "web: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8600/)"
    ;;
    
  logs)
    tail -20 /tmp/rf_worker.log /tmp/rf_engine.log /tmp/rf_web.log
    ;;
    
  *) echo "usage: rf {start|stop|status|logs}" ;;
esac
