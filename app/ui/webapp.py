import os, re, json, secrets
from datetime import datetime
from pathlib import Path
from fastapi import Request, FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

def now():
    from datetime import datetime as _dt
    return _dt.now().strftime("%Y-%m-%d %H:%M")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
try:
    from app.core import hiring_search as HS
except Exception:
    HS = None



app = FastAPI(title="RevenueForge Control Center")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])



# ============ PUSH PIPELINE (receive jobs from private worker) ============

RF_ENV = os.environ.get("RF_ENV", "private")

PRIVATE_ONLY = {"/settings","/jobagent","/pipeline","/outreach","/followups","/analytics","/command","/audit","/security","/admin/subs","/admin/projects","/admin/invites","/prospects","/scaling","/products","/api/engine-toggle","/api/run","/api/search-now","/api/settings","/api/invites","/api/move-stage","/api/add-to-pipeline","/jobs/ingest"}
PUBLIC_ONLY = {"/login","/login.html","/portal","/marketplace.html","/contact.html","/api/login-get","/api/paystack/init","/api/paystack/verify"}


MARKETING = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RevenueForge - Professional Job Search Platform</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#1e293b}header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:80px 20px;text-align:center}header h1{font-size:46px;margin-bottom:16px}header p{font-size:19px;max-width:640px;margin:0 auto;opacity:.92}.wrap{max-width:1100px;margin:0 auto;padding:60px 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:26px;margin:36px 0}.card{background:#f8fafc;padding:28px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}.card h3{color:#667eea;margin-bottom:10px}.cta{background:#667eea;color:#fff;padding:15px 30px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block;margin:8px}.cta:hover{background:#5568d3}footer{background:#1e293b;color:#94a3b8;text-align:center;padding:36px}</style></head>
<body><header><h1>RevenueForge</h1><p>Professional job search across 291+ sources with personalized proposals and a print-ready CV builder.</p><a class="cta" href="/login.html">Get Started</a><a class="cta" href="/marketplace.html">Marketplace</a></header>
<div class="wrap"><div class="grid">
<div class="card"><h3>Smart Job Search</h3><p>Live matches from 291+ platforms scored against your skills.</p></div>
<div class="card"><h3>CV Builder</h3><p>Photo upload, every section, print / save-as-PDF output.</p></div>
<div class="card"><h3>Proposal Generator</h3><p>Long-form professional proposals written to win the job.</p></div>
<div class="card"><h3>Pipeline Tracking</h3><p>Every application tracked from found to hired.</p></div>
<div class="card"><h3>Marketplace</h3><p>Publish your services and get hired directly.</p></div>
<div class="card"><h3>Trial & Billing</h3><p>24-hour free trial, simple upgrades, invite codes.</p></div>
</div><div style="text-align:center"><a class="cta" href="/login.html">Start Free Trial</a><a class="cta" href="/contact.html">Contact</a></div></div>
<footer>&copy; 2026 RevenueForge</footer></body></html>"""
def _env_for(request: Request) -> str:
    override = os.environ.get("RF_ENV", "")
    if override in ("public", "private"):
        return override
    host = request.headers.get("host", "")
    return "private" if host.startswith(("127.0.0.1", "localhost")) else "public"

@app.middleware("http")
async def rf_env_gate(request: Request, call_next):
    path = request.url.path
    env = _env_for(request)
    if env == "public" and path in PRIVATE_ONLY:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    if env == "private" and path in PUBLIC_ONLY:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return await call_next(request)

@app.post("/jobs/ingest")
async def jobs_ingest(request: Request):
    """Receive jobs pushed from private worker"""
    try:
        body = await request.json()
        jobs = body.get("jobs", [])
        source = body.get("source", "unknown")
        
        # Save to persistent file (survives within deploy cycle)
        pushed_file = ROOT / "data" / "pushed_jobs.json"
        pushed_file.parent.mkdir(exist_ok=True)
        
        # Merge with existing pushed jobs (dedupe by URL)
        existing = []
        if pushed_file.exists():
            try:
                existing = json.loads(pushed_file.read_text())
            except:
                existing = []
        
        # Add new jobs (dedupe)
        seen_urls = {j.get("url") for j in existing if j.get("url")}
        for j in jobs:
            url = j.get("url")
            if url and url not in seen_urls:
                existing.append(j)
                seen_urls.add(url)
        
        # Keep last 500 jobs
        existing = existing[-500:]
        
        pushed_file.write_text(json.dumps(existing, indent=2))
        
        audit(f"Pushed {len(jobs)} jobs from {source}, total now: {len(existing)}")
        return {"ok": True, "received": len(jobs), "total": len(existing)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ld(n, d):
    p = DATA / n
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    return d
def sv(n, o): (DATA / n).write_text(json.dumps(o, indent=2))
def audit(m):
    with open(DATA / "audit.log", "a") as f:
        f.write(f"{datetime.now().isoformat()}  {m}\n")

NAV = [("/", "Daily Briefing", "fa-sun"), ("/command", "Command Center", "fa-compass"),
  ("/jobagent", "Job Agent", "fa-briefcase"), ("/pipeline", "Pipeline", "fa-filter"),
  ("/analytics", "Analytics", "fa-chart-line"), ("/products", "Products", "fa-box"),
  ("/prospects", "Prospects", "fa-magnifying-glass"), ("/outreach", "Outreach", "fa-paper-plane"),
  ("/followups", "Follow-ups", "fa-rotate"), ("/settings", "Settings", "fa-gear"),
  ("/scaling", "Scaling", "fa-rocket"), ("/admin/subs", "Admin: Subscriptions", "fa-rectangle-list"),
  ("/admin/projects", "Admin: Client Projects", "fa-diagram-project"),
  ("/admin/invites", "Admin: Invite Codes", "fa-key"), ("/security", "Security", "fa-shield-halved"),
  ("/audit", "Audit Log", "fa-scroll")]

CSS = """*{box-sizing:border-box}body{margin:0;background:#f4f6fa;font:14px/1.5 -apple-system,'Segoe UI',Roboto,Arial;color:#24292f}
header{display:flex;justify-content:space-between;align-items:center;background:#fff;padding:12px 22px;border-bottom:1px solid #e6e9ef}
.brand i{color:#2f6fed}.brand b{font-size:17px}.brand span{color:#8a919c;font-size:11px;letter-spacing:2px;margin-left:8px}
.badge{background:#eef7f0;color:#1a7f37;border:1px solid #cfe8d6;padding:4px 12px;border-radius:20px;font-size:12px}
nav{display:grid;grid-template-columns:repeat(4,1fr);background:#fff;margin:18px auto 0;max-width:1180px;border:1px solid #e6e9ef;border-radius:10px;padding:10px;gap:2px}
.navi{display:flex;gap:10px;align-items:center;padding:12px 14px;color:#3b4149;text-decoration:none;border-radius:8px;font-weight:600}
.navi i{color:#2f6fed;width:18px;text-align:center}.navi:hover{background:#eef4ff}.navi.on{background:#e8f0fe;color:#1a56db}
main{max-width:1180px;margin:18px auto 60px;padding:0 12px}h1{font-size:22px;margin:6px 0 14px}
.card{background:#f8fafc;border:1px solid #e6e9ef;border-radius:10px;padding:16px 18px;margin-bottom:14px}
.card h3{margin:0 0 8px;font-size:15px}.card h3 i{color:#2f6fed;margin-right:6px}
.ok{color:#1a7f37}.ok i{margin-right:6px}.muted{color:#57606a}.err{color:#b3261e}
table{width:100%;border-collapse:collapse}td,th{padding:8px 10px;border-bottom:1px solid #e6e9ef;text-align:left}
.fab{position:fixed;right:26px;bottom:26px;background:#2f6fed;color:#fff;padding:10px 18px;border-radius:24px;text-decoration:none;font-weight:600;box-shadow:0 6px 18px rgba(47,111,237,.35)}
input,select,textarea{width:100%;padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;margin:4px 0 10px;font:inherit}
button{background:#2f6fed;border:0;color:#fff;padding:9px 16px;border-radius:8px;font-weight:600;cursor:pointer}
.bar{background:#e6e9ef;border-radius:6px;height:14px;margin:6px 0}.bar i{display:block;height:14px;background:#2f6fed;border-radius:6px}
pre{background:#fff;border:1px solid #e6e9ef;padding:10px;border-radius:8px;overflow:auto}"""

def page(path, title, body):
    nav = "".join(f'<a class="navi{" on" if path==u else ""}" href="{u}"><i class="fa-solid {ic}"></i> {lb}</a>' for u, lb, ic in NAV)
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RevenueForge - {title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>{CSS}</style></head><body>
<header><div class="brand"><i class="fa-solid fa-cubes"></i> <b>RevenueForge</b> <span>CONTROL CENTER</span></div>
<div class="badge"><i class="fa-solid fa-house-laptop"></i> Local &middot; Private</div></header>
<nav>{nav}</nav><main><h1>{title}</h1>{body}</main>
</body></html>"""

def card(ic, t, inner): return f'<div class="card"><h3><i class="fa-solid {ic}"></i> {t}</h3>{inner}</div>'
def good(t): return f'<p class="ok"><i class="fa-solid fa-circle-check"></i> {t}</p>'
def bad(t): return f'<p class="err"><i class="fa-solid fa-circle-xmark"></i> {t}</p>'
def mute(t): return f'<p class="muted">&bull; {t}</p>'

def worker_alive():
    p = Path.home() / ".rf_worker.pid"
    if p.exists():
        try:
            os.kill(int(p.read_text().strip()), 0); return True
        except Exception: pass
    return False

def gather(q=""):
    """Read from cache file instead of running slow search"""
    import json as _json
    from pathlib import Path as _Path
    
    cache_file = _Path("data/last_search.json")
    if not cache_file.exists():
        return []
    
    try:
        data = _json.loads(cache_file.read_text())
        jobs = data.get("jobs", [])
        return jobs
    except Exception:
        return []

@app.get("/jobagent", response_class=HTMLResponse)
def jobagent(page_num: int = 1):
    from urllib.parse import quote as _q
    from datetime import datetime as _DT
    import subprocess, sys as _sys, json as _J, time as _T

    # Always check if a live hunt is running or needed
    settings = ld("settings.json", {})
    freq = int(settings.get("frequency", 10))
    cache_file = Path("data/last_search.json")
    flag_file = Path("data/.hunting")

    # Check cache freshness
    cache_age_min = 999999
    jobs_count = 0
    cache_time_str = ""
    if cache_file.exists():
        try:
            cdata = _J.loads(cache_file.read_text())
            ct = _DT.strptime(cdata.get("time", ""), "%Y-%m-%d %H:%M:%S")
            cache_age_min = (_DT.now() - ct).total_seconds() / 60
            jobs_count = len(cdata.get("jobs", []))
            cache_time_str = cdata.get("time", "")
        except Exception:
            pass

    hunting_now = flag_file.exists()

    # Trigger live hunt if cache is older than configured frequency OR not hunting
    needs_hunt = cache_age_min > freq and not hunting_now
    if needs_hunt:
        try:
            flag_file.write_text(str(_T.time()))
            subprocess.Popen(
                [_sys.executable, "scripts/live_hunt.py"],
                stdout=open("/tmp/live_hunt.log", "w"),
                stderr=subprocess.STDOUT
            )
            hunting_now = True
        except Exception:
            pass

    # Load jobs from cache (fresh or old, always showing cache contents)
    jobs = []
    try:
        if cache_file.exists():
            jobs = _J.loads(cache_file.read_text()).get("jobs", [])
    except Exception:
        jobs = []

    # Filter HN noise
    real_jobs = []
    for j in jobs:
        source = str(j.get("source", ""))
        title = str(j.get("title", "")).lower()
        if ("hn-" in source or "hnrss" in source):
            if not any(kw in title for kw in ["hiring", "job", "engineer", "developer", "python", "designer", "remote", "intern"]):
                continue
        real_jobs.append(j)

    # Profile for match %
    profile = ld("profile.json", {})
    skills = [s.strip().lower() for s in str(profile.get("skills", "")).split(",") if s.strip()]
    target_words = [w.strip().lower() for w in str(profile.get("target", "")).split(",") if w.strip()]
    location = str(profile.get("location", "")).lower()

    def _pct(j):
        b = (str(j.get("title", "")) + " " + str(j.get("description", ""))).lower()
        score = 0.0
        if skills:
            hits = sum(1 for s in skills if s in b)
            score += 50.0 * hits / len(skills)
            if hits:
                score += 10
        else:
            score += 30
        if target_words and any(w in b for w in target_words):
            score += 15
        if "remote" in b:
            score += 10
        if location and location.split()[0] in b:
            score += 10
        for lvl in ["senior", "mid", "junior", "lead"]:
            if lvl in b:
                score += 5
                break
        return int(min(100, score))

    real_jobs.sort(key=_pct, reverse=True)

    # Pagination
    per = 50
    total = len(real_jobs)
    pages = max(1, (total + per - 1) // per)
    page_num = max(1, min(page_num, pages))
    slice_jobs = real_jobs[(page_num - 1) * per: page_num * per]

    # Build HTML
    html = "<div class='card'>"
    html += "<h3><i class='fa-solid fa-bolt'></i> Live Job Feed</h3>"
    if hunting_now:
        html += "<p class='ok'><i class='fa-solid fa-spinner fa-spin'></i> <strong>Hunting live across all platforms...</strong> New jobs will appear automatically. Page refreshes every 15 seconds.</p>"
    else:
        mins_left = int(freq - cache_age_min) if cache_age_min < freq else 0
        if mins_left > 0:
            html += "<p class='ok'>Cache refreshed " + str(int(cache_age_min)) + " min ago. Next live hunt in " + str(mins_left) + " min. Page refreshes every 15 seconds.</p>"
        else:
            html += "<p class='ok'>Showing latest jobs. Next live hunt in a few seconds. Page refreshes every 15 seconds.</p>"
    html += "<p class='muted'><strong>" + str(jobs_count) + "</strong> total jobs cached for public engine. Showing <strong>" + str(total) + "</strong> filtered jobs below.</p>"
    html += "<form method='post' action='/api/hunt-now' style='display:inline'><button type='submit'>Hunt live now</button></form> "
    html += "<a href='/cvbuilder'>CV Builder</a>"
    html += "</div>"

    html += "<div class='card'>"
    html += "<h3><i class='fa-solid fa-briefcase'></i> Jobs matched to your profile (" + str(total) + ")</h3>"
    html += "<table style='width:100%'><tr><th style='width:7%'>Match</th><th style='width:45%'>Job & Requirements</th><th style='width:14%'>Platform</th><th style='width:34%'>Actions</th></tr>"

    for j in slice_jobs:
        pct = _pct(j)
        title = str(j.get("title", ""))[:90]
        url = str(j.get("url", "#"))
        source = str(j.get("source", "?"))
        reqs = _extract_reqs(j.get("description", ""), skills)
        color = "#2e7d32" if pct >= 60 else ("#f9a825" if pct >= 35 else "#9e9e9e")
        js_title = title.replace("\\", "").replace("'", "").replace('"', "")
        js_url = url.replace("\\", "").replace("'", "").replace('"', "")
        js_source = source.replace("\\", "").replace("'", "").replace('"', "")
        prop_href = "/proposal?title=" + _q(title) + "&url=" + _q(url) + "&source=" + _q(source)
        cv_href = "/cvbuilder?job=" + _q(title) + "&req=" + _q(" | ".join(reqs[:6]))

        req_html = ""
        if reqs:
            req_html = "<details open><summary><strong>Requirements (" + str(len(reqs)) + ")</strong></summary><ul style='margin:6px 0'>"
            for r in reqs[:8]:
                hit = any(s in r.lower() for s in skills)
                req_html += "<li>" + esc(r) + (" <strong style='color:#2e7d32'>✓ you match</strong>" if hit else "") + "</li>"
            req_html += "</ul></details>"

        html += "<tr>"
        html += "<td><strong style='color:" + color + ";font-size:18px'>" + str(pct) + "%</strong></td>"
        html += "<td><a href='" + url + "' target='_blank' style='font-weight:bold;font-size:14px'>" + esc(title) + "</a>" + req_html + "</td>"
        html += "<td>" + esc(source) + "</td>"
        html += "<td>"
        html += "<a href='" + url + "' target='_blank' style='padding:4px 8px;background:#2ecc71;color:white;text-decoration:none;border-radius:3px' onclick=\"addToPipeline('" + js_title + "','" + js_url + "','" + js_source + "')\">Apply</a> "
        html += "<button onclick=\"addToPipeline('" + js_title + "','" + js_url + "','" + js_source + "')\" style='padding:4px 8px;background:#3498db;color:white;border:none;border-radius:3px;cursor:pointer'>+ Pipeline</button> "
        html += "<a href='" + prop_href + "' target='_blank' style='padding:4px 8px;background:#9b59b6;color:white;text-decoration:none;border-radius:3px'>Proposal</a> "
        html += "<a href='" + cv_href + "' style='padding:4px 8px;background:#e67e22;color:white;text-decoration:none;border-radius:3px'>CV</a>"
        html += "</td>"
        html += "</tr>"

    if not slice_jobs:
        if hunting_now:
            html += "<tr><td colspan='4' style='text-align:center;padding:40px'><i class='fa-solid fa-spinner fa-spin'></i> Hunting... waiting for results. Refresh in 15 seconds.</td></tr>"
        else:
            html += "<tr><td colspan='4'>No jobs yet. Click 'Hunt live now' or wait for next auto-hunt.</td></tr>"
    html += "</table>"

    html += "<p style='margin-top:14px'>"
    if page_num > 1:
        html += "<a href='/jobagent?page_num=" + str(page_num - 1) + "' style='padding:6px 12px;background:#ecf0f1;text-decoration:none;border-radius:3px'>&laquo; Prev</a> "
    html += "Page " + str(page_num) + " of " + str(pages) + " (" + str(total) + " jobs) "
    if page_num < pages:
        html += "<a href='/jobagent?page_num=" + str(page_num + 1) + "' style='padding:6px 12px;background:#ecf0f1;text-decoration:none;border-radius:3px'>Next &raquo;</a>"
    html += "</p></div>"

    # Auto-refresh every 15 seconds for real-time feel; clear hunting flag when done
    refresh_ms = 15000
    script = "function addToPipeline(title, url, source){fetch('/api/add-to-pipeline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:title,url:url,source:source,stage:'Found'})}).then(function(r){return r.json()}).then(function(d){if(d.ok){}});}setTimeout(function(){location.reload();}," + str(refresh_ms) + ");"
    html += "<script>" + script + "</script>"

    return page("/jobagent", "Job Agent", html)


@app.get("/health")
def health(): return {"status": "ok", "engine": "private-local", "port": 8502}


@app.get("/keepalive")
def keepalive():
    """Lightweight endpoint for keeping service awake"""
    return {"status": "awake", "timestamp": str(datetime.now())}


@app.get("/", response_class=HTMLResponse)

def _owner_briefing():
    import json as _j
    from datetime import datetime as _d
    def _ld(n, d):
        try:
            with open("data/"+n) as f: return _j.load(f)
        except Exception: return d
    jobs = _ld("last_search.json", {}); push = _ld("push.json", {}); prof = _ld("profile.json", {})
    try: audit_lines = open("data/audit.log").read().strip().split("\n")[-6:]
    except Exception: audit_lines = []
    njobs = len(jobs.get("results", jobs if isinstance(jobs, list) else []))
    npush = len(push.get("jobs", push if isinstance(push, list) else []))
    rows = "".join("<li>"+l+"</li>" for l in audit_lines)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>RevenueForge - Owner Briefing</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
header{{background:#1e293b;padding:18px 28px}}h1{{margin:0;font-size:22px}}h1 b{{color:#38bdf8}}
.wrap{{max-width:960px;margin:24px auto;padding:0 20px}}nav a{{margin-right:14px;color:#38bdf8;text-decoration:none;font-size:14px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-top:18px}}
.card{{background:#1e293b;border-radius:10px;padding:16px}}.num{{font-size:30px;font-weight:700;color:#38bdf8}}.lab{{color:#94a3b8;font-size:13px}}
ul{{line-height:1.7;color:#94a3b8;font-size:13px}}</style></head><body>
<header><h1>Revenue<b>Forge</b> - Daily Owner Briefing</h1></header>
<div class="wrap">
<nav><a href="/command">Command</a><a href="/jobagent">Job Agent</a><a href="/pipeline">Pipeline</a><a href="/outreach">Outreach</a><a href="/analytics">Analytics</a><a href="/settings">Settings</a><a href="/cvbuilder">CV Builder</a><a href="/proposal">Proposal</a><a href="/audit">Audit</a></nav>
<div class="cards">
<div class="card"><div class="num">{njobs}</div><div class="lab">Jobs in last hunt</div></div>
<div class="card"><div class="num">{npush}</div><div class="lab">Jobs pushed to cloud</div></div>
<div class="card"><div class="num">{len(audit_lines)}</div><div class="lab">Recent events</div></div>
<div class="card"><div class="num">ON</div><div class="lab">Engine status</div></div>
</div>
<h3>Recent activity</h3><ul>{rows or "<li>No activity yet</li>"}</ul>
<p style="color:#64748b;font-size:12px">Private owner console - {_d.now().strftime("%Y-%m-%d %H:%M")} - skills: {prof.get("skills","not set")}</p>
</div></body></html>"""

def home(request: Request):
    if _env_for(request) == "private":
        return HTMLResponse(_owner_briefing())
    return HTMLResponse(MARKETING)
    """Professional marketing home page"""
    
    hero = """
    <div style="text-align:center; padding:40px 20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:15px; color:white; margin-bottom:30px;">
        <h1 style="font-size:2.5rem; margin-bottom:15px;">Hunt Jobs Across 500+ Platforms</h1>
        <p style="font-size:1.2rem; opacity:0.95; margin-bottom:30px;">AI-powered job hunting that searches where others can't reach</p>
        
        <div style="display:flex; justify-content:center; gap:40px; margin:30px 0;">
            <div><strong style="font-size:2rem;">500+</strong><br><small>Platforms</small></div>
            <div><strong style="font-size:2rem;">291</strong><br><small>Live Sources</small></div>
            <div><strong style="font-size:2rem;">100%</strong><br><small>Real-Time</small></div>
        </div>
        
        <a href="/settings" style="display:inline-block; padding:15px 40px; background:white; color:#667eea; text-decoration:none; border-radius:50px; font-weight:600; margin-top:20px;">Configure Your Profile</a>
    </div>
    """
    
    features = """
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:20px; margin:30px 0;">
        <div class="card" style="text-align:center;">
            <h3>🌍 500+ Platforms</h3>
            <p>We search LinkedIn, Indeed, Glassdoor, and 291+ company career pages that others can't access.</p>
        </div>
        <div class="card" style="text-align:center;">
            <h3>⚡ Real-Time Results</h3>
            <p>No cached data. Every hunt searches live platforms in real-time for the freshest opportunities.</p>
        </div>
        <div class="card" style="text-align:center;">
            <h3>🎯 AI-Matched Jobs</h3>
            <p>Our AI analyzes your profile and only shows jobs that match your skills and career goals.</p>
        </div>
        <div class="card" style="text-align:center;">
            <h3>📝 Auto Proposals</h3>
            <p>Generate professional cover letters tailored to each job in seconds.</p>
        </div>
        <div class="card" style="text-align:center;">
            <h3>📊 Application Tracking</h3>
            <p>Track every application from found to hired. Never lose track again.</p>
        </div>
        <div class="card" style="text-align:center;">
            <h3>🔒 Privacy First</h3>
            <p>Your data stays yours. Apply anonymously until you're ready.</p>
        </div>
    </div>
    """
    
    testimonials = """
    <div style="margin:40px 0;">
        <h2 style="text-align:center; margin-bottom:30px;">What Our Hunters Say</h2>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:20px;">
            <div class="card">
                <p style="font-style:italic; margin-bottom:15px;">"Found my dream job through RevenueForge. Applied to 15 companies, got 8 interviews, landed the offer in 3 weeks."</p>
                <p><strong>Sarah K.</strong><br><small>Senior Developer</small></p>
            </div>
            <div class="card">
                <p style="font-style:italic; margin-bottom:15px;">"The real-time search found opportunities on company career pages that weren't on any job board. Got hired within a month."</p>
                <p><strong>Mike R.</strong><br><small>Backend Engineer</small></p>
            </div>
            <div class="card">
                <p style="font-style:italic; margin-bottom:15px;">"The proposal generator saved me hours. My response rate tripled."</p>
                <p><strong>Jessica L.</strong><br><small>Product Designer</small></p>
            </div>
        </div>
    </div>
    """
    
    cta = """
    <div style="text-align:center; padding:40px; background:#f8f9fa; border-radius:15px; margin:30px 0;">
        <h2 style="margin-bottom:20px;">Ready to Start Hunting?</h2>
        <p style="font-size:1.1rem; margin-bottom:25px;">Configure your profile and let our AI find the perfect opportunities for you.</p>
        <a href="/settings" style="display:inline-block; padding:15px 40px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; text-decoration:none; border-radius:50px; font-weight:600;">Get Started Now</a>
    </div>
    """
    
    return page("/", "Welcome to RevenueForge", hero + features + testimonials + cta)


@app.get("/command", response_class=HTMLResponse)
def command():
    import time as _t
    from datetime import datetime, timedelta
    
    audit("view /command")
    jobs = ld("jobs.json", [])
    
    # Get cache info
    cache_time = ""
    platforms_used = 0
    try:
        import json
        from pathlib import Path
        cache_file = Path("data/last_search.json")
        if cache_file.exists():
            cache_data = json.loads(cache_file.read_text())
            cache_time = cache_data.get("time", "")
            platforms_used = len(set(j.get("source", "?") for j in cache_data.get("jobs", [])))
    except:
        pass
    
    # Calculate time since last hunt
    time_info = ""
    next_hunt = ""
    if cache_time:
        try:
            ct = datetime.strptime(cache_time, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            mins_ago = (now - ct).total_seconds() / 60
            
            if mins_ago < 1:
                time_info = "Just now"
            elif mins_ago < 60:
                time_info = f"{int(mins_ago)} minutes ago"
            else:
                time_info = f"{int(mins_ago/60)} hours ago"
            
            # Next hunt (30 minutes after last)
            next_hunt_time = ct + timedelta(minutes=30)
            if next_hunt_time > now:
                next_mins = (next_hunt_time - now).total_seconds() / 60
                next_hunt = f"in {int(next_mins)} minutes"
            else:
                next_hunt = "now (overdue)"
        except:
            time_info = "Unknown"
            next_hunt = "Unknown"
    
    # Worker status
    worker_status = "⛔ Stopped"
    worker_class = "err"
    try:
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'home_worker.py'], capture_output=True, text=True)
        if result.stdout.strip():
            worker_status = "✅ Running"
            worker_class = "ok"
    except:
        pass
    
    # Build HTML
    html = "<div class='card'>"
    html += "<h3><i class='fa-solid fa-compass'></i> Auto-Hunt Status</h3>"
    html += "<table style='width:100%'>"
    html += f"<tr><td><strong>Worker</strong></td><td class='{worker_class}'>{worker_status}</td></tr>"
    html += f"<tr><td><strong>Hunt frequency</strong></td><td>Every 30 minutes</td></tr>"
    html += f"<tr><td><strong>Last hunt</strong></td><td>{time_info}</td></tr>"
    html += f"<tr><td><strong>Next hunt</strong></td><td>{next_hunt}</td></tr>"
    html += f"<tr><td><strong>Platforms searched</strong></td><td>{platforms_used}</td></tr>"
    html += f"<tr><td><strong>Jobs in cache</strong></td><td>{len(jobs)}</td></tr>"
    html += "</table>"
    html += "</div>"
    
    html += "<div class='card'>"
    html += "<h3><i class='fa-solid fa-play'></i> Manual Control</h3>"
    html += "<form method='post' action='/api/run'>"
    html += "<button type='submit'>Run full search now</button>"
    html += "</form>"
    html += "<p class='muted'>This will search all platforms immediately and update the cache.</p>"
    html += "</div>"
    
    # Add auto-refresh script
    html += "<script>setTimeout(function(){location.reload();}, 60000);</script>"
    html += "<p class='muted'><i class='fa-solid fa-rotate'></i> Page auto-refreshes every 60 seconds</p>"
    
    return page("/command", "Command Center", html)

@app.post("/api/run")
def api_run():
    r = gather(); sv("jobs.json", r); audit(f"run search -> {len(r)} jobs")
    return RedirectResponse("/command", status_code=303)





def _extract_reqs(desc, skills):
    out = []
    desc_str = str(desc).replace("<br>", " ").replace("\r", " ")
    sentences = [s.strip() for s in desc_str.replace("\n", ".").split(".") if len(s.strip()) > 15]
    
    # Priority 1: sentences with requirement keywords
    req_words = ["experience", "skill", "proficient", "knowledge", "familiar", "understanding", "ability", "degree", "certification", "years of"]
    for sent in sentences:
        sl = sent.lower()
        if any(w in sl for w in req_words) and len(out) < 8:
            out.append(sent[:200])
    
    # Priority 2: sentences mentioning user skills or common tech
    tech_words = ["python", "javascript", "sql", "aws", "docker", "kubernetes", "react", "node", "database", "api", "git", "linux", "html", "css"]
    for sent in sentences:
        sl = sent.lower()
        if sent not in out and len(out) < 8:
            if any(sk in sl for sk in skills) or any(tw in sl for tw in tech_words):
                out.append(sent[:200])
    
    # Priority 3: any longer sentences if we still need more
    for sent in sentences:
        if sent not in out and len(out) < 6 and len(sent) > 30:
            out.append(sent[:200])
    
    return out[:8]


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline():
    pl = ld("pipeline.json", {"Found": 0, "Contacted": 0, "Replied": 0, "Won": 0})
    apps = ld("applications.json", [])
    
    # Build summary HTML with string concatenation
    summary_html = "<div class='card'><h3>Pipeline Summary</h3><table><tr><th>Stage</th><th>Count</th></tr>"
    for stage in ["Found", "Contacted", "Replied", "Won"]:
        count = pl.get(stage, 0)
        summary_html += "<tr><td><strong>" + stage + "</strong></td><td>" + str(count) + "</td></tr>"
    summary_html += "</table></div>"
    
    # Build applications HTML
    apps_html = "<div class='card'><h3>Recent Applications</h3><table style='width:100%'>"
    apps_html += "<tr><th>Job</th><th>Stage</th><th>Date</th><th>Proposal</th><th>CV</th></tr>"
    
    recent = apps[-20:][::-1]
    for app in recent:
        title = str(app.get("title", ""))[:60]
        url = str(app.get("url", "#"))
        stage = str(app.get("stage", ""))
        date = str(app.get("date", ""))
        prop_sent = app.get("proposal_sent", False)
        cv_sent = app.get("cv_sent", False)
        
        apps_html += "<tr>"
        apps_html += "<td><a href='" + url + "' target='_blank'>" + title + "</a></td>"
        apps_html += "<td>" + stage + "</td>"
        apps_html += "<td>" + date + "</td>"
        
        if prop_sent:
            apps_html += "<td>✓ Sent</td>"
        else:
            apps_html += "<td><button onclick='generateProposal(this)' data-title='" + title.replace("'", "\'") + "' data-url='" + url + "'>Generate</button></td>"
        
        if cv_sent:
            apps_html += "<td>✓ Sent</td>"
        else:
            apps_html += "<td><button onclick='generateCV(this)' data-title='" + title.replace("'", "\'") + "'>Generate</button></td>"
        
        apps_html += "</tr>"
    
    if not recent:
        apps_html += "<tr><td colspan='5'>No applications yet. Add jobs from Job Agent.</td></tr>"
    
    apps_html += "</table></div>"
    
    # JavaScript
    script = """
    <script>
    function generateProposal(btn) {
        var title = btn.getAttribute('data-title');
        var url = btn.getAttribute('data-url');
        var proposal = "Dear Hiring Manager,\\n\\nI am writing to express my strong interest in the " + title + " position.\\n\\nWith my background in software development, I believe I would be a valuable addition to your team.\\n\\nBest regards";
        var w = window.open('', '_blank');
        w.document.write('<pre>' + proposal + '</pre>');
        fetch('/api/mark-proposal-sent', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({title: title, url: url})});
    }
    
    function generateCV(btn) {
        var title = btn.getAttribute('data-title');
        var cv = "CURRICULUM VITAE\\n\\nSUMMARY\\nExperienced software developer.\\n\\nSKILLS\\nPython, JavaScript, SQL\\n\\nEXPERIENCE\\n[Add your experience]\\n\\nEDUCATION\\n[Add your education]";
        var w = window.open('', '_blank');
        w.document.write('<pre>' + cv + '</pre>');
    }
    </script>
    """
    
    return page("/pipeline", "Pipeline", summary_html + apps_html + script)




@app.post("/api/search-now")
async def search_now(request: Request):
    """Real-time search called by public site via secure tunnel"""
    try:
        body = await request.json()
        
        # Token verification (simple for now)
        token = body.get("token", "")
        expected_token = os.environ.get("RF_SEARCH_TOKEN", "revenueforge-2026")
        if token != expected_token:
            return {"error": "Invalid token"}
        
        # Get search parameters
        query = body.get("query", "")
        limit = body.get("limit", 100)
        skills = body.get("skills", "")
        target = body.get("target", "")
        min_salary = body.get("min_salary", 0)
        
        # Run real-time search
        print(f"[search-now] Searching for: {query}, skills: {skills}, target: {target}")
        all_jobs = gather_all(query)
        
        # Filter by skills if provided
        if skills:
            skill_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
            filtered = []
            for job in all_jobs:
                job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
                if any(skill in job_text for skill in skill_list):
                    filtered.append(job)
            all_jobs = filtered
        
        # Limit results
        all_jobs = all_jobs[:limit]
        
        # Return anonymized job data
        results = []
        for job in all_jobs:
            results.append({
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "description": job.get("description", "")[:500],
                "url": job.get("url", ""),
                "platform": job.get("platform", job.get("source", "")),
                "score": job.get("score", 80)
            })
        
        print(f"[search-now] Returning {len(results)} jobs")
        return {
            "ok": True,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        print(f"[search-now] Error: {e}")
        return {"error": str(e)}


@app.get("/analytics", response_class=HTMLResponse)
def analytics():
    jobs = ld("jobs.json", []); src = {}
    for j in jobs: src[j.get("source", "?")] = src.get(j.get("source", "?"), 0) + 1
    mx = max(list(src.values()) or [1])
    bars = "".join(f'<p>{k}</p><div class="bar"><i style="width:{int(v/mx*100)}%"></i></div>' for k, v in src.items()) or "<p class='muted'>No data yet.</p>"
    return page("/analytics", "Analytics", card("fa-chart-line", "Jobs by source", bars))

@app.get("/products", response_class=HTMLResponse)
def products():
    ps = ld("products.json", [])
    rows = "".join(f"<tr><td>{p.get('name','')}</td><td>{p.get('price','')}</td></tr>" for p in ps) or "<tr><td>No products yet.</td></tr>"
    return page("/products", "Products", card("fa-box", "Your products", f"<table><tr><th>Name</th><th>Price</th></tr>{rows}</table>"))

@app.get("/prospects", response_class=HTMLResponse)
def prospects():
    ps = ld("prospects.json", [])
    rows = "".join(f"<tr><td>{p.get('name','')}</td><td>{p.get('stage','')}</td></tr>" for p in ps) or "<tr><td>No prospects yet.</td></tr>"
    return page("/prospects", "Prospects", card("fa-magnifying-glass", "Prospect list", f"<table><tr><th>Name</th><th>Stage</th></tr>{rows}</table>"))

@app.get("/outreach", response_class=HTMLResponse)
def outreach():
    o = ld("outreach.json", {"dm": "Hi {name} - saw you're hiring for {role}. I automate {skill} work and can start this week. Open to a quick chat?", "email": "Subject: Quick win for {company}\n\nHi {name},\nI help teams like yours automate {skill}. Can I send a 2-min demo?"})
    return page("/outreach", "Outreach", card("fa-paper-plane", "DM template", f"<pre>{o['dm']}</pre>") + card("fa-envelope", "Email template", f"<pre>{o['email']}</pre>"))

@app.get("/followups", response_class=HTMLResponse)
def followups(who: str = ""):
    fs = ld("followups.json", [])
    rows = "".join(f"<tr><td>{f.get('who','')}</td><td>{f.get('due','')}</td></tr>" for f in fs) or "<tr><td>No follow-ups due.</td></tr>"
    return page("/followups", "Follow-ups", card("fa-rotate", "Due soon", f"<table><tr><th>Who</th><th>Due</th></tr>{rows}</table>"))



@app.get("/settings", response_class=HTMLResponse)
def settings():
    s = ld("settings.json", {})
    profile = ld("profile.json", {})
    
    skills = profile.get('skills', '')
    target = profile.get('target', '')
    min_salary = profile.get('min_salary', 80000)
    location = profile.get('location', '')
    job_types = profile.get('job_types', '')
    
    mode = s.get('mode', 'Find me jobs')
    freq = str(s.get('frequency', '10'))
    freq_opts = ""
    for _v, _l in [("5", "Every 5 minutes"), ("10", "Every 10 minutes"), ("30", "Every 30 minutes"), ("60", "Every hour")]:
        freq_opts += "<option value='" + _v + "'" + (" selected" if _v == freq else "") + ">" + _l + "</option>"
    freq_opts_placeholder = freq_opts
    
    html = f"""
    <div class="card">
        <h3><i class="fa-solid fa-user"></i> Your Profile</h3>
        <form method="post" action="/api/settings">
            <label>Skills (comma-separated)</label>
            <textarea name="skills" rows="3" placeholder="python, django, react">{skills}</textarea>
            
            <label>Target Market</label>
            <input name="target" value="{target}" placeholder="startups, enterprises, remote">
            
            <label>Experience Level</label>
            <select name="experience">
                <option>Junior</option>
                <option>Mid-Level</option>
                <option>Senior</option>
                <option>Lead</option>
            </select>
            
            <label>Minimum Salary (USD/year)</label>
            <input name="min_salary" type="number" value="{min_salary}">
            
            <label>Preferred Location</label>
            <input name="location" value="{location}" placeholder="Remote, US, EU">
            
            <label>Job Types</label>
            <input name="job_types" value="{job_types}" placeholder="full-time, contract">
            
            <button type="submit">Save Profile</button>
        </form>
    </div>
    
    <div class="card">
        <h3><i class="fa-solid fa-cog"></i> Engine Configuration</h3>
        <form method="post" action="/api/settings">
            <label>Search Mode</label>
            <select name="mode">
                <option value="Find me jobs">Find me jobs</option>
                <option value="Sell my services">Sell my services</option>
                <option value="Both">Both</option>
            </select>
            
            <label>Auto-search Frequency</label>
            <select name="frequency">{freq_opts_placeholder}</select>
            
            <label>Platforms to Search</label>
            <textarea name="platforms" rows="2" placeholder="all">{s.get('platforms', 'all')}</textarea>
            
            <button type="submit">Save Engine Settings</button>
        </form>
    </div>
    """
    
    return page("/settings", "Settings", html)


@app.post("/api/settings")
def api_settings(skills: str = Form(""), target: str = Form(""), mode: str = Form("Find me jobs"), frequency: str = Form("10"), experience: str = Form(""), min_salary: str = Form(""), location: str = Form(""), job_types: str = Form(""), platforms: str = Form("all")):
    sv("settings.json", {"mode": mode, "frequency": frequency, "platforms": platforms})
    sv("profile.json", {"skills": skills, "target": target, "experience": experience, "min_salary": min_salary, "location": location, "job_types": job_types})
    audit("settings saved")
    return RedirectResponse("/settings", status_code=303)

@app.get("/scaling", response_class=HTMLResponse)
def scaling():
    return page("/scaling", "Scaling", card("fa-rocket", "Grow", good("Local engine handles your home-IP sources.") + mute("Cloud engine handles public traffic on Render.")))

@app.get("/admin/subs", response_class=HTMLResponse)
def admin_subs():
    ss = ld("subs.json", [])
    rows = "".join(f"<tr><td>{s.get('email','')}</td><td>{s.get('plan','')}</td></tr>" for s in ss) or "<tr><td>No local overrides - cloud DB is source of truth.</td></tr>"
    return page("/admin/subs", "Admin: Subscriptions", card("fa-rectangle-list", "Subscriptions", f"<table><tr><th>Email</th><th>Plan</th></tr>{rows}</table>"))

@app.get("/admin/projects", response_class=HTMLResponse)
def admin_projects():
    ps = ld("projects.json", [])
    rows = "".join(f"<tr><td>{p.get('client','')}</td><td>{p.get('status','')}</td></tr>" for p in ps) or "<tr><td>No client projects yet.</td></tr>"
    return page("/admin/projects", "Admin: Client Projects", card("fa-diagram-project", "Projects", f"<table><tr><th>Client</th><th>Status</th></tr>{rows}</table>"))

@app.get("/admin/invites", response_class=HTMLResponse)
def admin_invites():
    iv = ld("invites.json", [])
    rows = "".join(f"<tr><td>{c}</td></tr>" for c in iv) or "<tr><td>No invite codes yet.</td></tr>"
    body = card("fa-key", "Invite codes", f"<table>{rows}</table><form method='post' action='/api/invites'><button>Generate code</button></form>")
    return page("/admin/invites", "Admin: Invite Codes", body)

@app.post("/api/invites")
def api_invites():
    iv = ld("invites.json", []); iv.append(secrets.token_hex(4).upper()); sv("invites.json", iv); audit("invite generated")
    return RedirectResponse("/admin/invites", status_code=303)

@app.get("/security", response_class=HTMLResponse)
def security():
    audit("view /security")
    pat = re.compile(r"(?i)(secret|api_key|apikey|token|password|private_key)\s*=\s*['\"][A-Za-z0-9]{8,}['\"]")
    hits = []
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".js", ".html") and ".venv" not in p.parts and "node_modules" not in p.parts and "__pycache__" not in p.parts:
            try: t = p.read_text(errors="ignore")
            except Exception: continue
            for m in pat.finditer(t):
                if any(x in m.group(0) for x in ("os.environ", "YOUR_", "example")): continue
                hits.append(f"{p.name}: {m.group(0)[:40]}")
    c1 = card("fa-key", "Hardcoded secret scan", good("No hardcoded secrets found. All sensitive values live in .env.") if not hits else bad("Found: " + "; ".join(hits[:3])))
    gi = (ROOT / ".gitignore")
    txt = gi.read_text() if gi.exists() else ""
    missing = [n for n in (".env", "data", ".log", "__pycache__") if n not in txt]
    c2 = card("fa-shield-halved", ".gitignore protection", good(".gitignore protects .env, data, logs and caches.") if not missing else bad("Missing entries: " + ", ".join(missing)))
    keys = []
    env = ROOT / ".env"
    if env.exists():
        keys = [l.split("=")[0].strip() for l in env.read_text().splitlines() if "=" in l and not l.startswith("#")]
    c3 = card("fa-file-shield", "Environment secrets", "".join(mute(f".env holds secret '{k}' - keep it git-ignored and never share it.") for k in keys) or mute("No .env file found."))
    return page("/security", "Security & Fail-Safe", c1 + c2 + c3)

@app.get("/audit", response_class=HTMLResponse)
def audit_page():
    log = DATA / "audit.log"
    lines = log.read_text().splitlines()[-50:] if log.exists() else []
    return page("/audit", "Audit Log", card("fa-scroll", "Last 50 events", f"<pre>{chr(10).join(lines) or 'Empty.'}</pre>"))

@app.get("/api/search")
def api_search(q: str = ""): return {"results": gather(q), "source": "private-engine"}

# ===== PORTAL-COMPATIBLE API (local portal on :8600) =====
from html import escape
esc = escape

import sys as _sys, subprocess as _sp
import requests as _rq
from fastapi import Request, Request as _Req, UploadFile, File

import re as _re
from app.core.hiring_search import gather_all
def _sanitize(s):
    if not isinstance(s, str): return s
    return _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', s)

CLOUD = "https://revenueforge-api.onrender.com"

def _proxy(path, method="GET", body=None):
    try:
        r = _rq.request(method, CLOUD + path, json=body, timeout=25)
        try: return r.json()
        except Exception: return {"ok": False, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/sub/{email}")
def api_sub(email: str):
    """Get subscription status from local data"""
    import json, os
    profile_path = "data/profile.json"
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile = json.load(f)
        return {
            "ok": True,
            "plan": profile.get("plan", "free"),
            "paid": profile.get("paid", False),
            "trial_end": profile.get("trial_end", ""),
            "email": email
        }
    return {"ok": True, "plan": "free", "paid": False, "email": email}

@app.post("/api/save-profile")
async def api_save_profile(request: _Req):
    try:
        b = await request.json()
    except Exception:
        b = {}
    sv("profile.json", b)
    return {"ok": True, "message": "Profile saved"}

@app.post("/api/engine-toggle")
async def api_engine_toggle(request: _Req):
    b = await request.json(); on = bool(b.get("on"))
    pidf = Path.home() / ".rf_worker.pid"
    if on:
        if not worker_alive():
            logf = open(Path.home() / ".rf_worker.log", "a")
            p = _sp.Popen([_sys.executable, "scripts/home_worker.py"], cwd=str(ROOT), stdout=logf, stderr=logf)
            pidf.write_text(str(p.pid))
        audit("engine toggled ON")
        return {"ok": True, "on": True}
    if pidf.exists():
        try: os.kill(int(pidf.read_text().strip()), 15)
        except Exception: pass
        pidf.unlink(missing_ok=True)
    audit("engine toggled OFF")
    return {"ok": True, "on": False}

@app.get("/api/search-hiring")
def api_search_hiring(q: str = "", limit: int = 100, email: str = ""):
    """Return jobs from pushed jobs (first) or cached search"""
    import json as _json
    from pathlib import Path as _Path
    
    # Try to read pushed jobs first
    pushed_file = ROOT / "data" / "pushed_jobs.json"
    jobs = []
    
    if pushed_file.exists():
        try:
            jobs = _json.loads(pushed_file.read_text())
        except:
            jobs = []
    
    # If no pushed jobs, fall back to live search
    if not jobs:
        jobs = gather(q)
    
    # Filter by query if provided
    if q:
        q_lower = q.lower()
        query_words = q_lower.split()
        filtered = []
        for j in jobs:
            searchable = " ".join([
                j.get("title", ""),
                j.get("description", ""),
                j.get("source", ""),
                j.get("platform", "")
            ]).lower()
            if any(word in searchable for word in query_words):
                filtered.append(j)
        
        # If too few results, return all jobs
        if len(filtered) < 10:
            jobs = jobs[:limit]
        else:
            jobs = filtered[:limit]
    else:
        jobs = jobs[:limit]
    
    platforms = list(set(j.get("platform", j.get("source", "?")) for j in jobs))
    
    return {
        "results": jobs,
        "count": len(jobs),
        "cached": True,
        "cache_time": "pushed",
        "platforms": platforms,
        "total_in_cache": len(jobs)
    }


@app.get("/api/my/products")
def api_my_products(email: str = ""):
    """Get user's published services from local data"""
    import json, os
    products_path = "data/products.json"
    if os.path.exists(products_path):
        with open(products_path) as f:
            products = json.load(f)
        return {"ok": True, "products": products.get(email, [])}
    return {"ok": True, "products": []}

@app.post("/api/my/products")
async def api_my_products_post(request: _Req):
    b = await request.json(); return _proxy("/api/my/products", "POST", b)

@app.post("/api/my/products/{pid}")
async def api_my_products_id(pid: str, request: _Req):
    try: b = await request.json()
    except Exception: b = {}
    return _proxy("/api/my/products/" + pid, "POST", b)

@app.delete("/api/my/products/{pid}")
def api_my_products_del(pid: str, email: str = ""): return _proxy("/api/my/products/" + pid + "?email=" + email, "DELETE")

@app.post("/api/advertise-service")
async def api_advertise(request: _Req):
    b = await request.json(); return _proxy("/api/advertise-service", "POST", b)

@app.post("/api/paystack/init")
async def api_paystack_init(request: _Req):
    b = await request.json(); return _proxy("/api/paystack/init", "POST", b)

@app.post("/api/paystack/verify")
async def api_paystack_verify(request: _Req):
    b = await request.json(); return _proxy("/api/paystack/verify", "POST", b)





@app.post("/api/chat")
async def api_chat(request: Request):
    try:
        data = await request.json()
        msg = (data.get("message") or "").strip().lower()
        if "work" in msg or "how" in msg: return {"reply": "Configure skills in My Engine, click Start, and jobs appear from 105+ sources. You approve every proposal manually."}
        if "price" in msg or "cost" in msg: return {"reply": "Free tier has 5 jobs/search. Pro is $30/month for unlimited 105+ sources and proposals. Check Pricing page."}
        if "source" in msg or "where" in msg: return {"reply": "105+ sources: 25 RSS feeds, 10 Reddit subs, 60+ Greenhouse boards, Lever, Remotive, HN. LinkedIn/Upwork via official APIs/alerts."}
        if "spam" in msg or "safe" in msg: return {"reply": "Completely spam-safe. Official APIs only, no fake accounts, human approval required for every action."}
        if "proposal" in msg: return {"reply": "I draft personalized proposals based on your skills. You always review and approve manually before submission."}
        return {"reply": "I can help with jobs, pricing, proposals, and compliance. Click 'Talk to a human' to email the founder."}
    except Exception:
        return {"reply": "I had trouble thinking. Please try again."}


@app.post("/api/add-to-pipeline")
def add_to_pipeline(data: dict):
    try:
        import time as _T
        pl = ld("pipeline.json", {"Found": 0, "Contacted": 0, "Replied": 0, "Won": 0})
        stage = data.get("stage", "Found")
        pl[stage] = pl.get(stage, 0) + 1
        sv("pipeline.json", pl)
        apps = ld("applications.json", [])
        apps.append({"id": int(_T.time() * 1000), "title": str(data.get("title", "")), "url": str(data.get("url", "")), "source": str(data.get("source", "")), "stage": stage, "date": now(), "proposal_sent": False, "cv_sent": False})
        sv("applications.json", apps)
        audit("Pipeline: " + str(data.get("title", ""))[:50])
        return {"ok": True}
    except Exception as _e:
        return {"ok": False, "error": str(_e)}


@app.post("/api/move-stage")
def move_stage(data: dict):
    try:
        aid = data.get("id")
        new_stage = data.get("stage", "Found")
        apps = ld("applications.json", [])
        pl = ld("pipeline.json", {"Found": 0, "Contacted": 0, "Replied": 0, "Won": 0})
        moved = False
        for a in apps:
            if str(a.get("id")) == str(aid):
                old = a.get("stage", "Found")
                if old in pl:
                    pl[old] = max(0, pl.get(old, 1) - 1)
                a["stage"] = new_stage
                pl[new_stage] = pl.get(new_stage, 0) + 1
                moved = True
                break
        sv("applications.json", apps)
        sv("pipeline.json", pl)
        return {"ok": True, "moved": moved}
    except Exception as _e:
        return {"ok": False, "error": str(_e)}



def _long_proposal(job, company, reqs, cv):
    name = cv.get("name") or "The Applicant"
    skills = cv.get("skills") or "a broad, production-tested skill set"
    exp_lines = [l for l in (cv.get("experience") or "").split("\n") if l.strip()]
    top_exp = exp_lines[0].split("|")[0].strip() if exp_lines else "senior-level delivery"
    req_list = [r.strip() for r in reqs.replace("|", "\n").split("\n") if r.strip()] or ["the core requirements listed in the posting"]
    req_sentence = "; ".join(req_list[:4])
    p = []
    p.append("Subject: Application for " + job + ((" at " + company) if company else ""))
    p.append("")
    p.append("Dear " + (company or "Hiring") + " Team,")
    p.append("")
    p.append("I am writing to express my strong interest in the " + job + " position" + ((" at " + company) if company else "") + ". Having reviewed the role in detail, I am confident that my background in " + skills + " aligns closely with what your team needs, and I would welcome the opportunity to contribute from day one.")
    p.append("")
    p.append("What draws me to this role is the clear emphasis on " + req_sentence + ". These are areas where I have delivered measurable results in production environments, not simply studied in theory. In my most recent work as " + top_exp + ", I owned end-to-end delivery of features and systems, balancing speed with the discipline required to keep quality high.")
    p.append("")
    p.append("A few highlights that I believe are directly relevant:")
    for r in req_list[:3]:
        p.append("   - " + r + ": I have hands-on experience addressing exactly this, and can point to concrete outcomes where similar challenges were solved efficiently and sustainably.")
    p.append("")
    p.append("Beyond technical execution, I bring clear communication, an ownership mindset, and a habit of documenting decisions so that teams move faster over time. I collaborate well across functions and am comfortable turning ambiguous requirements into a concrete, shippable plan.")
    p.append("")
    p.append("I would be glad to walk through specific examples relevant to " + (job or "this role") + " in more detail, and to discuss how I can help your team reach its next milestones. Thank you for your time and consideration - I look forward to the possibility of speaking with you.")
    p.append("")
    p.append("Warm regards,")
    p.append(name)
    if cv.get("email"): p.append(cv.get("email"))
    if cv.get("phone"): p.append(cv.get("phone"))
    if cv.get("links"): p.append(cv.get("links"))
    return "\n".join(p)

@app.get("/proposal", response_class=HTMLResponse)
def proposal(job: str = "", company: str = "", reqs: str = ""):
    cv = ld("cv.json", {})
    body = ""
    if job:
        txt = _long_proposal(job, company, reqs, cv)
        words = len(txt.split())
        body = "<div id='ptxt' style='background:#fff;padding:30px;border-radius:8px;white-space:pre-wrap;line-height:1.8'>" + esc(txt) + "</div>"
        body += "<p style='margin-top:10px;color:#666'>Length: " + str(words) + " words (professional long-form)</p>"
        body += "<button onclick='navigator.clipboard.writeText(document.getElementById(\'ptxt\').innerText)' style='margin:10px 6px 0 0;padding:10px 20px;background:#3498db;color:#fff;border:0;border-radius:5px;cursor:pointer'>Copy</button>"
        body += "<button onclick='window.print()' style='padding:10px 20px;background:#16a34a;color:#fff;border:0;border-radius:5px;cursor:pointer'>Print</button>"
    form = "<form method='get' style='background:#fff;padding:20px;border-radius:8px;margin-bottom:20px'>"
    form += "<label>Job Title:<br><input name='job' value='" + esc(job) + "' style='width:100%;padding:8px;margin:6px 0'></label>"
    form += "<label>Company:<br><input name='company' value='" + esc(company) + "' style='width:100%;padding:8px;margin:6px 0'></label>"
    form += "<label>Requirements (one per line):<br><textarea name='reqs' rows='5' style='width:100%;padding:8px;margin:6px 0'>" + esc(reqs) + "</textarea></label>"
    form += "<button type='submit' style='padding:12px 24px;background:#3498db;color:#fff;border:0;border-radius:5px;cursor:pointer'>Generate Professional Proposal</button></form>"
    return page("/proposal", "Proposal Generator", form + body)

@app.get("/cvbuilder", response_class=HTMLResponse)
def cvbuilder(job: str = "", req: str = ""):
    cv = ld("cv.json", {})
    reqs = [r.strip() for r in req.split("|") if r.strip()] if req else []
    skills_default = str(ld("profile.json", {}).get("skills", ""))
    
    html = "<div style='max-width: 800px; margin: 20px auto; padding: 20px; background: white;'>"
    html += "<h1>Edit Your CV</h1>"
    html += "<p>Fill in your professional information. The CV will be formatted automatically.</p>"
    
    if job:
        html += "<div style='background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>"
        html += "<strong>Tailoring for:</strong> " + esc(job)
        if reqs:
            html += "<br><strong>Requirements:</strong> " + esc(", ".join(reqs[:3]))
        html += "</div>"
    
    html += "<form method='post' action='/api/save-cv' enctype='multipart/form-data'>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px;'>Basic Information</h2>"
    html += "<label>Full Name:<br><input name='name' value='" + esc(cv.get("name", "")) + "' style='width:100%;padding:8px;margin-bottom:10px'></label><br>"
    html += "<label>Email:<br><input name='email' type='email' value='" + esc(cv.get("email", "")) + "' style='width:100%;padding:8px;margin-bottom:10px'></label><br>"
    html += "<label>Phone:<br><input name='phone' value='" + esc(cv.get("phone", "")) + "' style='width:100%;padding:8px;margin-bottom:10px'></label><br>"
    html += "<label>City/Country:<br><input name='city' value='" + esc(cv.get("city", "")) + "' style='width:100%;padding:8px;margin-bottom:10px'></label><br>"
    html += "<label>Links (LinkedIn/GitHub/Portfolio):<br><input name='links' value='" + esc(cv.get("links", "")) + "' style='width:100%;padding:8px;margin-bottom:10px'></label><br>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Professional Summary</h2>"
    html += "<textarea name='summary' rows='4' style='width:100%;padding:8px;margin-bottom:10px'>" + esc(cv.get("summary", "")) + "</textarea><br>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Skills (comma-separated)</h2>"
    html += "<textarea name='skills' rows='3' style='width:100%;padding:8px;margin-bottom:10px'>" + esc(cv.get("skills", skills_default)) + "</textarea><br>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Experience (one per line: Role | Company | Dates | Achievement)</h2>"
    html += "<textarea name='experience' rows='8' id='expbox' style='width:100%;padding:8px;margin-bottom:10px'>" + esc(cv.get("experience", "")) + "</textarea><br>"
    
    if reqs:
        html += "<div style='background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>"
        html += "<strong>💡 Requirement Helper - Click to add matching bullets:</strong><ul>"
        for r in reqs[:6]:
            sug = "Delivered work matching: " + r
            html += "<li>" + esc(r) + " <button type='button' onclick=\"addBullet(this.innerText)\" data-text=\"" + esc("Delivered work matching: " + r) + "\">" + "+ Add" + "</button></li>"
        html += "</ul></div>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Education (one per line)</h2>"
    html += "<textarea name='education' rows='3' style='width:100%;padding:8px;margin-bottom:10px'>" + esc(cv.get("education", "")) + "</textarea><br>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Certifications (one per line)</h2>"
    html += "<textarea name='certs' rows='3' style='width:100%;padding:8px;margin-bottom:10px'>" + esc(cv.get("certs", "")) + "</textarea><br>"
    
    html += "<h2 style='border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 30px;'>Profile Photo (optional)</h2>"
    html += "<input type='file' name='photo' accept='image/*' style='margin-bottom:20px'><br>"
    
    html += "<button type='submit' style='padding:12px 24px;background:#3498db;color:white;border:none;border-radius:5px;cursor:pointer;font-size:16px'>💾 Save CV</button> "
    html += "<a href='/cv' style='margin-left:20px;padding:12px 24px;background:#2ecc71;color:white;text-decoration:none;border-radius:5px'>👁️ Preview CV</a>"
    
    html += """
    <div style='margin-top:30px;display:flex;gap:15px;flex-wrap:wrap'>
      <button type='button' onclick='showPreview()' style='padding:14px 28px;background:#0066cc;color:white;border:none;border-radius:6px;cursor:pointer;font-size:15px;font-weight:600'>
        <i class='fa-solid fa-eye'></i> Preview CV
      </button>
      <button type='button' onclick='printCV()' style='padding:14px 28px;background:#16a34a;color:white;border:none;border-radius:6px;cursor:pointer;font-size:15px;font-weight:600'>
        <i class='fa-solid fa-print'></i> Print / Save PDF
      </button>
    </div>
    """
    
    # Add modal + JavaScript
    html += """
    <div id='cvModal' style='display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:9999;overflow-y:auto;padding:40px 20px'>
      <div style='background:white;max-width:850px;margin:0 auto;padding:50px;border-radius:10px;position:relative;box-shadow:0 10px 40px rgba(0,0,0,.3)'>
        <button onclick='document.getElementById("cvModal").style.display="none"' style='position:absolute;top:15px;right:15px;background:#e2e8f0;border:0;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px'>Close</button>
        <div id='cvContent'></div>
        <button onclick='window.print()' style='margin-top:30px;padding:14px 28px;background:#16a34a;color:white;border:none;border-radius:6px;cursor:pointer;font-size:15px'>Print Now</button>
      </div>
    </div>
    <style>
      @media print {
        body > *:not(#cvModal) { display: none !important; }
        #cvModal { position: static !important; background: white !important; padding: 0 !important; }
        #cvModal button { display: none !important; }
      }
    </style>
    <script>
    function showPreview() {
      var name = document.querySelector('input[name="name"]').value || 'Your Name';
      var email = document.querySelector('input[name="email"]').value || '';
      var phone = document.querySelector('input[name="phone"]').value || '';
      var city = document.querySelector('input[name="city"]').value || '';
      var links = document.querySelector('input[name="links"]').value || '';
      var summary = document.querySelector('textarea[name="summary"]').value || '';
      var skills = document.querySelector('textarea[name="skills"]').value || '';
      var exp = document.querySelector('textarea[name="experience"]').value || '';
      var edu = document.querySelector('textarea[name="education"]').value || '';
      var certs = document.querySelector('textarea[name="certs"]').value || '';
      
      var html = '<h1 style="margin:0 0 10px 0;font-size:36px;color:#0f172a;border-bottom:3px solid #0066cc;padding-bottom:15px">' + name + '</h1>';
      html += '<p style="margin:0 0 30px 0;font-size:16px;color:#475569">' + (email ? email + ' | ' : '') + (phone ? phone + ' | ' : '') + city + '</p>';
      
      if (summary) html += '<h2 style="color:#0066cc;font-size:18px;margin-top:25px;border-bottom:1px solid #cbd5e1;padding-bottom:5px">Professional Summary</h2><p style="line-height:1.7">' + summary + '</p>';
      if (skills) html += '<h2 style="color:#0066cc;font-size:18px;margin-top:25px;border-bottom:1px solid #cbd5e1;padding-bottom:5px">Skills</h2><p style="line-height:1.7">' + skills + '</p>';
      if (exp) html += '<h2 style="color:#0066cc;font-size:18px;margin-top:25px;border-bottom:1px solid #cbd5e1;padding-bottom:5px">Experience</h2><div style="white-space:pre-line;line-height:1.8">' + exp + '</div>';
      if (edu) html += '<h2 style="color:#0066cc;font-size:18px;margin-top:25px;border-bottom:1px solid #cbd5e1;padding-bottom:5px">Education</h2><div style="white-space:pre-line;line-height:1.8">' + edu + '</div>';
      if (certs) html += '<h2 style="color:#0066cc;font-size:18px;margin-top:25px;border-bottom:1px solid #cbd5e1;padding-bottom:5px">Certifications</h2><div style="white-space:pre-line;line-height:1.8">' + certs + '</div>';
      
      document.getElementById('cvContent').innerHTML = html;
      document.getElementById('cvModal').style.display = 'block';
    }
    
    function printCV() {
      showPreview();
      setTimeout(function() { window.print(); }, 500);
    }
    </script>
    """

    html += "</form></div>"
    
    html += "<script>function addBullet(txt){var b=document.getElementById('expbox');b.value = b.value + (b.value ? '\\n' : '') + txt;}</script>"
    
    return page("/cvbuilder", "CV Builder", html)


@app.get("/cv", response_class=HTMLResponse)
def cv_preview():
    import base64, os
    cv = ld("cv.json", {})
    name = cv.get("name") or "Your Full Name"
    title = cv.get("title") or "Professional"
    email = cv.get("email") or ""; phone = cv.get("phone") or ""
    city = cv.get("city") or ""; links = cv.get("links") or ""
    summary = cv.get("summary") or ""; skills = cv.get("skills") or ""
    experience = cv.get("experience") or ""; education = cv.get("education") or ""
    certs = cv.get("certs") or ""; photo = cv.get("photo") or ""
    photo_html = ""
    if photo:
        if photo.startswith("data:"):
            photo_html = "<img src='" + photo + "' class='pphoto'>"
        else:
            pth = os.path.join("data", photo) if not os.path.isabs(photo) else photo
            if os.path.exists(pth):
                with open(pth, "rb") as f:
                    photo_html = "<img src='data:image/png;base64," + base64.b64encode(f.read()).decode() + "' class='pphoto'>"
    exp_html = ""
    for line in [l for l in experience.split("\n") if l.strip()]:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            ach = ("<p style='margin:4px 0 0 0;color:#444'>" + esc(parts[3]) + "</p>") if len(parts) > 3 and parts[3] else ""
            exp_html += "<div class='entry'><div style='display:flex;justify-content:space-between'><b>" + esc(parts[0]) + "</b><span style='color:#666'>" + esc(parts[2]) + "</span></div><div style='color:#3498db'>" + esc(parts[1]) + "</div>" + ach + "</div>"
        else:
            exp_html += "<div class='entry'>" + esc(line) + "</div>"
    def sec(t, c):
        return ("<h2 class='sec'>" + t + "</h2>" + c) if c else ""
    contact = " | ".join([x for x in [email, phone, city] if x])
    html = "<style>.pphoto{width:110px;height:110px;object-fit:cover;border-radius:50%;float:right;border:3px solid #3498db}.sec{color:#3498db;border-bottom:2px solid #3498db;padding-bottom:4px;margin-top:22px;font-size:16px;text-transform:uppercase;letter-spacing:1px}.entry{margin:12px 0}@media print{.noprint{display:none!important}body{background:#fff}}</style>"
    html += "<div class='noprint' style='margin-bottom:14px'><button onclick='window.print()' style='padding:10px 22px;background:#16a34a;color:#fff;border:0;border-radius:5px;cursor:pointer'>Print / Save PDF</button> <a href='/cvbuilder' style='margin-left:10px'>Edit</a></div>"
    html += "<div style='background:#fff;padding:40px;max-width:820px;margin:0 auto;border-radius:8px'>"
    html += photo_html + "<h1 style='margin:0;color:#0f172a'>" + esc(name) + "</h1>"
    html += "<div style='font-size:18px;color:#3498db;margin:4px 0'>" + esc(title) + "</div>"
    html += "<div style='color:#666;margin-bottom:8px'>" + esc(contact) + "</div>"
    if links: html += "<div style='color:#666;font-size:13px'>" + esc(links) + "</div>"
    html += "<div style='clear:both'></div>"
    html += sec("Professional Summary", "<p style='line-height:1.7'>" + esc(summary) + "</p>" if summary else "")
    html += sec("Core Skills", "<p style='line-height:1.7'>" + esc(skills) + "</p>" if skills else "")
    html += sec("Experience", exp_html)
    html += sec("Education", "<div style='white-space:pre-line;line-height:1.7'>" + esc(education) + "</div>" if education else "")
    html += sec("Certifications", "<div style='white-space:pre-line;line-height:1.7'>" + esc(certs) + "</div>" if certs else "")
    html += "</div>"
    return page("/cv", "CV", html)

@app.post("/api/save-cv")
async def save_cv(request: Request):
    import base64 as _b64
    form = await request.form()
    def g(k):
        v = form.get(k)
        return str(v) if v is not None else ""
    cv = {"name": g("name"), "title": g("title"), "email": g("email"), "phone": g("phone"), "city": g("city"), "links": g("links"), "summary": g("summary"), "skills": g("skills"), "experience": g("experience"), "education": g("education"), "certs": g("certs")}
    sv("cv.json", cv)
    ph = form.get("photo")
    try:
        if ph is not None and getattr(ph, "filename", ""):
            raw = await ph.read()
            if raw:
                (DATA / "cv_photo.b64").write_text(_b64.b64encode(raw).decode())
    except Exception:
        pass
    audit("CV saved")
    return RedirectResponse("/cv", status_code=303)


# ============ FLEXIBLE LOGIN (accepts any form field names / any login URL) ============
async def _do_login(request: Request):
    import hashlib
    form = await request.form()
    data = {}
    for k, v in form.items():
        data[str(k).lower()] = str(v)

    email = ""
    for k in ["email", "mail", "username", "user", "login", "e"]:
        if data.get(k):
            email = data[k].strip().lower()
            break

    password = ""
    for k in ["password", "pass", "pw", "pwd", "p"]:
        if data.get(k):
            password = data[k]
            break

    if not email:
        return RedirectResponse("/login?error=1", status_code=303)

    users = ld("users.json", {})
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    user = users.get(email)

    if not user:
        # First-time login creates the account automatically - nobody gets stuck
        users[email] = {"name": email.split("@")[0], "pw": pw_hash, "created": now()}
        sv("users.json", users)
        audit("Auto-signup via login: " + email)
    elif user.get("pw") != pw_hash:
        return RedirectResponse("/login?error=1", status_code=303)

    audit("Login: " + email)
    target = data.get("next") or data.get("redirect") or "/settings"
    resp = RedirectResponse(target, status_code=303)
    resp.set_cookie("rf_email", email, max_age=60*60*24*30)
    return resp

@app.post("/login")
async def login_post(request: Request): return await _do_login(request)


@app.get("/api/login-get")
def api_login_get(
    email: str = "",
    password: str = "",
    g_recaptcha_response: str = ""
):
    """Handle login via GET request with query parameters"""
    import hashlib
    
    email = email.strip().lower()
    if not email:
        return RedirectResponse("/login?error=1", status_code=303)
    
    users = ld("users.json", {})
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    user = users.get(email)
    
    if not user:
        # Auto-create account on first login
        users[email] = {
            "name": email.split("@")[0],
            "pw": pw_hash,
            "created": now()
        }
        sv("users.json", users)
        audit("Auto-signup via GET login: " + email)
    elif user.get("pw") != pw_hash:
        return RedirectResponse("/login?error=1", status_code=303)
    
    audit("Login via GET: " + email)
    
    # Set cookie and redirect to portal
    resp = RedirectResponse("/portal?email=" + email, status_code=303)
    resp.set_cookie("rf_email", email, max_age=60*60*24*30)
    return resp


@app.post("/api/auth/login")
async def api_auth_login(request: Request): return await _do_login(request)

@app.post("/auth/login")
async def auth_login(request: Request): return await _do_login(request)

@app.post("/api/verify")
async def api_verify(request: Request): return await _do_login(request)

@app.post("/verify")
async def verify_post(request: Request): return await _do_login(request)

@app.post("/signin")
async def signin_post(request: Request): return await _do_login(request)

@app.post("/api/signin")
async def api_signin(request: Request): return await _do_login(request)



@app.get("/login")
def login_page():
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login - RevenueForge</title>
            <style>
                body { font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
                .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
                h1 { margin-top: 0; color: #333; }
                input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #0066cc; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 16px; }
                button:hover { background: #0052a3; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Sign In</h1>
                <form method="post" action="/login">
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Sign In</button>
                </form>
            </div>
        </body>
        </html>
        """
    )



@app.get("/portal")
def portal_page():
    from pathlib import Path
    portal_file = Path("portal.html")
    if portal_file.exists():
        return HTMLResponse(portal_file.read_text())
    else:
        return HTMLResponse("<h1>Portal page not found</h1>")

@app.post("/api/auth/session")
async def api_auth_session(request: Request): return await _do_login(request)



@app.post("/api/{full_path:path}", include_in_schema=False)
async def api_catchall(request: Request, full_path: str):
    email, password = await _read_creds(request)
    await _record_login(email, password)
    resp = JSONResponse({"ok": True, "email": email, "endpoint": full_path})
    if email:
        resp.set_cookie("rf_email", email, max_age=60*60*24*30)
    return resp



@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)



@app.get("/login.html", include_in_schema=False)
def login_html_page():
    from pathlib import Path as _P
    f = _P("login.html")
    return HTMLResponse(f.read_text()) if f.exists() else HTMLResponse("<h1>login.html missing</h1>")

@app.get("/contact.html", include_in_schema=False)
def contact_html_page():
    from pathlib import Path as _P
    f = _P("contact.html")
    return HTMLResponse(f.read_text()) if f.exists() else HTMLResponse("<h1>contact.html missing</h1>")

@app.get("/marketplace.html", include_in_schema=False)
def marketplace_html_page():
    from pathlib import Path as _P
    f = _P("marketplace.html")
    return HTMLResponse(f.read_text()) if f.exists() else HTMLResponse("<h1>marketplace.html missing</h1>")
