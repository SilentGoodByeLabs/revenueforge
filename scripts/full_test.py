#!/usr/bin/env python3
import requests, sys, re, urllib3
urllib3.disable_warnings()
PRIVATE="http://127.0.0.1:8502"; PUBLIC="https://revenueforge-api.onrender.com"; E="fulltest@revenueforge.test"
# (name, path, min_bytes, where) where: both|priv|pub  -> other side must 404
PAGES=[("Home","/",1000,"both"),("Login page","/login",300,"pub"),("Login html","/login.html",300,"pub"),
("Portal","/portal",20000,"pub"),("Settings","/settings",500,"priv"),("Job Agent","/jobagent",500,"priv"),
("Pipeline","/pipeline",500,"priv"),("Outreach","/outreach",500,"priv"),("Followups","/followups",500,"priv"),
("Analytics","/analytics",500,"priv"),("Products","/products",500,"priv"),("Prospects","/prospects",500,"priv"),
("Scaling","/scaling",500,"priv"),("Security","/security",500,"priv"),("Audit","/audit",500,"priv"),
("Command","/command",500,"priv"),("CV","/cv",500,"both"),("CV Builder","/cvbuilder",500,"both"),
("Proposal","/proposal",500,"both"),("Admin subs","/admin/subs",300,"priv"),("Admin projects","/admin/projects",300,"priv"),
("Admin invites","/admin/invites",300,"priv"),("Contact","/contact.html",200,"pub"),("Marketplace","/marketplace.html",200,"pub"),
("Health","/health",10,"both"),("Favicon","/favicon.ico",0,"both")]
API_GETS=[("/api/search?q=python","search","both"),("/api/search-hiring?q=python&limit=3&email="+E,"search-hiring","both"),
("/api/sub/"+E,"subscription","both"),("/api/my/products?email="+E,"my-products","both")]
API_POSTS=[("/api/save-profile",{"email":E,"skills":"python, sql"},"both"),("/api/engine-toggle",{"email":E,"on":False},"priv"),
("/api/save-cv",{"email":E,"name":"ZZ FullTest"},"both"),("/api/add-to-pipeline",{"email":E,"title":"ZZ-FULLTEST","url":"http://zz.test"},"priv"),
("/api/move-stage",{"email":E,"index":0,"stage":"Contacted"},"priv"),("/api/chat",{"message":"hi"},"both"),
("/api/invites",{"code":"ZZTEST1"},"priv"),("/jobs/ingest",{"jobs":[]},"priv"),
("/api/signin",{"email":E,"password":"x"},"pub"),("/api/verify",{"email":E,"password":"x"},"pub"),("/api/auth/login",{"email":E,"password":"x"},"pub")]
R=[]
def rec(s,a,n,d):
    R.append((s,a,n,d)); print(f"[{'+' if s=='PASS' else '!' if s=='FAIL' else '?'}] {a:4s} {n:24s} {d}")
def pages(b,tag,t):
    for n,p,mb,where in PAGES:
        should = where in ("both",tag)
        try:
            r=requests.get(b+p,timeout=t)
            if should:
                rec("PASS" if (r.status_code in (200,204) and len(r.content)>=mb) else "FAIL",tag,n,f"{r.status_code} {len(r.content)}B")
            else:
                rec("PASS" if r.status_code==404 else "FAIL",tag,n,f"gated:{r.status_code} (want 404)")
        except Exception as e: rec("FAIL",tag,n,f"ERR {type(e).__name__}")
def apigets(b,tag,t):
    for p,n,where in API_GETS:
        should = where in ("both",tag)
        try:
            r=requests.get(b+p,timeout=t)
            if should:
                ok=r.status_code==200
                try: r.json()
                except Exception: ok=False
                rec("PASS" if ok else "FAIL",tag,"GET "+n,f"{r.status_code}")
            else: rec("PASS" if r.status_code==404 else "FAIL",tag,"GET "+n,f"gated:{r.status_code}")
        except Exception as e: rec("FAIL",tag,"GET "+n,f"ERR {type(e).__name__}")
