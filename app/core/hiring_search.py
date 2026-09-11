import time, requests, feedparser
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
_SEEN=set(); _CACHE={}; _TIME={}; _ROT=0

def _add(out, title, url, source, desc=""):
    if not url or url in _SEEN: return
    _SEEN.add(url)
    out.append({"title": title or "Untitled", "url": url, "source": source, "description": desc or "", "date": datetime.now().isoformat()})

def _cached(key, fn, ttl=600):
    now=time.time()
    if key in _CACHE and now-_TIME.get(key,0)<ttl: return _CACHE[key]
    r=fn(); _CACHE[key]=r; _TIME[key]=now; return r

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
 "https://www.upwork.com/ab/feed/jobs/rss?q=python", "https://www.upwork.com/ab/feed/jobs/rss?q=automation",
 "https://www.upwork.com/ab/feed/jobs/rss?q=api+integration",
 "https://hnrss.org/newest?points=50&query=python", "https://hnrss.org/newest?points=50&query=automation",
]
SUBS = ["forhire","hiring","remotejobs","freelance","gigs","Jobbit","devjobs","slavelabour","remotework","digitalnomadjobs"]
CATS = ["software-dev","design","marketing","customer-support","devops","finance","human-resources","product","sales","writing","education"]
GREENHOUSE = ["stripe","coinbase","datadog","twilio","mongodb","elastic","hashicorp","gitlab","duolingo","notion",
 "figma","airtable","zapier","hubspot","cloudflare","digitalocean","discord","openai","anthropic","databricks",
 "snowflake","confluent","grafana","sentry","netlify","supabase","render","atlassian","dropbox","asana",
 "canva","klarna","revolut","wise","monzo","intercom","mixpanel","amplitude","segment","plaid","brex","ramp","mercury"]
LEVER = ["shopify","palantir"]
APIS = [
 ("remotive","https://remotive.com/api/remote-jobs"),
 ("arbeitnow","https://www.arbeitnow.com/api/job-board-api"),
 ("remoteok","https://remoteok.com/api"),
 ("jobicy","https://jobicy.com/api/v2/remote-jobs?count=50"),
 ("themuse","https://www.themuse.com/api/public/jobs?page=1"),
 ("githubjobs","https://jobs.github.com/positions.json"),
]
SOURCE_COUNT = len(FEEDS)+len(SUBS)+len(CATS)+len(GREENHOUSE)+len(LEVER)+len(APIS)+1+2  # +HN +import +alerts

def _group():
    global _ROT
    _ROT += 1
    return _ROT % 3

def _feeds():
    out=[]; g=_group(); feeds=FEEDS[g::3]+FEEDS[:2]
    for u in feeds:
        try:
            f=feedparser.parse(u)
            for e in f.entries[:4]: _add(out, e.get("title"), e.get("link"), u.split("/")[2])
        except Exception: pass
    return out

def _reddit():
    out=[]
    for s in SUBS:
        try:
            r=requests.get(f"https://www.reddit.com/r/{s}/new.json?limit=8", headers=HEADERS, timeout=8)
            if r.status_code==200:
                for c in r.json().get("data",{}).get("children",[]):
                    d=c["data"]
                    if not d.get("stickied"): _add(out, d["title"], "https://reddit.com"+d["permalink"], "reddit/r/"+s, d.get("selftext","")[:200])
        except Exception: pass
    return out

def _cats():
    out=[]
    for c in CATS:
        try:
            r=requests.get(f"https://remotive.com/api/remote-jobs?category={c}", headers=HEADERS, timeout=8)
            for j in r.json().get("jobs",[])[:3]: _add(out, j.get("title"), j.get("url"), "remotive/"+c, (j.get("description") or "")[:200])
        except Exception: pass
    return out

