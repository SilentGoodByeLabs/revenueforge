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
def sv(n, o): DATA.mkdir(exist_ok=True); (DATA / n).write_text(json.dumps(o, indent=2))

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





# ============ WORKING DIRECT APIS (Phase 2 - Fixed) ============
def search_usajobs(q=""):
    """USAJobs government API (free, no auth needed)"""
    out = []
    try:
        url = f"https://data.usajobs.gov/api/Search/Results?Keyword={_up.quote(q)}&WhoMayApply=public&ResultsPerPage=20"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Host": "data.usajobs.gov",
            "Authorization-Key": "DEMO_KEY"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            for j in data.get("SearchResult", {}).get("SearchResultItems", [])[:20]:
                out.append({
                    "title": j.get("MatchedObjectDescriptor", {}).get("PositionTitle", ""),
                    "url": j.get("MatchedObjectDescriptor", {}).get("PositionURI", ""),
                    "description": _strip(j.get("MatchedObjectDescriptor", {}).get("PositionLocationDisplay", ""))[:400],
                    "source": "usajobs",
                    "platform": "usajobs",
                    "score": _score(j.get("MatchedObjectDescriptor", {}).get("PositionTitle", ""), q)
                })
    except Exception:
        pass
    return out

def search_devitjobs(q=""):
    """DevITJobs UK tech jobs RSS"""
    out = []
    try:
        raw = _get("https://devitjobs.uk/job_feed.xml", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "devitjobs",
                    "platform": "devitjobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_authenticjobs(q=""):
    """Authentic Jobs RSS feed"""
    out = []
    try:
        raw = _get("https://authenticjobs.com/rss/", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "authenticjobs",
                    "platform": "authenticjobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_golangprojects(q=""):
    """Golang Projects RSS feed"""
    out = []
    try:
        raw = _get("https://golangprojects.com/golang-jobs.xml", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "golangprojects",
                    "platform": "golangprojects",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_euremotejobs(q=""):
    """EU Remote Jobs RSS feed"""
    out = []
    try:
        raw = _get("https://euremotejobs.com/feed/", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "euremotejobs",
                    "platform": "euremotejobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out



# ============ BLOCKED SITES (Private Engine Bridge Only) ============
def _glassdoor_rss(q=""):
    """Glassdoor RSS (limited, needs bridge for full access)"""
    out = []
    try:
        # Glassdoor has limited public RSS for some categories
        raw = _get(f"https://www.glassdoor.com/search/rss.htm?searchSource=GN_TEXTBOX&sc.keyword={_up.quote(q)}", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "glassdoor",
                    "platform": "glassdoor",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def _wellfound(q=""):
    """Wellfound (AngelList) job search"""
    out = []
    try:
        # Wellfound has a public job search endpoint
        url = f"https://wellfound.com/api/v2/search/jobs?q={_up.quote(q)}&page=1"
        data = json.loads(_get(url, timeout=10) or "{}")
        for j in data.get("jobs", [])[:15]:
            out.append({
                "title": j.get("title", ""),
                "url": f"https://wellfound.com/jobs/{j.get('id', '')}",
                "description": _strip(j.get("description", ""))[:400],
                "source": "wellfound",
                "platform": "wellfound",
                "score": _score(j.get("title", "") + " " + j.get("description", ""), q)
            })
    except Exception:
        pass
    return out

def _dice_rss(q=""):
    """Dice RSS feed (limited)"""
    out = []
    try:
        raw = _get(f"https://www.dice.com/jobs?q={_up.quote(q)}&format=rss", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "dice",
                    "platform": "dice",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def _angel_co(q=""):
    """Angel.co jobs (now Wellfound, but legacy endpoint)"""
    out = []
    try:
        url = f"https://angel.co/api/v1/search/jobs?query={_up.quote(q)}"
        data = json.loads(_get(url, timeout=10) or "{}")
        for j in data.get("results", [])[:15]:
            out.append({
                "title": j.get("title", ""),
                "url": j.get("url", ""),
                "description": _strip(j.get("description", ""))[:400],
                "source": "angellist",
                "platform": "angellist",
                "score": _score(j.get("title", "") + " " + j.get("description", ""), q)
            })
    except Exception:
        pass
    return out

def _builtin_sf(q=""):
    """Built In SF tech jobs RSS"""
    out = []
    try:
        raw = _get("https://www.builtinsf.com/jobs/rss", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "builtinsf",
                    "platform": "builtinsf",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

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


# ============ EXTRA PLATFORMS (appended safely) ============
import urllib.parse as _up
import concurrent.futures as _cf
import xml.etree.ElementTree as _ET

GH_EXTRA = ["stripe","shopify","spotify","airbnb","dropbox","gitlab","figma","notion","linear","ramp","brex","plaid","coinbase","cloudflare","datadog","mongodb","elastic","hashicorp","twilio","atlassian","canva","miro","airtable","zapier","hubspot","intercom","asana","slack","pinterest","duolingo"]
LEVER_EXTRA = ["netflix","kickstarter","square","gusto","flexport","lattice","culture-amp","warby-parker","rappi","anthropic","openai","vercel"]
ASHBY_EXTRA = ["supabase","neon","fly-io","retool","mercury","scale-ai","ramp","notion","linear","perplexity"]
RSS_EXTRA = [("workingnomads","https://workingnomads.com/feed?category=development"),("jobspresso","https://jobspresso.co/feed/"),("weworkremotely","https://weworkremotely.com/categories/remote-programming-jobs.rss"),("remotewomen","https://remotewomen.co/feed/")]

def _rss_jobs(url, platform, maxn=15):
    out=[]
    try:
        raw=_get(url, timeout=10)
        if not raw: return out
        root=_ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out)>=maxn: break
            ti=(item.findtext('title') or '').strip(); li=(item.findtext('link') or '').strip()
            de=item.findtext('description') or ''
            if ti and li: out.append({"title":ti,"url":li,"source":platform,"platform":platform,"description":re.sub('<[^>]+>','',de)[:300],"score":0})
        for e in root.iter('{http://www.w3.org/2005/Atom}entry'):
            if len(out)>=maxn: break
            ti=(e.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            le=e.find('{http://www.w3.org/2005/Atom}link'); li=le.get('href') if le is not None else ''
            if ti and li: out.append({"title":ti,"url":li,"source":platform,"platform":platform,"description":"","score":0})
    except Exception: pass
    return out

def _linkedin_guest(q=""):
    out=[]
    try:
        url="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords="+_up.quote(q or "remote")+"&start=0"
        raw=_get(url, timeout=12) or ""
        for m in re.finditer(r'href="(https://www\.linkedin\.com/jobs/view/[^"]+)"[^>]*>\s*<h3[^>]*>([^<]+)</h3>', raw):
            out.append({"title":m.group(2).strip(),"url":m.group(1),"source":"linkedin","platform":"linkedin","description":"","score":0})
        if not out:
            for m in re.finditer(r'<a[^>]+href="([^"]+/jobs/view/[^"]+)"[^>]*aria-label="([^"]+)"', raw):
                out.append({"title":m.group(2).strip(),"url":m.group(1),"source":"linkedin","platform":"linkedin","description":"","score":0})
        if not out:
            for m in re.finditer(r'<a[^>]+href="([^"]+/jobs/view/[^"]+)"[^>]*>(.*?)</a>', raw, re.S):
                ti=re.sub(r'<[^>]+>','',m.group(2)).strip()
                if len(ti)>4:
                    out.append({"title":ti,"url":m.group(1),"source":"linkedin","platform":"linkedin","description":"","score":0})
        seen=set(); ded=[]
        for j in out:
            if j["url"] not in seen: seen.add(j["url"]); ded.append(j)
        out=ded
    except Exception:
        pass
    return out[:15]

def _indeed_rss(q=""):
    return _rss_jobs("https://rss.indeed.com/rss?q="+_up.quote(q or "remote"), "indeed")

def _arbeitnow(q=""):
    out=[]
    try:
        d=json.loads(_get("https://www.arbeitnow.com/api/job-board-api", timeout=12) or "{}")
        for j in d.get("data",[])[:15]:
            out.append({"title":j.get("title",""),"url":j.get("url",""),"source":"arbeitnow","platform":"arbeitnow","description":(j.get("description","") or "")[:300],"score":0})
    except Exception: pass
    return out

def _gh_extra(q=""):
    out=[]
    def one(c):
        r=[]
        try:
            d=json.loads(_get("https://boards-api.greenhouse.io/v1/boards/"+c+"/jobs", timeout=8) or "{}")
            for j in d.get("jobs",[])[:4]:
                r.append({"title":j.get("title",""),"url":j.get("absolute_url",""),"source":"greenhouse/"+c,"platform":"greenhouse","description":"","score":0})
        except Exception: pass
        return r
    with _cf.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(one, GH_EXTRA): out += r
    return out

def _lever_extra(q=""):
    out=[]
    def one(c):
        r=[]
        try:
            d=json.loads(_get("https://api.lever.co/v0/postings/"+c+"?mode=json", timeout=8) or "[]")
            for j in (d or [])[:4]:
                r.append({"title":j.get("text",""),"url":j.get("hostedUrl",""),"source":"lever/"+c,"platform":"lever","description":"","score":0})
        except Exception: pass
        return r
    with _cf.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(one, LEVER_EXTRA): out += r
    return out

def _ashby_extra(q=""):
    out=[]
    def one(c):
        r=[]
        try:
            d=json.loads(_get("https://api.ashbyhq.com/posting-api/job-board/"+c, timeout=8) or "{}")
            for j in (d.get("jobs") or [])[:4]:
                r.append({"title":j.get("title",""),"url":j.get("jobUrl",""),"source":"ashby/"+c,"platform":"ashby","description":"","score":0})
        except Exception: pass
        return r
    with _cf.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(one, ASHBY_EXTRA): out += r
    return out

def _rss_extra(q=""):
    out=[]
    with _cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda x: _rss_jobs(x[1], x[0]), RSS_EXTRA): out += r
    return out

_orig_gather_all = gather_all
def gather_all(q=""):
    jobs=[]
    try: jobs=list(_orig_gather_all(q))
    except Exception: jobs=[]
    futs=[]
    with _cf.ThreadPoolExecutor(max_workers=7) as ex:
        futs=[ex.submit(f, q) for f in (_linkedin_guest,_indeed_rss,_arbeitnow,_gh_extra,_lever_extra,_ashby_extra,_rss_extra,_glassdoor_rss,_wellfound,_dice_rss,_angel_co,_builtin_sf)]
        for fu in _cf.as_completed(futs, timeout=50):
            try: jobs += fu.result(timeout=1) or []
            except Exception: pass
    seen=set(); ded=[]
    for j in jobs:
        # Add platform field if missing (use source as platform)
        if 'platform' not in j and 'source' in j:
            j['platform'] = j['source']
        u=j.get("url") or j.get("title")
        if not u or u in seen: continue
        seen.add(u); ded.append(j)
    return ded





# ============ WORKING DIRECT APIS (Phase 2 - Fixed) ============
def search_usajobs(q=""):
    """USAJobs government API (free, no auth needed)"""
    out = []
    try:
        url = f"https://data.usajobs.gov/api/Search/Results?Keyword={_up.quote(q)}&WhoMayApply=public&ResultsPerPage=20"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Host": "data.usajobs.gov",
            "Authorization-Key": "DEMO_KEY"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            for j in data.get("SearchResult", {}).get("SearchResultItems", [])[:20]:
                out.append({
                    "title": j.get("MatchedObjectDescriptor", {}).get("PositionTitle", ""),
                    "url": j.get("MatchedObjectDescriptor", {}).get("PositionURI", ""),
                    "description": _strip(j.get("MatchedObjectDescriptor", {}).get("PositionLocationDisplay", ""))[:400],
                    "source": "usajobs",
                    "platform": "usajobs",
                    "score": _score(j.get("MatchedObjectDescriptor", {}).get("PositionTitle", ""), q)
                })
    except Exception:
        pass
    return out

def search_devitjobs(q=""):
    """DevITJobs UK tech jobs RSS"""
    out = []
    try:
        raw = _get("https://devitjobs.uk/job_feed.xml", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "devitjobs",
                    "platform": "devitjobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_authenticjobs(q=""):
    """Authentic Jobs RSS feed"""
    out = []
    try:
        raw = _get("https://authenticjobs.com/rss/", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "authenticjobs",
                    "platform": "authenticjobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_golangprojects(q=""):
    """Golang Projects RSS feed"""
    out = []
    try:
        raw = _get("https://golangprojects.com/golang-jobs.xml", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "golangprojects",
                    "platform": "golangprojects",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def search_euremotejobs(q=""):
    """EU Remote Jobs RSS feed"""
    out = []
    try:
        raw = _get("https://euremotejobs.com/feed/", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 20:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "euremotejobs",
                    "platform": "euremotejobs",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out



# ============ BLOCKED SITES (Private Engine Bridge Only) ============
def _glassdoor_rss(q=""):
    """Glassdoor RSS (limited, needs bridge for full access)"""
    out = []
    try:
        # Glassdoor has limited public RSS for some categories
        raw = _get(f"https://www.glassdoor.com/search/rss.htm?searchSource=GN_TEXTBOX&sc.keyword={_up.quote(q)}", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "glassdoor",
                    "platform": "glassdoor",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def _wellfound(q=""):
    """Wellfound (AngelList) job search"""
    out = []
    try:
        # Wellfound has a public job search endpoint
        url = f"https://wellfound.com/api/v2/search/jobs?q={_up.quote(q)}&page=1"
        data = json.loads(_get(url, timeout=10) or "{}")
        for j in data.get("jobs", [])[:15]:
            out.append({
                "title": j.get("title", ""),
                "url": f"https://wellfound.com/jobs/{j.get('id', '')}",
                "description": _strip(j.get("description", ""))[:400],
                "source": "wellfound",
                "platform": "wellfound",
                "score": _score(j.get("title", "") + " " + j.get("description", ""), q)
            })
    except Exception:
        pass
    return out

def _dice_rss(q=""):
    """Dice RSS feed (limited)"""
    out = []
    try:
        raw = _get(f"https://www.dice.com/jobs?q={_up.quote(q)}&format=rss", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "dice",
                    "platform": "dice",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

def _angel_co(q=""):
    """Angel.co jobs (now Wellfound, but legacy endpoint)"""
    out = []
    try:
        url = f"https://angel.co/api/v1/search/jobs?query={_up.quote(q)}"
        data = json.loads(_get(url, timeout=10) or "{}")
        for j in data.get("results", [])[:15]:
            out.append({
                "title": j.get("title", ""),
                "url": j.get("url", ""),
                "description": _strip(j.get("description", ""))[:400],
                "source": "angellist",
                "platform": "angellist",
                "score": _score(j.get("title", "") + " " + j.get("description", ""), q)
            })
    except Exception:
        pass
    return out

def _builtin_sf(q=""):
    """Built In SF tech jobs RSS"""
    out = []
    try:
        raw = _get("https://www.builtinsf.com/jobs/rss", timeout=10)
        if not raw:
            return out
        root = _ET.fromstring(raw)
        for item in root.iter('item'):
            if len(out) >= 15:
                break
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = item.findtext('description') or ''
            if title and link:
                out.append({
                    "title": title,
                    "url": link,
                    "source": "builtinsf",
                    "platform": "builtinsf",
                    "description": re.sub('<[^>]+>', '', desc)[:300],
                    "score": _score(title + " " + desc, q)
                })
    except Exception:
        pass
    return out

SOURCE_COUNT = len(RSS_FEEDS) + len(GH_EXTRA) + len(LEVER_EXTRA) + len(ASHBY_EXTRA) + len(RSS_EXTRA) + 49