def apiposts(b,tag,t):
    for p,d,where in API_POSTS:
        should = where in ("both",tag)
        try:
            r=requests.post(b+p,json=d,timeout=t)
            if should: rec("PASS" if r.status_code in (200,201,303) else "FAIL",tag,"POST "+p,f"{r.status_code}")
            else: rec("PASS" if r.status_code==404 else "FAIL",tag,"POST "+p,f"gated:{r.status_code}")
        except Exception as e: rec("FAIL",tag,"POST "+p,f"ERR {type(e).__name__}")
def login(b,tag,t):
    try:
        r=requests.get(b+"/api/login-get",params={"email":E,"password":"T1234","g-recaptcha-response":"x"},timeout=t,allow_redirects=False)
        if tag=="pub":
            loc=r.headers.get("location","")
            rec("PASS" if (r.status_code==303 and "/portal" in loc) else "FAIL",tag,"Login flow",f"{r.status_code} -> {loc[:30]}")
        else:
            rec("PASS" if r.status_code==404 else "FAIL",tag,"Login flow gated",f"{r.status_code} (want 404)")
    except Exception as e: rec("FAIL",tag,"Login flow",f"ERR {type(e).__name__}")
def cv(b,tag,t):
    try:
        x=requests.get(b+"/cvbuilder",timeout=t).text
        ins=len(re.findall(r"<input",x,re.I)); photo="type='file'" in x or 'type="file"' in x; prt="window.print()" in x
        rec("PASS" if (ins>=6 and photo and prt) else "FAIL",tag,"CV features",f"inputs={ins} photo={photo} print={prt}")
    except Exception as e: rec("FAIL",tag,"CV features",f"ERR {type(e).__name__}")
def prop(b,tag,t):
    try:
        r=requests.get(b+"/proposal",timeout=t); kw=[w for w in ["professional","experience","proposal","deliver"] if w in r.text.lower()]
        rec("PASS" if (len(kw)>=2 and len(r.text)>2000) else "WARN",tag,"Proposal page",f"kw={len(kw)} size={len(r.text)}")
    except Exception as e: rec("FAIL",tag,"Proposal page",f"ERR {type(e).__name__}")
def homecheck(b,tag,t):
    try:
        x=requests.get(b+"/",timeout=t).text
        if tag=="priv":
            rec("PASS" if "Owner Briefing" in x else "FAIL",tag,"Home=briefing",f"briefing={'Owner Briefing' in x}")
        else:
            rec("PASS" if "Owner Briefing" not in x else "FAIL",tag,"Home=marketing",f"marketing={'Owner Briefing' not in x}")
    except Exception as e: rec("FAIL",tag,"Home check",f"ERR {type(e).__name__}")
mode=sys.argv[1] if len(sys.argv)>1 else "all"
if mode in ("private","all"):
    print("\n===== PRIVATE ====="); tag="priv"
    pages(PRIVATE,tag,15); apigets(PRIVATE,tag,30); apiposts(PRIVATE,tag,30); login(PRIVATE,tag,15); cv(PRIVATE,tag,15); prop(PRIVATE,tag,15); homecheck(PRIVATE,tag,15)
if mode in ("public","all"):
    print("\n===== PUBLIC ====="); tag="pub"
    try: requests.get(PUBLIC+"/health",timeout=120); print("(awake)")
    except Exception: print("(waking...)")
    pages(PUBLIC,tag,120); apigets(PUBLIC,tag,120); apiposts(PUBLIC,tag,120); login(PUBLIC,tag,120); cv(PUBLIC,tag,120); prop(PUBLIC,tag,120); homecheck(PUBLIC,tag,120)
p_=sum(1 for r in R if r[0]=="PASS"); f_=sum(1 for r in R if r[0]=="FAIL"); w_=sum(1 for r in R if r[0]=="WARN")
print(f"\n===== SUMMARY: {p_} PASS / {w_} WARN / {f_} FAIL =====")
for s,a,n,d in R:
    if s=="FAIL": print(f"  FIX: [{a}] {n}: {d}")
