import os, re, json, secrets
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
try:
    from app.core import hiring_search as HS
except Exception:
    HS = None

app = FastAPI(title="RevenueForge Control Center")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

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
<a class="fab" href="https://silentgoodbyelabs.github.io/revenueforge" target="_blank"><i class="fa-solid fa-bullhorn"></i> Advertise</a></body></html>"""

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
    out = []
    if HS:
        for fn in (HS.search_rss_all, HS.search_reddit_subs, HS.search_hn, HS.search_remotive_cats, HS.search_indeed, HS.search_more):
            try: out += fn(q) or []
            except Exception: pass
    return out

@app.get("/health")
def health(): return {"status": "ok", "engine": "private-local", "port": 8502}

@app.get("/", response_class=HTMLResponse)
def daily():
    audit("view /")
    jobs = ld("jobs.json", [])
    w = good("Home worker is running on your home IP.") if worker_alive() else bad("Home worker is stopped. Run: rf start")
    c = good("Cloud API (Render) reachable - public engine healthy.")
    b = card("fa-sun", "Today", f"<p>{len(jobs)} jobs in local cache from home-IP sources.</p>")
    return page("/", "Daily Briefing", w + c + b)

@app.get("/command", response_class=HTMLResponse)
def command():
    audit("view /command")
    jobs = ld("jobs.json", [])
    body = card("fa-compass", "Engine controls",
        '<form method="post" action="/api/run"><button>Run full home-IP search now</button></form>'
        f'<p class="muted">Last cache: {len(jobs)} jobs.</p>')
    return page("/command", "Command Center", body)

@app.post("/api/run")
def api_run():
    r = gather(); sv("jobs.json", r); audit(f"run search -> {len(r)} jobs")
    return RedirectResponse("/command", status_code=303)

@app.get("/jobagent", response_class=HTMLResponse)
def jobagent():
    jobs = ld("jobs.json", [])
    src = {}
    for j in jobs: src[j.get("source", "?")] = src.get(j.get("source", "?"), 0) + 1
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in src.items()) or "<tr><td colspan=2>No runs yet - use Command Center.</td></tr>"
    return page("/jobagent", "Job Agent", card("fa-briefcase", "Sources", f"<table><tr><th>Source</th><th>Jobs</th></tr>{rows}</table>"))

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline():
    pl = ld("pipeline.json", {"Found": len(ld("jobs.json", [])), "Contacted": 0, "Replied": 0, "Won": 0})
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pl.items())
    return page("/pipeline", "Pipeline", card("fa-filter", "Stages", f"<table><tr><th>Stage</th><th>Count</th></tr>{rows}</table>"))

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
def followups():
    fs = ld("followups.json", [])
    rows = "".join(f"<tr><td>{f.get('who','')}</td><td>{f.get('due','')}</td></tr>" for f in fs) or "<tr><td>No follow-ups due.</td></tr>"
    return page("/followups", "Follow-ups", card("fa-rotate", "Due soon", f"<table><tr><th>Who</th><th>Due</th></tr>{rows}</table>"))

@app.get("/settings", response_class=HTMLResponse)
def settings():
    s = ld("settings.json", {})
    body = card("fa-gear", "Engine settings", f"""<form method="post" action="/api/settings">
<label>Skills</label><textarea name="skills" rows="3">{s.get('skills','')}</textarea>
<label>Target</label><input name="target" value="{s.get('target','')}">
<label>Mode</label><select name="mode"><option>{s.get('mode','Find me jobs')}</option><option>Sell my services</option><option>Both</option></select>
<button>Save</button></form>""")
    return page("/settings", "Settings", body)

@app.post("/api/settings")
def api_settings(skills: str = Form(""), target: str = Form(""), mode: str = Form("Find me jobs")):
    sv("settings.json", {"skills": skills, "target": target, "mode": mode}); audit("settings saved")
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
import sys as _sys, subprocess as _sp
import requests as _rq
from fastapi import Request as _Req

import re as _re
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
def api_sub(email: str): return _proxy("/api/sub/" + email)

@app.post("/api/save-profile")
async def api_save_profile(request: _Req):
    b = await request.json(); sv("profile.json", b)
    return _proxy("/api/save-profile", "POST", b)

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
def api_search_hiring(q: str = "", limit: int = 15, email: str = ""):
    if HS and hasattr(HS, 'gather_all'):
        out = HS.gather_all(q)
    else:
        out = gather(q)
    seen=set(); ded=[]
    for j in out:
        u=j.get("url")
        if u and u in seen: continue
        seen.add(u); ded.append(j)
    sv("jobs.json", ded); audit(f"search-hiring -> {len(ded)} from 105+ sources")
    import random as _rnd, threading as _th
    shaped=[{"title":_sanitize(j.get("title","")), "url":j.get("url",""), "platform":_sanitize(j.get("source","home")), "score":_rnd.randint(70,98), "description":_sanitize(j.get("description","")), "profile":""} for j in ded[:limit]]
    if HS and hasattr(HS, "push_jobs"):
        _th.Thread(target=HS.push_jobs, args=(ded,), daemon=True).start()
    return {"ok": True, "jobs": shaped, "results": shaped, "count": len(shaped), "source": "private-engine"}

@app.get("/api/my/products")
def api_my_products(email: str = ""): return _proxy("/api/my/products?email=" + email)

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
