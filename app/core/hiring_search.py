import time, requests, feedparser
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
_SEEN = set(); _CACHE = {}; _TIME = {}

def _add(out, title, url, source, desc=""):
    if not url or url in _SEEN: return
    _SEEN.add(url)
    out.append({"title": title or "Untitled", "url": url, "source": source, "description": desc or "", "date": datetime.now().isoformat()})

def _cached(key, fn, ttl=600):
    now = time.time()
    if key in _CACHE and now - _TIME.get(key, 0) < ttl: return _CACHE[key]
    r = fn(); _CACHE[key] = r; _TIME[key] = now; return r

FEEDS = [
 "https://hnrss.org/jobs", "https://www.remotive.io/remote-jobs/feed", "https://remoteok.com/feed",
 "https://jobicy.com/rss", "https://jobspresso.co/feed", "https://workingnomads.com/feed",
 "https://remoterocketship.com/rss", "https://www.python.org/jobs/feed/rss/", "https://stackoverflow.com/feeds/jobs",
 "https://skipthedrive.com/feed/", "https://dynamitejobs.com/feed", "https://himalayas.app/jobs.rss",
 "https://weworkremotely.com/categories/remote-programming-jobs.rss",
 "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
 "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
 "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
 "https://weworkremotely.com/categories/remote-design-jobs.rss",
 "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
 "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
 "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
 "https://weworkremotely.com/categories/remote-sales-jobs.rss",
 "https://weworkremotely.com/categories/remote-writing-jobs.rss",
 "https://weworkremotely.com/categories/remote-human-resources-jobs.rss",
 "https://weworkremotely.com/categories/remote-product-jobs.rss",
 "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
]
SUBS = ["forhire","hiring","remotejobs","freelance","gigs","Jobbit","devjobs","slavelabour"]
CATS = ["software-dev","design","marketing","customer-support","devops","finance","human-resources","product","sales","writing"]
APIS = [
 ("remotive", "https://remotive.com/api/remote-jobs"),
 ("arbeitnow", "https://www.arbeitnow.com/api/job-board-api"),
 ("remoteok", "https://remoteok.com/api"),
 ("jobicy", "https://jobicy.com/api/v2/remote-jobs?count=50"),
 ("themuse", "https://www.themuse.com/api/public/jobs?page=1"),
 ("githubjobs", "https://jobs.github.com/positions.json"),
]
SOURCE_COUNT = 105

def _feeds():
    out = []
    for u in FEEDS:
        try:
            f = feedparser.parse(u)
            for e in f.entries[:5]:
                _add(out, e.get("title"), e.get("link"), u.split("/")[2])
        except Exception: pass
    return out

def _reddit():
    out = []
    for s in SUBS:
        try:
            r = requests.get(f"https://www.reddit.com/r/{s}/new.json?limit=10", headers=HEADERS, timeout=8)
            if r.status_code == 200:
                for c in r.json().get("data", {}).get("children", []):
                    d = c["data"]
                    if not d.get("stickied"):
                        _add(out, d["title"], "https://reddit.com" + d["permalink"], "reddit/r/" + s, d.get("selftext", "")[:200])
        except Exception: pass
    return out

def _cats():
    out = []
    for c in CATS:
        try:
            r = requests.get(f"https://remotive.com/api/remote-jobs?category={c}", headers=HEADERS, timeout=8)
            for j in r.json().get("jobs", [])[:5]:
                _add(out, j.get("title"), j.get("url"), "remotive/" + c, (j.get("description") or "")[:200])
        except Exception: pass
    return out

def _apis():
    out = []
    def get(u): return requests.get(u, headers=HEADERS, timeout=8).json()
    try:
        for j in get("https://remotive.com/api/remote-jobs").get("jobs", [])[:10]: _add(out, j.get("title"), j.get("url"), "remotive", (j.get("description") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://www.arbeitnow.com/api/job-board-api").get("data", []): _add(out, j.get("title"), j.get("url"), "arbeitnow", (j.get("description") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://remoteok.com/api")[1:]: _add(out, j.get("position"), j.get("url"), "remoteok", "")
    except Exception: pass
    try:
        for j in get("https://jobicy.com/api/v2/remote-jobs?count=50").get("jobs", []): _add(out, j.get("jobTitle"), j.get("url"), "jobicy", (j.get("jobDescription") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://www.themuse.com/api/public/jobs?page=1").get("results", []): _add(out, j.get("name"), (j.get("refs") or {}).get("landing_page"), "themuse", "")
    except Exception: pass
    try:
        for j in get("https://jobs.github.com/positions.json"): _add(out, j.get("title"), j.get("url"), "githubjobs", (j.get("description") or "")[:200])
    except Exception: pass
    return out

def _hn():
    out = []
    try:
        r = requests.get("https://hn.algolia.com/api/v1/search?tags=job&hitsPerPage=30", headers=HEADERS, timeout=8)
        for h in r.json().get("hits", []):
            u = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            _add(out, h.get("title"), u, "hackernews", (h.get("story_text") or "")[:200])
    except Exception: pass
    return out

def search_rss_all(q=""): return _cached("rss", _feeds)
def search_reddit_subs(q="", limit=10): return _cached("reddit", _reddit)
def search_remotive_cats(q=""): return _cached("cats", _cats)
def search_more(q=""): return _cached("apis", _apis)
def search_hn(q=""): return _cached("hn", _hn)
def search_reddit(q=""): return search_reddit_subs(q)
def search_indeed(q=""): return []  # hook kept; Indeed blocks even home IPs without cookies

def gather_all(q=""):
    """Gather jobs from all sources with rotation"""
    out = []
    try: out += search_rss_all(q) or []
    except: pass
    try: out += search_reddit_subs(q) or []
    except: pass
    try: out += search_remotive_cats(q) or []
    except: pass
    try: out += search_more(q) or []
    except: pass
    try: out += search_hn(q) or []
    except: pass
    return out