def _boards():
    out=[]; g=_group()
    for t in GREENHOUSE[g::3]:
        try:
            r=requests.get(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs", headers=HEADERS, timeout=8)
            for j in r.json().get("jobs",[])[:3]: _add(out, j.get("title"), j.get("absolute_url"), "greenhouse/"+t)
        except Exception: pass
    for t in LEVER:
        try:
            r=requests.get(f"https://api.lever.co/v0/postings/{t}?mode=json", headers=HEADERS, timeout=8)
            for j in r.json()[:3]: _add(out, j.get("text"), j.get("hostedUrl"), "lever/"+t)
        except Exception: pass
    return out

def _apis():
    out=[]
    def get(u): return requests.get(u, headers=HEADERS, timeout=8).json()
    try:
        for j in get("https://remotive.com/api/remote-jobs").get("jobs",[])[:8]: _add(out, j.get("title"), j.get("url"), "remotive", (j.get("description") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://www.arbeitnow.com/api/job-board-api").get("data",[]): _add(out, j.get("title"), j.get("url"), "arbeitnow", (j.get("description") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://remoteok.com/api")[1:]: _add(out, j.get("position"), j.get("url"), "remoteok")
    except Exception: pass
    try:
        for j in get("https://jobicy.com/api/v2/remote-jobs?count=50").get("jobs",[]): _add(out, j.get("jobTitle"), j.get("url"), "jobicy", (j.get("jobDescription") or "")[:200])
    except Exception: pass
    try:
        for j in get("https://www.themuse.com/api/public/jobs?page=1").get("results",[]): _add(out, j.get("name"), (j.get("refs") or {}).get("landing_page"), "themuse")
    except Exception: pass
    return out

def _hn():
    out=[]
    try:
        r=requests.get("https://hn.algolia.com/api/v1/search?tags=job&hitsPerPage=25", headers=HEADERS, timeout=8)
        for h in r.json().get("hits",[]):
            u=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            _add(out, h.get("title"), u, "hackernews", (h.get("story_text") or "")[:200])
    except Exception: pass
    return out

def _imported():
    out=[]
    for j in _load_json("imported.json", []) + _load_json("alerts.json", []):
        _add(out, j.get("title"), j.get("url"), j.get("source","imported"), j.get("description","")[:200])
    return out

def _load_json(name, default):
    from pathlib import Path as _P
    f=_P(__file__).resolve().parents[2]/"data"/name
    try: return __import__("json").loads(f.read_text()) if f.exists() else default
    except Exception: return default

def gather_all(q=""):
    out=[]
    out += _imported()
    out += _cached("feeds%d"%_ROT, _feeds, ttl=300)
    out += _cached("boards%d"%_ROT, _boards, ttl=300)
    out += _cached("reddit", _reddit, ttl=600)
    out += _cached("cats", _cats, ttl=600)
    out += _cached("apis", _apis, ttl=600)
    out += _cached("hn", _hn, ttl=600)
    return out

def search_rss_all(q=""): return _cached("feeds%d"%_ROT, _feeds, ttl=300)
def search_reddit_subs(q="", limit=10): return _cached("reddit", _reddit, ttl=600)
def search_remotive_cats(q=""): return _cached("cats", _cats, ttl=600)
def search_more(q=""): return _cached("apis", _apis, ttl=600) + _cached("boards%d"%_ROT, _boards, ttl=300)
def search_hn(q=""): return _cached("hn", _hn, ttl=600)
def search_reddit(q=""): return search_reddit_subs(q)
def search_indeed(q=""): return []

CLOUD="https://revenueforge-api.onrender.com"
def push_jobs(rs):
    """PRIVACY-SAFE: push ONLY anonymized job listings to cloud. No queries, skills, or email."""
    import json as _j
    from pathlib import Path as _P
    pf=_P(__file__).resolve().parents[2]/"data"/"pushed.json"
    try: pushed=set(_j.loads(pf.read_text())) if pf.exists() else set()
    except Exception: pushed=set()
    new=[{"title":r["title"],"url":r["url"],"source":r["source"],"description":r.get("description","")} for r in rs if r["url"] not in pushed]
    if not new: return 0
    for ep in ["/api/jobs/ingest","/api/ingest","/api/jobs","/api/push-jobs"]:
        try:
            r=requests.post(CLOUD+ep, json={"jobs":new[:50],"origin":"home-worker"}, timeout=15)
            if r.status_code in (200,201):
                pushed.update(x["url"] for x in new); pf.parent.mkdir(exist_ok=True); pf.write_text(_j.dumps(list(pushed)[-2000:]))
                return len(new)
        except Exception: continue
    return 0
