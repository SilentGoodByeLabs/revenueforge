#!/usr/bin/env python3
"""
Autonomous home-IP worker: searches 182 sources every 30 minutes,
pushes anonymized jobs to cloud, logs activity.
"""
import time
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.hiring_search import gather_all, push_jobs, SOURCE_COUNT

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def run_cycle():
    """One complete search + push cycle"""
    try:
        log(f"Starting search across {SOURCE_COUNT} sources...")
        jobs = gather_all("")
        log(f"Found {len(jobs)} unique jobs")
        
        if jobs:
            # Save to local cache for UI
            import json
            from datetime import datetime
            cache_file = Path("data/last_search.json")
            cache_data = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "jobs": jobs,
                "query": "auto-hunt"
            }
            cache_file.write_text(json.dumps(cache_data, indent=2))
            log(f"Saved {len(jobs)} jobs to cache")
            
            # Save to jobs.json for UI
            jobs_file = Path("data/jobs.json")
            jobs_file.write_text(json.dumps(jobs, indent=2))
            log(f"Saved {len(jobs)} jobs to jobs.json")
            
            # Push to cloud
            log("Pushing to cloud...")
            push_jobs(jobs)
            log("Push complete")
        else:
            log("No jobs found this cycle")
            
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")

def main():
    log(f"Worker started - will search every 30 minutes")
    log(f"Scraping {SOURCE_COUNT} sources from home IP")
    
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"FATAL ERROR in cycle: {type(e).__name__}: {e}")
            log("Will retry in 30 minutes...")
        freq = 10
        try:
            import json as _j
            _s = _j.loads(Path("data/settings.json").read_text())
            freq = int(_s.get("frequency", 10))
        except Exception:
            freq = 10
        log(f"Sleeping {freq} minutes...")
        time.sleep(freq * 60)

if __name__ == "__main__":
    main()
