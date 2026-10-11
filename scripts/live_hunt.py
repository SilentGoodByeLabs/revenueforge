#!/usr/bin/env python3
import sys, json, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FLAG = Path("data/.hunting")
CACHE = Path("data/last_search.json")
JOBS = Path("data/jobs.json")

# Mark start
FLAG.write_text(str(time.time()))
print(f"[{datetime.now().strftime('%H:%M:%S')}] Live hunt started", flush=True)

try:
    from app.core.hiring_search import gather_all
    jobs = gather_all("")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(jobs)} jobs", flush=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cache_data = {"time": now_str, "jobs": jobs, "query": "all"}
    CACHE.write_text(json.dumps(cache_data, indent=2))
    JOBS.write_text(json.dumps(jobs, indent=2))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved to cache (public engine ready)", flush=True)
except Exception as e:
    print(f"[{datetime.now().strftime('%H:%M:%S')]} ERROR: {e}", flush=True)
finally:
    try:
        FLAG.unlink()
    except Exception:
        pass
    print(f"[{datetime.now().strftime('%H:%M:%S')]} Hunt finished, flag cleared", flush=True)
