#!/usr/bin/env python3
"""Push jobs from private engine to cloud every 30 minutes."""
import sys
sys.path.insert(0, '/home/silentgoodbye/projects/revenue_forge')
from app.core import hiring_search as HS
import time

print("Starting scheduled job push to cloud...")
while True:
    try:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Collecting jobs from 105+ sources...")
        jobs = HS.gather_all()
        print(f"Collected {len(jobs)} jobs")
        
        print("Pushing to cloud (anonymized)...")
        pushed = HS.push_jobs(jobs)
        print(f"Pushed {pushed} new jobs to cloud")
    except Exception as e:
        print(f"Error: {e}")
    
    print("Sleeping 30 minutes...")
    time.sleep(1800)  # 30 minutes
