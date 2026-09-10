import feedparser
import requests
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_reddit_subs(query="hiring", limit=10):
    """Scrape r/forhire and r/hiring for posts."""
    results = []
    subs = ["forhire", "hiring", "remotejobs"]
    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                for post in r.json().get("data", {}).get("children", []):
                    data = post["data"]
                    if data.get("stickied"): continue
                    results.append({
                        "title": data["title"],
                        "url": f"https://reddit.com{data['permalink']}",
                        "source": "Reddit",
                        "date": datetime.fromtimestamp(data["created_utc"]).isoformat()
                    })
        except Exception:
            pass
    return results

def search_rss_all(query=""):
    """Search RSS feeds for remote tech jobs (HackerNews, StackOverflow, etc)."""
    feeds = [
        "https://hnrss.org/jobs",
        "https://stackoverflow.com/jobs/feed",
        "https://www.reddit.com/r/remotejobs/.rss",
        "https://www.remotive.io/remote-jobs/feed",
    ]
    results = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                results.append({
                    "title": entry.get("title", "No Title"),
                    "url": entry.get("link", ""),
                    "source": feed_url.split("/")[2],
                    "date": entry.get("published", datetime.now().isoformat())
                })
        except Exception:
            pass
    return results

def search_more(query=""):
    """Fallback search for additional sources."""
    return []

def search_indeed(query=""):
    """Scrape Indeed (requires residential IP)."""
    return []

def search_reddit(query=""):
    """Alias for search_reddit_subs."""
    return search_reddit_subs(query)

def search_remotive_cats(query=""):
    """Search Remotive categories."""
    return []

def search_hn(query=""):
    """Search Hacker News jobs."""
    return []
