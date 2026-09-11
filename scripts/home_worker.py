import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.hiring_search import search_more, search_reddit_subs, search_rss_all, search_indeed

def main():
    print("🏠 Home worker running on YOUR home IP. Ctrl-C to stop.")
    print("home worker sources:", ["search_more", "search_reddit_subs", "search_reddit", "search_remotive_cats", "search_hn"])
    
    # Test the functions
    try:
        rss = search_rss_all("python")
        print(f"✅ RSS found {len(rss)} jobs")
    except Exception as e:
        print(f"❌ RSS failed: {e}")

    try:
        reddit = search_reddit_subs("hiring")
        print(f"✅ Reddit found {len(reddit)} jobs")
    except Exception as e:
        print(f"❌ Reddit failed: {e}")

    import time
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Worker stopped.")

if __name__ == "__main__":
    main()
