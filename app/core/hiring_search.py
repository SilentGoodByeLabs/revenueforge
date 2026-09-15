import feedparser, json, urllib.request, urllib.parse, time
from pathlib import Path
from datetime import datetime

DATA = Path(__file__).resolve().parents[2] / "data"
DATA.mkdir(exist_ok=True)

def ld(n, d):
    p = DATA / n
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    return d
def sv(n, o): (DATA / n).write_text(json.dumps(o, indent=2))

_rot = {"index": 0, "last": 0}

def _get(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception: return ""


def _strip(html):
    """Remove HTML tags so descriptions show as clean text"""
    import re as _re
    if not html: return ""
    txt = _re.sub(r'<[^>]+>', ' ', html)
    txt = _re.sub(r'&[a-z]+;', ' ', txt)
    txt = _re.sub(r'\s+', ' ', txt).strip()
    return txt

def _score(text, q):
    if not text or not q: return 55
    t, q = text.lower(), q.lower(); s = 55
    for w in q.split():
        if w in t: s += 9
    if any(w in t for w in ["remote","freelance","contract","work from home"]): s += 12
    if any(w in t for w in ["python","automation","ai","api","n8n","zapier","scraping"]): s += 8
    return min(s, 99)

RSS_FEEDS = [
 ("hnrss","https://hnrss.org/newest?points=50"), ("remoteok","https://remoteok.com/remote-jobs.rss"),
 ("weworkremotely-dev","https://weworkremotely.com/categories/remote-programming-jobs.rss"),
 ("weworkremotely-design","https://weworkremotely.com/categories/remote-design-jobs.rss"),
 ("weworkremotely-mkt","https://weworkremotely.com/categories/remote-marketing-jobs.rss"),
 ("jobicy","https://jobicy.com/feed"), ("remotive-dev","https://remotive.com/remote-jobs/software-dev/feed"),
 ("stackoverflow","https://stackoverflow.com/jobs/feed?q=python"), ("upwork","https://www.upwork.com/ab/feed/jobs/rss?sort=recency"),
 ("fiverr","https://www.fiverr.com/rss/gigs?category=programming-tech"),
 ("workingnomads","https://www.workingnomads.com/feed"), ("jobspresso","https://jobspresso.co/feed"),
 ("remote4me","https://remote4me.com/feed"), ("justremote","https://justremote.co/feed"),
 ("remotegigs","https://remotegigs.com/feed"), ("wfh","https://wfh.io/feed"),
 ("jobsgrid","https://jobsgrid.io/feed"), ("remoteleaf","https://remoteleaf.com/feed"),
 ("skipthedrive","https://www.skipthedrive.com/feed"), ("himalayas","https://himalayas.app/jobs/feed"),
 ("dynamitejobs","https://dynamitejobs.com/feed"), ("remotive-product","https://remotive.com/remote-jobs/product/feed"),
 ("remotive-data","https://remotive.com/remote-jobs/data/feed"), ("remotive-devops","https://remotive.com/remote-jobs/devops/feed"),
 ("remotive-support","https://remotive.com/remote-jobs/customer-support/feed"),
 ("remotive-sales","https://remotive.com/remote-jobs/sales/feed"), ("remotive-mkt","https://remotive.com/remote-jobs/marketing/feed"),
 ("remotive-finance","https://remotive.com/remote-jobs/finance/feed"), ("remotive-hr","https://remotive.com/remote-jobs/human-resources/feed"),
 ("remotive-writing","https://remotive.com/remote-jobs/writing/feed")]

REDDIT_SUBS = ["r/forhire","r/hiring","r/remotejobs","r/programmingjobs","r/freelance","r/workonline",
 "r/digitalnomad","r/startups","r/entrepreneur","r/smallbusiness","r/automate","r/nocode","r/swejobs",
 "r/cscareerquestions","r/revskilltrade"]

REMOVIVE_CATS = ["software-dev","design","product","customer-support","marketing","sales","writing",
 "finance","hr","devops","data"]

GREENHOUSE = ["stripe","coinbase","gitlab","notion","figma","linear","vercel","supabase","railway",
 "render","netlify","shopify","github","atlassian","slack","discord","twitch","cloudflare","datadog",
 "twilio","plaid","brex","ramp","mercury","gusto","rippling","deel","buffer","zapier","webflow",
 "airtable","loom","calendly","typeform","intercom","hubspot","salesforce","zendesk","freshworks",
 "zoho","monday","canva","miro","amplitude","mixpanel","segment","postman","snyk","auth0","okta",
 "duolingo","spotify","reddit","pinterest","dropbox","asana","clickup","notion-labs","grammarly",
 "quora","medium","substack","discord-gg","fly-io","planetscale","neon","turso","prisma","retool",
 "superhuman","front","linear-app","height","shortcut","clubhouse","gitbook","docsify","readme",
 "postman-labs","insomnia","hoppscotch","raycast","warp","tabnine","codegen","sourcegraph","replit",
 "codesandbox","stackblitz","glitch","codepen"]

LEVER = ["vercel","netlify","railway","render","planetscale","supabase","neon","turso","prisma","retool"]

ASHBY = ["notion","linear","vercel","supabase","ramp","mercury","brex","deel","gusto","rippling",
 "webflow","loom","calendly","typeform"]

SMARTRECRUITERS = ["bosch","visa","ukg","wayfair","zalando","jdpw","smartrecruiters","revolut"]

def search_rss_all(q=""):
    out=[]
    for name,url in RSS_FEEDS:
        try:
            d = feedparser.parse(_get(url))
            for e in d.entries[:8]:
                out.append({"title":e.get("title",""),"url":e.get("link",""),"description":_strip(e.get("summary",""))[:400],"source":name,"score":_score(e.get("title","")+e.get("summary",""),q)})
        except Exception: pass
    try:
        data = json.loads(_get("https://www.arbeitnow.com/api/job-board-api"))
        for j in data.get("jobs",[])[:25]:
            out.append({"title":j.get("title",""),"url":j.get("url",""),"description":_strip(j.get("description",""))[:400],"source":"arbeitnow","score":_score(j.get("title","")+j.get("description",""),q)})
    except Exception: pass
    return out

def search_reddit_subs(q=""):
    out=[]
    for s in REDDIT_SUBS:
        try:
            data=json.loads(_get(f"https://www.reddit.com/{s}/new.json?limit=12"))
            for c in data.get("data",{}).get("children",[]):
                p=c.get("data",{}); t=p.get("title","")
                if any(w in t.lower() for w in ["hiring","looking for","need","want","hire"]):
                    out.append({"title":t,"url":"https://reddit.com"+p.get("permalink",""),"description":_strip(p.get("selftext",""))[:400],"source":s,"score":_score(t+p.get("selftext",""),q)})
        except Exception: pass
    return out

def search_remotive_cats(q=""):
    out=[]
    for c in REMOVIVE_CATS:
        try:
            data=json.loads(_get(f"https://remotive.com/api/remote-jobs?category={c}&limit=12"))
            for j in data.get("jobs",[]):
                out.append({"title":j.get("title",""),"url":j.get("url",""),"description":_strip(j.get("description",""))[:400],"source":"remotive/"+c,"score":_score(j.get("title","")+j.get("description",""),q)})
        except Exception: pass
    return out

def search_greenhouse(q=""):
    out=[]
    for c in GREENHOUSE:
        try:
            data=json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs", timeout=5))
            for j in data.get("jobs",[])[:4]:
                out.append({"title":j.get("title",""),"url":j.get("absolute_url",""),"description":_strip(j.get("content","") or "")[:400],"source":"greenhouse/"+c,"score":_score(j.get("title",""),q)})
        except Exception: pass
    return out

def search_lever(q=""):
    out=[]
    for c in LEVER:
        try:
            data=json.loads(_get(f"https://api.lever.co/v0/postings/{c}?mode=json", timeout=5))
            for j in data[:4]:
                out.append({"title":j.get("text",""),"url":j.get("hostedUrl",""),"description":_strip(j.get("descriptionPlain","") or "")[:400],"source":"lever/"+c,"score":_score(j.get("text",""),q)})
        except Exception: pass
    return out

def search_ashby(q=""):
    out=[]
    for c in ASHBY:
        try:
            data=json.loads(_get(f"https://api.ashbyhq.com/posting-api/job-board/{c}", timeout=5))
            for j in data.get("jobs",[])[:4]:
                out.append({"title":j.get("title",""),"url":j.get("jobUrl") or j.get("url",""),"description":_strip(j.get("descriptionPlain","") or "")[:400],"source":"ashby/"+c,"score":_score(j.get("title",""),q)})
        except Exception: pass
    return out

def search_smartrecruiters(q=""):
    out=[]
    for c in SMARTRECRUITERS:
        try:
            data=json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=5", timeout=5))
            for j in data.get("content",[]):
                out.append({"title":j.get("name",""),"url":j.get("postingUrl",""),"description":(j.get("jobAd",{}).get("jobDescription","") or "")[:400],"source":"smartrecruiters/"+c,"score":_score(j.get("name",""),q)})
        except Exception: pass
    return out

def search_hn(q=""):
    out=[]
    try:
        data=json.loads(_get(f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(q or 'python')}&tags=job"))
        for h in data.get("hits",[])[:20]:
            out.append({"title":h.get("title",""),"url":f"https://news.ycombinator.com/item?id={h.get('objectID','')}","description":_strip(h.get("story_text","") or "")[:400],"source":"hn-algolia","score":_score(h.get("title",""),q)})
    except Exception: pass
    return out

def search_imported(q=""):
    return [j for j in ld("imported.json",[]) if _score(j.get("title","")+j.get("description",""),q)>55]

SOURCE_COUNT = len(RSS_FEEDS)+1+len(REDDIT_SUBS)+len(REMOVIVE_CATS)+len(GREENHOUSE)+len(LEVER)+len(ASHBY)+len(SMARTRECRUITERS)+2

def gather_all(q=""):
    global _rot
    if time.time()-_rot.get("last",0)>300:
        _rot["index"]=0; _rot["last"]=time.time()
    idx=_rot["index"]; _rot["index"]=(idx+1)%4
    jobs = search_rss_all(q)+search_hn(q)+search_imported(q)
    if idx==0: jobs+=search_reddit_subs(q)+search_remotive_cats(q)
    elif idx==1: jobs+=search_greenhouse(q)
    elif idx==2: jobs+=search_lever(q)+search_ashby(q)
    else: jobs+=search_smartrecruiters(q)+search_remotive_cats(q)
    seen=set(); ded=[]
    for j in jobs:
        u=j.get("url")
        if u and u not in seen: seen.add(u); ded.append(j)
    ded.sort(key=lambda x:x.get("score",0), reverse=True)
    return ded

def push_jobs(jobs):
    try:
        payload={"jobs":[{"title":j.get("title",""),"platform":j.get("source","home"),"url":j.get("url",""),"description":_strip(j.get("description",""))[:400],"score":j.get("score",80)} for j in jobs[:300]],"source":"home-worker"}
        req=urllib.request.Request("https://revenueforge-api.onrender.com/jobs/ingest", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=30)
        sv("push.json",{"time":datetime.now().isoformat(),"total":len(jobs)})
    except Exception: pass
