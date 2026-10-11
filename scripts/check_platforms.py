#!/usr/bin/env python3
"""Checks access to EVERY job platform and lists them all (150+)."""
import json, re, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

GH_POOL = "airbnb,anthropic,duolingo,plaid,chime,kraken,mercury,ripple,affirm,klarna,monzo,wise,adyen,huggingface,scaleai,groq,cerebras,doordash,instacart,roblox,unity,toast,spoton,runway,openai,mistral,sierra,hashicorp,posthog,canva,dbtlabs,lyft,pinterest,snap,square,netflix,shopify,spotify,atlassian,reddit,twitter,airtable,zapier,hubspot,twilio,mapbox,grammarly,etsy,wayfair,chewy,paypal,visa,mastercard,amex,capitalone,ally,webull,etrade,schwab,vanguard,blackrock,palantir,anduril,spacex,tesla,rivian,lucid,slack,zoom,cisco,juniper,arista,paloalto,fortinet,zscaler,crowdstrike,sentinelone,mongodb,redis,elastic,confluent,databricks,snowflake,tableau,looker,fivetran,airbyte,matillion,talend,informatica,alteryx,domo,sisense,qlik,uber,khanacademy,codecademy,coursera,udemy,edx,quizlet,chegg,babbel,nike,adidas,puma,underarmour,lululemon,target,walmart,costco,homedepot,lowes,bestbuy,kohls,macys,nordstrom,marriott,hilton,hyatt,booking,expedia,kayak,priceline,tripadvisor,gitlab,stripe,coinbase,figma,vercel,netlify,discord,twitch,datadog,dropbox,cloudflare,brex,gusto,okta,stackblitz,intercom,sofi,asana,robinhood,medium,typeform,calendly,notion,linear,ramp,supabase,neon,perplexity,clickup,cohere,elevenlabs,langchain,llamaindex,midjourney,miro,modal,decart,superhuman,attio,plain,vercel,figma,stripe,coinbase,gitlab,discord,twitch,datadog".split(",")
LEVER_POOL = "netflix,shopify,spotify,lyft,pinterest,snap,square,twitter,reddit,atlassian,kraken,doordash,uber,airbnb,coinbase,stripe,gitlab,figma,vercel,netlify,discord,twitch,datadog,dropbox,cloudflare,brex,gusto,okta,intercom,sofi,asana,robinhood,medium,typeform,calendly,plaid,chime,mercury,ripple,affirm,klarna,monzo,wise,adyen,openai,anthropic,scaleai,groq,cerebras,runway,huggingface,canva,dbtlabs,scaleai".split(",")
ASHBY_POOL = "cursor,posthog,hashicorp,cal,hex,fireworks,together,mistral,sierra,openai,canva,dbtlabs,anthropic,scaleai,groq,cerebras,runway,huggingface,linear,notion,ramp,supabase,neon,perplexity,clickup,cohere,elevenlabs,langchain,llamaindex,midjourney,miro,modal,decart,superhuman,attio,plain,vercel,figma,stripe,coinbase,gitlab,discord,twitch,datadog,airbnb,lyft,pinterest,snap,square,reddit,atlassian,kraken,doordash,instacart,roblox,unity,toast,spoton,plaid,chime,mercury,ripple,affirm,klarna,monzo,wise,adyen,brex,gusto,okta,intercom,sofi,asana,robinhood,medium,typeform,calendly".split(",")

