#!/usr/bin/env python3
"""RevenueForge test: each side tests ONLY what it owns. Clean output."""
import requests, sys, re, urllib3
urllib3.disable_warnings()
PRIVATE="http://127.0.0.1:8502"; PUBLIC="https://revenueforge-api.onrender.com"; E="fulltest@revenueforge.test"
R=[]
def rec(s,n,d):
    R.append((s,n,d)); print(f"[{'+' if s=='PASS' else '!'}] {n:28s} {d}")

# ---- PRIVATE (owner console) ----
PRIV_PAGES=[("Home=briefing","/",1000),("Settings","/settings",500),("Job Agent","/jobagent",500),
("Pipeline","/pipeline",500),("Outreach","/outreach",500),("Followups","/followups",500),
("Analytics","/analytics",500),("Products","/products",500),("Prospects","/prospects",500),
("Scaling","/scaling",500),("Security","/security",500),("Audit","/audit",500),("Command","/command",500),
("CV","/cv",500),("CV Builder","/cvbuilder",500),("Proposal","/proposal",500),
("Admin subs","/admin/subs",300),("Admin projects","/admin/projects",300),("Admin invites","/admin/invites",300),
("Health","/health",10),("Favicon","/favicon.ico",0)]
PRIV_GET=[("/api/search?q=py","search"),("/api/search-hiring?q=py&limit=2","search-hiring"),
("/api/sub/"+E,"subscription"),("/api/my/products?email="+E,"my-products")]
PRIV_POST=[("/api/save-profile",{"email":E,"skills":"py"}),("/api/engine-toggle",{"email":E,"on":False}),
("/api/save-cv",{"email":E,"name":"ZZ"}),("/api/add-to-pipeline",{"email":E,"title":"ZZ","url":"http://z"}),
("/api/move-stage",{"email":E,"index":0,"stage":"Contacted"}),("/api/chat",{"message":"hi"}),
("/api/invites",{"code":"ZZ1"}),("/jobs/ingest",{"jobs":[]})]
PRIV_BLOCKED=["/portal","/login","/login.html","/marketplace.html","/contact.html"]

# ---- PUBLIC (customer site) ----
PUB_PAGES=[("Home=marketing","/",1000),("Login page","/login",300),("Login html","/login.html",300),
("Portal","/portal",20000),("Marketplace","/marketplace.html",200),("Contact","/contact.html",200),
("CV","/cv",500),("CV Builder","/cvbuilder",500),("Proposal","/proposal",500),
("Health","/health",10),("Favicon","/favicon.ico",0)]
PUB_GET=[("/api/search-hiring?q=py&limit=2","search-hiring"),("/api/sub/"+E,"subscription"),
("/api/my/products?email="+E,"my-products")]
PUB_POST=[("/api/save-profile",{"email":E,"skills":"py"}),("/api/save-cv",{"email":E,"name":"ZZ"}),
("/api/chat",{"message":"hi"}),("/api/signin",{"email":E,"password":"x"}),
("/api/verify",{"email":E,"password":"x"}),("/api/auth/login",{"email":E,"password":"x"})]
PUB_BLOCKED=["/settings","/jobagent","/pipeline","/admin/subs","/command","/audit","/security"]

def pages(b,items,t):
    for n,p,mb in items:
        try:
            r=requests.get(b+p,timeout=t)
            rec("PASS" if (r.status_code in (200,204) and len(r.content)>=mb) else "FAIL",n,f"{r.status_code} {len(r.content)}B")
        except Exception as e: rec("FAIL",n,f"ERR {type(e).__name__}")
def gets(b,items,t):
    for p,n in items:
        try:
            r=requests.get(b+p,timeout=t); ok=r.status_code==200
            try: r.json()
            except Exception: ok=False
            rec("PASS" if ok else "FAIL","GET "+n,f"{r.status_code}")
        except Exception as e: rec("FAIL","GET "+n,f"ERR {type(e).__name__}")
def posts(b,items,t):
    for p,d in items:
        try:
            r=requests.post(b+p,json=d,timeout=t)
            rec("PASS" if r.status_code in (200,201,303) else "FAIL","POST "+p,f"{r.status_code}")
        except Exception as e: rec("FAIL","POST "+p,f"ERR {type(e).__name__}")
def cv(b,t):
    try:
        x=requests.get(b+"/cvbuilder",timeout=t).text
        ins=len(re.findall(r"<input",x,re.I)); photo=("type='file'" in x or 'type="file"' in x); prt="window.print()" in x
        rec("PASS" if (ins>=6 and photo and prt) else "FAIL","CV features",f"inputs={ins} photo={photo} print={prt}")
    except Exception as e: rec("FAIL","CV features",f"ERR {type(e).__name__}")
def prop(b,t):
    try:
        r=requests.get(b+"/proposal",timeout=t); kw=len([w for w in ["professional","experience","proposal","deliver"] if w in r.text.lower()])
        rec("PASS" if (kw>=2 and len(r.text)>2000) else "WARN","Proposal",f"kw={kw} size={len(r.text)}")
    except Exception as e: rec("FAIL","Proposal",f"ERR {type(e).__name__}")
def home(b,tag,t):
    try:
        x=requests.get(b+"/",timeout=t).text
        ok=("Owner Briefing" in x) if tag=="priv" else ("Owner Briefing" not in x)
        rec("PASS" if ok else "FAIL","Home type","briefing" if tag=="priv" else "marketing")
    except Exception as e: rec("FAIL","Home type",f"ERR {type(e).__name__}")
def separation(b,blocked,t,label):
    ok=True
    for p in blocked:
        try:
            if requests.get(b+p,timeout=t).status_code!=404: ok=False
        except Exception: ok=False
    rec("PASS" if ok else "FAIL","Separation: "+label,f"{len(blocked)} blocked pages all 404")

mode=sys.argv[1] if len(sys.argv)>1 else "all"
if mode in ("private","all"):
    print("\n===== PRIVATE ENGINE (owner console) ====="); R.clear()
    pages(PRIVATE,PRIV_PAGES,15); gets(PRIVATE,PRIV_GET,30); posts(PRIVATE,PRIV_POST,30)
    cv(PRIVATE,15); prop(PRIVATE,15); home(PRIVATE,"priv",15); separation(PRIVATE,PRIV_BLOCKED,15,"public pages blocked")
    p_=sum(1 for r in R if r[0]=="PASS"); f_=sum(1 for r in R if r[0]=="FAIL")
    print(f"\n--- PRIVATE: {p_} PASS / {f_} FAIL ---")
    for s,n,d in R:
        if s=="FAIL": print(f"  FIX: {n}: {d}")
if mode in ("public","all"):
    print("\n===== PUBLIC SITE (customer) ====="); R.clear()
    try: requests.get(PUBLIC+"/health",timeout=120)
    except Exception: pass
    pages(PUBLIC,PUB_PAGES,120); gets(PUBLIC,PUB_GET,120); posts(PUBLIC,PUB_POST,120)
    cv(PUBLIC,120); prop(PUBLIC,120); home(PUBLIC,"pub",120); separation(PUBLIC,PUB_BLOCKED,120,"owner pages blocked")
    p_=sum(1 for r in R if r[0]=="PASS"); f_=sum(1 for r in R if r[0]=="FAIL")
    print(f"\n--- PUBLIC: {p_} PASS / {f_} FAIL ---")
    for s,n,d in R:
        if s=="FAIL": print(f"  FIX: {n}: {d}")
