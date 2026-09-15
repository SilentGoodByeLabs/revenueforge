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
        run_cycle()
        log("Sleeping 30 minutes...")
        time.sleep(1800)  # 30 minutes

if __name__ == "__main__":
    main()