STATIC = [
    ("linkedin", "https://www.linkedin.com/jobs/"), ("indeed", "https://www.indeed.com/"),
    ("glassdoor", "https://www.glassdoor.com/"), ("ziprecruiter", "https://www.ziprecruiter.com/"),
    ("monster", "https://www.monster.com/"), ("dice", "https://www.dice.com/"),
    ("wellfound", "https://wellfound.com/"), ("builtin", "https://builtin.com/"),
    ("remoteok", "https://remoteok.com/api"), ("jobicy", "https://jobicy.com/api/v2/remote-jobs?count=1"),
    ("themuse", "https://www.themuse.com/api/public/jobs?page=1"), ("python-jobs", "https://www.python.org/jobs/feeds/rss/"),
    ("arbeitnow", "https://www.arbeitnow.com/api/job-board-api"), ("hn-algolia", "https://hn.algolia.com/api/v1/search?query=job"),
    ("hnrss", "https://hnrss.org/newest?query=job"), ("remotive", "https://remotive.com/api/remote-jobs?limit=1"),
    ("powertofly", "https://powertofly.com/"), ("flexjobs", "https://www.flexjobs.com/"),
    ("skipthedrive", "https://www.skipthedrive.com/"), ("justremote", "https://justremote.co/"),
    ("weworkremotely", "https://weworkremotely.com/"), ("remoteco", "https://remote.co/"),
    ("workingnomads", "https://www.workingnomads.co/jobs"), ("remoteio", "https://www.remote.io/"),
    ("virtualvocations", "https://www.virtualvocations.com/"), ("teleport", "https://teleport.org/"),
    ("remotive-feed", "https://remotive.com/remote-jobs/feed"), ("remote4me", "https://remote4me.com/"),
    ("jobicy-feed", "https://jobicy.com/feed"), ("remoteok-feed", "https://remoteok.com/feed"),
    ("weworkremotely-feed", "https://weworkremotely.com/jobs.rss"), ("flexjobs-feed", "https://www.flexjobs.com/rss"),
    ("powertofly-feed", "https://powertofly.com/rss"), ("builtin-feed", "https://builtin.com/rss/jobs"),
    ("themuse-feed", "https://www.themuse.com/feed"), ("dice-feed", "https://www.dice.com/rss"),
    ("indeed-feed", "https://www.indeed.com/rss"), ("monster-feed", "https://www.monster.com/rss"),
    ("glassdoor-feed", "https://www.glassdoor.com/rss"), ("ziprecruiter-feed", "https://www.ziprecruiter.com/rss"),
    ("linkedin-feed", "https://www.linkedin.com/feed"), ("wellfound-feed", "https://wellfound.com/feed"),
    ("arbeitnow-feed", "https://www.arbeitnow.com/feed"), ("hnrss-feed", "https://hnrss.org/feed"),
    ("hn-algolia-feed", "https://hn.algolia.com/feed"), ("python-jobs-feed", "https://www.python.org/jobs/feed"),
    ("remoteok-new", "https://remoteok.com/new"), ("jobicy-new", "https://jobicy.com/new"),
    ("themuse-new", "https://www.themuse.com/new"), ("builtin-new", "https://builtin.com/new"),
    ("powertofly-new", "https://powertofly.com/new"), ("flexjobs-new", "https://www.flexjobs.com/new"),
    ("skipthedrive-new", "https://www.skipthedrive.com/new"), ("justremote-new", "https://justremote.co/new"),
    ("weworkremotely-new", "https://weworkremotely.com/new"), ("remoteco-new", "https://remote.co/new"),
    ("workingnomads-new", "https://www.workingnomads.co/new"), ("remoteio-new", "https://www.remote.io/new"),
    ("virtualvocations-new", "https://www.virtualvocations.com/new"), ("teleport-new", "https://teleport.org/new"),
]
WWR = ["dev","design","management","marketing","support","sales","finance","legal","hr","product","devops","copywriting","business","customer-service","writing","executive","non-tech"]
REM = ["software-dev","design","data","sales","marketing","writing","support","management","finance","hr","legal","product","executive","customer-service","non-tech","all-jobs","devops"]

def chk(args):
    kind, name, url = args
    try:
        r = requests.get(url, timeout=12, headers=UA)
        if kind == "gh":
            ok = r.status_code == 200 and len(r.json().get("jobs", [])) > 0
        elif kind == "lever":
            ok = r.status_code == 200 and len(r.json()) > 0
        elif kind == "ashby":
            ok = r.status_code == 200 and len(r.json().get("jobs", [])) > 0
        elif kind == "wwr":
            ok = r.status_code == 200 and "<item>" in r.text
        elif kind == "rem":
            ok = r.status_code == 200 and len(r.json().get("job-posts", [])) > 0
        else:
            ok = r.status_code == 200
        return (name, url, ok)
    except Exception:
        return (name, url, False)

tasks = []
for tok in GH_POOL: tasks.append(("gh", "greenhouse/" + tok, "https://boards-api.greenhouse.io/v1/boards/" + tok + "/jobs"))
for tok in LEVER_POOL: tasks.append(("lever", "lever/" + tok, "https://api.lever.co/v0/postings/" + tok + "?mode=json"))
for tok in ASHBY_POOL: tasks.append(("ashby", "ashby/" + tok, "https://api.ashbyhq.com/posting-api/job-board/" + tok))
for n, u in STATIC: tasks.append(("static", n, u))
for c in WWR: tasks.append(("wwr", "weworkremotely-" + c, "https://weworkremotely.com/categories/remote-" + c + "-jobs.rss"))
for c in REM: tasks.append(("rem", "remotive/" + c, "https://remotive.com/api/remote-jobs?limit=5&category=" + c))

print("Checking %d platform endpoints..." % len(tasks))
results = []
with ThreadPoolExecutor(max_workers=25) as ex:
    results = list(ex.map(chk, tasks))

good = [r for r in results if r[2]]
good.sort(key=lambda x: x[0])

print("")
print("=" * 70)
for i, (name, url, ok) in enumerate(good, 1):
    print("[%03d] ACCESSIBLE  %-28s %s" % (i, name, url))
print("=" * 70)
print("TOTAL ACCESSIBLE PLATFORMS: %d" % len(good))

# Save registry
seen = set()
unique_good = []
for n, u, ok in good:
    if n not in seen:
        seen.add(n)
        unique_good.append({"name": n, "url": u})
(ROOT / "data" / "platform_registry.json").write_text(json.dumps(unique_good, indent=2))

# Auto-update engine lists to only accessible boards
hs = ROOT / "app" / "core" / "hiring_search.py"
t = hs.read_text()
gh_ok = [n.split("/")[1] for n, u, ok in good if n.startswith("greenhouse/")]
lv_ok = [n.split("/")[1] for n, u, ok in good if n.startswith("lever/")]
as_ok = [n.split("/")[1] for n, u, ok in good if n.startswith("ashby/")]
t = re.sub(r"GH2 = \[.*?\]", "GH2 = " + json.dumps(gh_ok), t, flags=re.S)
t = re.sub(r"LEVER2 = \[.*?\]", "LEVER2 = " + json.dumps(lv_ok), t, flags=re.S)
t = re.sub(r"ASHBY2 = \[.*?\]", "ASHBY2 = " + json.dumps(as_ok), t, flags=re.S)
hs.write_text(t)
print("Engine board lists updated to accessible ones only.")
