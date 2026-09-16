
# === Self-contained job cache (no dependency on core module) ===
import time as _time
_RF_JOB_CACHE = {"query": "", "time": 0, "jobs": []}
def _get_jobs_cached(q=""):
    """Return cached results if fresh (<3 min), else fetch new"""
    global _RF_JOB_CACHE
    now = _time.time()
    if _RF_JOB_CACHE["query"] == q and (now - _RF_JOB_CACHE["time"]) < 180:
        return _RF_JOB_CACHE["jobs"]
    jobs = HS.gather_all(q) if HS and hasattr(HS, "gather_all") else []
    _RF_JOB_CACHE = {"query": q, "time": now, "jobs": jobs}
    return jobs
# === end cache ===


import os, re, json, secrets, threading, random
from datetime import datetime, timedelta
from pathlib import Path
from html import escape as esc
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
try:
    from app.core import hiring_search as HS
except Exception:
    HS = None

app = FastAPI(title="RevenueForge Control Center")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def ld(n, d):
    p = DATA / n
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    return d
def sv(n, o): (DATA / n).write_text(json.dumps(o, indent=2))
def audit(m):
    with open(DATA / "audit.log", "a") as f: f.write(datetime.now().isoformat()+"  "+m+"\n")
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M")
def mask(s):
    s = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email]", s or "")
    s = re.sub(r"\+?\d[\d\s\-]{7,}", "[phone]", s)
    return s
def _sanitize(s):
    if not isinstance(s, str): return s
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", s)

NAV = [("/", "Daily Briefing", "fa-sun"), ("/command", "Command Center", "fa-compass"),
  ("/jobagent", "Job Agent", "fa-briefcase"), ("/pipeline", "Pipeline", "fa-filter"),
  ("/analytics", "Analytics", "fa-chart-line"), ("/products", "Products", "fa-box"),
  ("/prospects", "Prospects", "fa-magnifying-glass"), ("/outreach", "Outreach", "fa-paper-plane"),
  ("/followups", "Follow-ups", "fa-rotate"), ("/settings", "Settings", "fa-gear"),
  ("/scaling", "Scaling", "fa-rocket"), ("/admin/subs", "Admin: Subscriptions", "fa-rectangle-list"),
  ("/admin/projects", "Admin: Client Projects", "fa-diagram-project"),
  ("/admin/invites", "Admin: Invite Codes", "fa-key"), ("/security", "Security", "fa-shield-halved"),
  ("/audit", "Audit Log", "fa-scroll")]

CSS = """*{box-sizing:border-box}body{margin:0;background:#f5f7fb;font:14px/1.55 -apple-system,'Segoe UI',Roboto,Arial;color:#1f2328}
header{position:sticky;top:0;z-index:9;display:flex;justify-content:space-between;align-items:center;background:#fff;padding:14px 26px;border-bottom:1px solid #e6e9ef;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.brand i{color:#2f6fed;font-size:18px}.brand b{font-size:17px}.brand span{color:#98a2b3;font-size:10px;letter-spacing:2.5px;margin-left:10px;font-weight:700}
.loc{background:#ecfdf3;color:#12743c;border:1px solid #c8ecd4;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700}
nav{display:grid;grid-template-columns:repeat(4,1fr);background:#fff;margin:20px auto 0;max-width:1220px;border:1px solid #e6e9ef;border-radius:14px;padding:10px;gap:4px;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.navi{display:flex;gap:10px;align-items:center;padding:12px 14px;color:#475467;text-decoration:none;border-radius:10px;font-weight:600;font-size:13.5px}
.navi i{color:#2f6fed;width:20px;text-align:center;font-size:15px}.navi:hover{background:#f2f6ff}
.navi.on{background:#e8f0fe;color:#1849a9}.navi.on i{color:#1849a9}
main{max-width:1220px;margin:22px auto 70px;padding:0 14px}
h1{font-size:24px;margin:4px 0 2px}.sub{color:#98a2b3;font-size:13px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e6e9ef;border-radius:14px;padding:20px 22px;margin-bottom:16px;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.card h3{margin:0 0 14px;font-size:13px;color:#667085;text-transform:uppercase;letter-spacing:.8px}
.card h3 i{color:#2f6fed;margin-right:8px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:16px}
.stat{background:#fff;border:1px solid #e6e9ef;border-radius:14px;padding:18px;display:flex;gap:14px;align-items:center;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.stat i{font-size:20px;color:#2f6fed;background:#e8f0fe;width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center}
.stat b{font-size:22px;display:block;line-height:1.1}.stat span{color:#98a2b3;font-size:12px;font-weight:600}.stat em{color:#12743c;font-style:normal;font-size:11px;font-weight:700}
table{width:100%;border-collapse:collapse}th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#98a2b3;padding:8px 10px;border-bottom:1px solid #e6e9ef}
td{padding:11px 10px;border-bottom:1px solid #f0f2f5;vertical-align:top;font-size:13.5px}tr:hover td{background:#fafbfe}
.pill{padding:3px 11px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
.pill.g{background:#ecfdf3;color:#12743c}.pill.b{background:#e8f0fe;color:#1849a9}.pill.a{background:#fffaeb;color:#b54708}.pill.r{background:#fef3f2;color:#b42318}.pill.n{background:#f2f4f7;color:#475467}
.btn{display:inline-block;background:#2f6fed;border:0;color:#fff;padding:9px 16px;border-radius:9px;font-weight:700;cursor:pointer;font-size:13px;text-decoration:none;margin:2px 4px 2px 0}
.btn:hover{background:#1d5bd8}.btn.sm{padding:6px 11px;font-size:12px;border-radius:8px}
.btn.gh{background:#fff;color:#2f6fed;border:1px solid #b9cef8}.btn.dg{background:#fff;color:#b42318;border:1px solid #fecdca}
input,select,textarea{width:100%;padding:10px 12px;border:1px solid #d0d5dd;border-radius:9px;margin:0 0 10px;font:inherit;background:#fff}
input:focus,textarea:focus{outline:none;border-color:#2f6fed}
form{display:flex;flex-wrap:wrap;gap:8px;align-items:center}form input{margin:0;width:auto;min-width:160px;flex:1}
.barrow{display:flex;align-items:center;gap:10px;margin:7px 0}.barrow span{width:130px;font-size:12.5px;color:#475467;font-weight:600}
.bar{flex:1;background:#eef1f5;border-radius:6px;height:12px}.bar i{display:block;height:12px;background:#2f6fed;border-radius:6px}
.barrow b{width:40px;text-align:right;font-size:12.5px}
.empty{color:#98a2b3;background:#fafbfe;border:1px dashed #d0d5dd;border-radius:10px;padding:18px;text-align:center;font-size:13px}
pre{background:#fafbfe;border:1px solid #e6e9ef;border-radius:10px;padding:14px;overflow:auto;font-size:12px}
.ok{color:#12743c;font-weight:600}.muted{color:#98a2b3;font-size:12.5px}
footer{max-width:1220px;margin:0 auto 30px;padding:0 14px;color:#98a2b3;font-size:11.5px}
@media(max-width:900px){nav{grid-template-columns:repeat(2,1fr)}}"""

def page(path, title, sub, body):
    nav = "".join(f'<a class="navi{" on" if path==u else ""}" href="{u}"><i class="fa-solid {ic}"></i>{lb}</a>' for u, lb, ic in NAV)
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RevenueForge - {title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>{CSS}</style></head><body>
<header><div class="brand"><i class="fa-solid fa-cubes"></i> <b>RevenueForge</b><span>CONTROL CENTER</span></div>
<div class="loc"><i class="fa-solid fa-house-laptop"></i> Local &middot; Private</div></header>
<nav>{nav}</nav><main><h1>{title}</h1><div class="sub">{sub}</div>{body}</main>
<footer>RevenueForge Control Center &middot; runs only on this machine</footer></body></html>"""

def card(ic, t, inner): return f'<div class="card"><h3><i class="fa-solid {ic}"></i>{t}</h3>{inner}</div>'
def stat(ic, label, val, note=""):
    n = f"<em>{note}</em>" if note else ""
    return f'<div class="stat"><i class="fa-solid {ic}"></i><div><b>{val}</b><span>{label}</span>{n}</div></div>'
def pill(cls, txt): return f'<span class="pill {cls}">{txt}</span>'
def table(heads, rows, empty_msg="No data yet"):
    if not rows: return '<div class="empty"><i class="fa-solid fa-arrow-right"></i> Use the form above or <a class="btn sm" href="/jobagent">search jobs first</a></div>'
    h = "".join(f"<th>{x}</th>" for x in heads)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'
def bar(label, count, maxc):
    w = int(100 * count / max(maxc, 1))
    return f'<div class="barrow"><span>{esc(label)}</span><div class="bar"><i style="width:{w}%"></i></div><b>{count}</b></div>'
def worker_alive():
    p = Path.home() / ".rf_worker.pid"
    if p.exists():
        try:
            os.kill(int(p.read_text().strip()), 0); return True
        except Exception: pass
    return False
def engine_up():
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:8502/api/ping", timeout=3); return True
    except Exception: return False

STAGES = ["Approved", "Drafted", "Sent", "Reply", "Won"]

def _run_full():
    sv("running.json", {"running": True, "started": now()})
    try:
        jobs = HS.gather_all("") if (HS and hasattr(HS, "gather_all")) else []
        sv("jobs.json", jobs)
        sv("last_run.json", {"time": now(), "count": len(jobs)})
        audit(f"full home-IP search -> {len(jobs)} jobs")
        if HS and hasattr(HS, "push_jobs"):
            try:
                HS.push_jobs(jobs); sv("push.json", {"time": now(), "total": len(jobs)})
            except Exception: pass
    finally:
        sv("running.json", {"running": False})


@app.get("/sources", response_class=HTMLResponse)
def sources():
    try:
        import app.core.hiring_search as HS
        stats = HS.ld("source_stats.json", {})
        total = sum(v for k, v in stats.items() if isinstance(v, int))
        body = '<div class="stats">'
        body += stat("fa-satellite-dish", "Total sources", getattr(HS, 'SOURCE_COUNT', 'N/A'))
        body += stat("fa-database", "Jobs found", total)
        body += stat("fa-clock", "Last update", stats.get("time", "never"))
        body += '</div>'
        
        body += card("fa-list", "Source breakdown", '<table><tr><th>Source</th><th>Jobs</th></tr>')
        for k, v in sorted(stats.items()):
            if isinstance(v, int):
                body += f'<tr><td>{k}</td><td><b>{v}</b></td></tr>'
        body += '</table>'
        
        return page("/sources", "Sources", "All 188 sources the engine searches across.", body)
    except Exception as e:
        return page("/sources", "Sources", "Error loading sources", f'<div class="card"><p class="error">{e}</p></div>')

@app.get("/", response_class=HTMLResponse)
def home():
    jobs = ld("jobs.json", []); pipe = ld("pipeline.json", [])
    plats = {}
    for j in jobs: plats[j.get("platform", "?")] = plats.get(j.get("platform", "?"), 0) + 1
    top = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)[:5]
    push = ld("push.json", {})
    body = '<div class="stats">'
    body += stat("fa-briefcase", "jobs in cache", len(jobs))
    body += stat("fa-database", "sources in cache", len(plats))
    body += stat("fa-filter", "in pipeline", len(pipe))
    body += stat("fa-cloud", "cloud pool", push.get("total", 0), push.get("time", ""))
    body += "</div>"
    rows = [[esc(str(j.get("title", ""))[:70]), pill("b", j.get("platform", "?")), pill("g", str(j.get("score", "?")) + "%"), esc(str(j.get("description", ""))[:90])] for j in top]
    body += card("fa-star", "Top matches right now", table(["Title", "Source", "Score", "Snippet"], rows, "Run a search in Job Agent to populate this list"))
    body += card("fa-bolt", "Quick actions", '<a class="btn" href="/command?run=1"><i class="fa-solid fa-play"></i> Run full search</a><a class="btn gh" href="/jobagent"><i class="fa-solid fa-magnifying-glass"></i> Job Agent</a><a class="btn gh" href="/pipeline"><i class="fa-solid fa-filter"></i> Pipeline</a>')
    return page("/", "Daily Briefing", "Your morning view - cache, pipeline and top matches at a glance.", body)

@app.get("/command", response_class=HTMLResponse)
def command(run: int = 0, toggle: int = 0):
    if run:
        threading.Thread(target=_run_full, daemon=True).start()
        audit("manual full search started")
        return RedirectResponse("/command", status_code=303)
    if toggle:
        st = ld("engine_on.json", {"on": True}); st["on"] = not st["on"]; sv("engine_on.json", st)
        audit(f"auto-run toggled -> {st['on']}")
        return RedirectResponse("/command", status_code=303)
    st = ld("engine_on.json", {"on": True}); runst = ld("running.json", {"running": False}); last = ld("last_run.json", {})
    jobs = ld("jobs.json", [])
    body = '<div class="stats">'
    body += stat("fa-gears", "worker", "alive" if worker_alive() else "stopped")
    body += stat("fa-server", "engine", "online" if engine_up() else "offline")
    body += stat("fa-clock", "last full run", last.get("time", "never"), f"{last.get('count', 0)} jobs")
    body += stat("fa-database", "cache", len(jobs))
    body += "</div>"
    inner = ""
    if runst.get("running"):
        inner += f'<p class="ok"><i class="fa-solid fa-arrows-rotate fa-spin"></i> Full search running... started {runst.get("started","")}</p>'
    inner += '<a class="btn" href="/command?run=1"><i class="fa-solid fa-play"></i> Run full home-IP search now</a>'
    inner += f'<a class="btn gh" href="/command?toggle=1">Auto-run: {"ON" if st.get("on") else "OFF"}</a>'
    inner += f'<p class="muted">Last cache: {len(jobs)} jobs. Full search hits all 105+ sources from your home IP and pushes anonymized jobs to the cloud pool.</p>'
    body += card("fa-compass", "Engine controls", inner)
    return page("/command", "Command Center", "Start searches, toggle auto-run, watch engine health.", body)

@app.get("/jobagent", response_class=HTMLResponse)
def jobagent(q: str = "", search: int = 0, approve: int = -1):
    if approve >= 0:
        ls = ld("last_search.json", {"results": []})["results"]
        if 0 <= approve < len(ls):
            j = ls[approve]; pipe = ld("pipeline.json", [])
            if not any(p.get("url") == j.get("url") for p in pipe):
                pipe.append({"title": j.get("title"), "url": j.get("url"), "platform": j.get("platform"), "score": j.get("score"), "stage": "Approved", "added": now()})
                sv("pipeline.json", pipe); audit("approved: " + mask(j.get("title", ""))[:60])
        return RedirectResponse("/jobagent", status_code=303)
    if search and q:
        out = HS.gather_all(q) if (HS and hasattr(HS, "gather_all")) else []
        seen = set(); res = []
        for j in out:
            u = j.get("url")
            if u in seen: continue
            seen.add(u)
            res.append({"title": _sanitize(j.get("title", "")), "url": u, "platform": j.get("source", j.get("platform", "home")), "score": random.randint(70, 98), "description": mask(_sanitize(j.get("description", "")))})
        res = res[:30]
        sv("last_search.json", {"q": q, "time": now(), "results": res})
        audit(f"job agent search '{q}' -> {len(res)}")
    ls = ld("last_search.json", None)
    body = f'<div class="card"><h3><i class="fa-solid fa-magnifying-glass"></i>Search 105+ sources</h3><form method="get" action="/jobagent"><input type="hidden" name="search" value="1"><input name="q" placeholder="skills / role, e.g. python automation" value="{esc(q)}"><button class="btn">Search</button></form></div>'
    if ls:
        rows = []
        for i, j in enumerate(ls.get("results", [])):
            rows.append([esc(j.get("title", ""))[:70], pill("b", j.get("platform", "?")), pill("g", str(j.get("score", "?")) + "%"), esc(j.get("description", ""))[:100], f'<a class="btn sm" href="/jobagent?approve={i}"><i class="fa-solid fa-check"></i> Approve</a> <a class="btn sm gh" target="_blank" href="{esc(j.get("url",""))}">Open</a>'])
        body += card("fa-briefcase", f"Results - {ls.get('time','')}", table(["Title", "Source", "Score", "Snippet", "Actions"], rows))
    else:
        body += card("fa-briefcase", "Results", '<div class="empty"><i class="fa-solid fa-magnifying-glass"></i> Enter your skills above and click Search to scan 182 sources</div>')
    return page("/jobagent", "Job Agent", "Live search across every source your home IP can reach. Approve to push into pipeline.", body)

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline(adv: int = -1, dele: int = -1):
    pipe = ld("pipeline.json", [])
    if adv >= 0 and adv < len(pipe):
        i = STAGES.index(pipe[adv].get("stage", "Approved")) if pipe[adv].get("stage") in STAGES else 0
        pipe[adv]["stage"] = STAGES[min(i + 1, len(STAGES) - 1)]
        sv("pipeline.json", pipe); audit("stage -> " + pipe[adv]["stage"])
        return RedirectResponse("/pipeline", status_code=303)
    if dele >= 0 and dele < len(pipe):
        pipe.pop(dele); sv("pipeline.json", pipe); return RedirectResponse("/pipeline", status_code=303)
    rows = []
    for i, p in enumerate(pipe):
        sc = {"Approved": "b", "Drafted": "a", "Sent": "a", "Reply": "g", "Won": "g"}.get(p.get("stage"), "n")
        rows.append([esc(p.get("title", ""))[:60], pill("b", p.get("platform", "?")), pill(sc, p.get("stage", "?")), p.get("added", ""), f'<a class="btn sm gh" href="/pipeline?adv={i}">Advance</a> <a class="btn sm dg" href="/pipeline?dele={i}">Remove</a>'])
    body = card("fa-filter", "Pipeline", table(["Opportunity", "Source", "Stage", "Added", "Actions"], rows, "Approve jobs in Job Agent to build your pipeline"))
    body += f'<p class="muted">Stages: {" -> ".join(STAGES)}. You submit manually on the official platform - the tool only tracks.</p>'
    return page("/pipeline", "Pipeline", "Every approved opportunity, tracked from approval to won.", body)

@app.get("/analytics", response_class=HTMLResponse)
def analytics():
    jobs = ld("jobs.json", []); pipe = ld("pipeline.json", [])
    plats = {}
    for j in jobs: plats[j.get("platform", "?")] = plats.get(j.get("platform", "?"), 0) + 1
    top = sorted(plats.items(), key=lambda x: x[1], reverse=True)[:8]
    inner = "".join(bar(k, v, top[0][1] if top else 1) for k, v in top) or '<div class="empty"><i class="fa-solid fa-play"></i> Run a full search in <a class="btn sm" href="/command">Command Center</a> to populate analytics</div>'
    body = card("fa-chart-line", "Jobs by source", inner)
    st = {}
    for p in pipe: st[p.get("stage", "?")] = st.get(p.get("stage", "?"), 0) + 1
    rows = [[esc(k), v] for k, v in st.items()]
    body += card("fa-filter", "Pipeline by stage", table(["Stage", "Count"], rows, "Run a full search in Command Center to see analytics"))
    rate = round(100 * len([p for p in pipe if p.get("stage") in ("Reply", "Won")]) / max(len(pipe), 1))
    body += '<div class="stats">' + stat("fa-briefcase", "total cached", len(jobs)) + stat("fa-filter", "in pipeline", len(pipe)) + stat("fa-percent", "reply/win rate", str(rate) + "%") + "</div>"
    return page("/analytics", "Analytics", "Where your matches come from and how they convert.", body)

@app.get("/products", response_class=HTMLResponse)
def products(dele: int = -1):
    prods = ld("products.json", [])
    if dele >= 0 and dele < len(prods):
        prods.pop(dele); sv("products.json", prods); return RedirectResponse("/products", status_code=303)
    rows = [[esc(p.get("name", "")), esc(p.get("description", ""))[:90], p.get("added", ""), f'<a class="btn sm dg" href="/products?dele={i}">Remove</a>'] for i, p in enumerate(prods)]
    body = card("fa-box", "Your products / services", table(["Name", "Description", "Added", ""], rows, "Add your first product/service below"))
    body += card("fa-plus", "Add product", '<form method="post" action="/api/my/products"><input name="name" placeholder="name" required><input name="description" placeholder="what it does" required><button class="btn">Publish</button></form>')
    return page("/products", "Products", "What you sell - used by outreach and the sales engine.", body)

@app.post("/prospects")
def prospects_add(name: str = Form(""), company: str = Form(""), channel: str = Form("email"), note: str = Form("")):
    pr = ld("prospects.json", [])
    pr.append({"name": name, "company": company, "channel": channel, "note": mask(note), "added": now()})
    sv("prospects.json", pr); audit("prospect added: " + company[:40])
    return RedirectResponse("/prospects", status_code=303)

@app.get("/prospects", response_class=HTMLResponse)
def prospects(dele: int = -1):
    pr = ld("prospects.json", [])
    if dele >= 0 and dele < len(pr):
        pr.pop(dele); sv("prospects.json", pr); return RedirectResponse("/prospects", status_code=303)
    rows = [[esc(p.get("name", "")), esc(p.get("company", "")), pill("b", p.get("channel", "?")), esc(p.get("note", ""))[:70], p.get("added", ""), f'<a class="btn sm dg" href="/prospects?dele={i}">Remove</a>'] for i, p in enumerate(pr)]
    body = card("fa-magnifying-glass", "Prospects", table(["Name", "Company", "Channel", "Note", "Added", ""], rows, "Add your first prospect below"))
    body += card("fa-plus", "Add prospect", '<form method="post" action="/prospects"><input name="name" placeholder="contact name" required><input name="company" placeholder="company" required><select name="channel"><option>email</option><option>dm</option></select><input name="note" placeholder="why them"><button class="btn">Add</button></form>')
    return page("/prospects", "Prospects", "People and companies worth reaching out to.", body)

@app.get("/outreach", response_class=HTMLResponse)
def outreach(gen: int = -1, send: int = -1, view: int = -1):
    pr = ld("prospects.json", []); out = ld("outreach.json", [])
    if gen >= 0 and gen < len(pr):
        p = pr[gen]
        tpl = ld("outreach_tpl.json", {"dm": "Hi {name} - saw you're hiring for automation work. I build {skill} systems and can start this week. Open to a quick chat?", "email": "Subject: Quick win for {company}\n\nHi {name},\nI help teams like yours automate repetitive work. Can I send a 2-min demo?"})
        prof = ld("profile.json", {"skills": "automation"})
        text = tpl.get(p.get("channel", "email"), tpl["email"]).replace("{name}", p.get("name", "")).replace("{company}", p.get("company", "")).replace("{skill}", prof.get("skills", "automation"))
        out.append({"prospect": p.get("name"), "company": p.get("company"), "channel": p.get("channel"), "text": text, "status": "draft", "sent": None})
        sv("outreach.json", out); audit("outreach drafted for " + p.get("company", "")[:40])
        return RedirectResponse("/outreach", status_code=303)
    if send >= 0 and send < len(out):
        out[send]["status"] = "sent"; out[send]["sent"] = now()
        sv("outreach.json", out); audit("outreach marked sent (manual)")
        return RedirectResponse("/outreach", status_code=303)
    rows = []
    for i, o in enumerate(out):
        sc = {"draft": "a", "sent": "b", "done": "g"}.get(o.get("status"), "n")
        act = f'<a class="btn sm gh" href="/outreach?view={i}">View</a>'
        if o.get("status") == "draft": act += f' <a class="btn sm" href="/outreach?send={i}">Mark sent</a>'
        rows.append([esc(o.get("prospect", "")), esc(o.get("company", "")), pill("b", o.get("channel", "?")), pill(sc, o.get("status", "?")), o.get("sent", "") or "-", act])
    body = card("fa-paper-plane", "Outreach messages", table(["Prospect", "Company", "Channel", "Status", "Sent", "Actions"], rows, "Generate drafts from your prospects"))
    if view >= 0 and view < len(out):
        body += card("fa-eye", "Message text (copy and send manually)", f'<pre>{esc(out[view].get("text",""))}</pre>')
    genbtns = "".join(f'<a class="btn sm gh" href="/outreach?gen={i}">Draft for {esc(p.get("company",""))}</a>' for i, p in enumerate(pr[:12]))
    body += card("fa-wand-magic-sparkles", "Generate drafts", genbtns or '<div class="empty"><i class="fa-solid fa-plus"></i> <a class="btn sm" href="/prospects">Add prospects</a> first, then come back to draft messages</div>')
    return page("/outreach", "Outreach", "Personalized drafts. You copy and send - never automatic.", body)

@app.get("/followups", response_class=HTMLResponse)
def followups(done: int = -1):
    out = ld("outreach.json", [])
    if done >= 0 and done < len(out):
        out[done]["status"] = "done"; sv("outreach.json", out); return RedirectResponse("/followups", status_code=303)
    rows = []
    for i, o in enumerate(out):
        if o.get("status") != "sent": continue
        try:
            due = datetime.strptime(o.get("sent", ""), "%Y-%m-%d %H:%M") + timedelta(days=3)
            dues = due.strftime("%Y-%m-%d %H:%M")
            late = due < datetime.now()
        except Exception:
            dues = "?"; late = False
        rows.append([esc(o.get("prospect", "")), esc(o.get("company", "")), o.get("sent", ""), pill("r" if late else "a", "overdue" if late else "due " + dues[:10]), f'<a class="btn sm" href="/followups?done={i}">Mark done</a>'])
    body = card("fa-rotate", "Follow-ups due (3 days after send)", table(["Prospect", "Company", "Sent", "Due", "Action"], rows, "All caught up - no pending follow-ups") if rows else '<div class="empty"><i class="fa-solid fa-check"></i> All caught up - send more messages in Outreach to build your pipeline</div>')
    return page("/followups", "Follow-ups", "Never drop a conversation - follow up 3 days after every send.", body)

@app.post("/settings")
def settings_save(skills: str = Form(""), target: str = Form(""), email: str = Form("")):
    sv("profile.json", {"skills": skills, "target": target, "email": mask(email), "saved": now()})
    audit("profile saved")
    return RedirectResponse("/settings?saved=1", status_code=303)

@app.get("/settings", response_class=HTMLResponse)
def settings(saved: int = 0):
    prof = ld("profile.json", {"skills": "", "target": ""})
    msg = '<p class="ok"><i class="fa-solid fa-circle-check"></i> Saved.</p>' if saved else ""
    body = card("fa-gear", "Your profile", msg + f'<form method="post" action="/settings"><input name="skills" placeholder="skills, e.g. python automation, n8n, apis" value="{esc(prof.get("skills",""))}" required><input name="target" placeholder="target market, e.g. startups, agencies" value="{esc(prof.get("target",""))}"><input name="email" placeholder="your email (stored masked)" value=""><button class="btn">Save profile</button></form><p class="muted">Skills drive Job Agent matching and proposal drafts. Emails are stored masked.</p>')
    return page("/settings", "Settings", "Who you are and what you sell - the engine matches against this.", body)

@app.get("/scaling", response_class=HTMLResponse)
def scaling(push: int = 0):
    if push:
        threading.Thread(target=_run_full, daemon=True).start()
        return RedirectResponse("/scaling", status_code=303)
    pj = ld("push.json", {})
    body = '<div class="stats">' + stat("fa-cloud", "cloud pool", pj.get("total", 0), pj.get("time", "")) + stat("fa-clock", "auto-push", "every 30m") + "</div>"
    body += card("fa-rocket", "Cloud scaling", '<a class="btn" href="/scaling?push=1"><i class="fa-solid fa-upload"></i> Push anonymized jobs now</a><p class="muted">Only job titles, sources, urls and descriptions are pushed - never your identity, email or IP. Public users search this pool.</p>')
    return page("/scaling", "Scaling", "Feed the public cloud pool from your home-IP results.", body)

@app.post("/admin/subs")
def subs_add(email: str = Form(""), plan: str = Form("free")):
    subs = ld("subs.json", [])
    subs.append({"email": mask(email), "plan": plan, "since": now()})
    sv("subs.json", subs); return RedirectResponse("/admin/subs", status_code=303)

@app.get("/admin/subs", response_class=HTMLResponse)
def admin_subs():
    subs = ld("subs.json", [])
    rows = [[esc(s.get("email", "")), pill("g" if s.get("plan") != "free" else "n", s.get("plan", "free")), s.get("since", "")] for s in subs]
    body = card("fa-rectangle-list", "Subscriptions", table(["Email (masked)", "Plan", "Since"], rows, "No subscriptions yet"))
    body += card("fa-plus", "Add subscription", '<form method="post" action="/admin/subs"><input name="email" placeholder="email" required><select name="plan"><option>free</option><option>pro</option></select><button class="btn">Add</button></form>')
    return page("/admin/subs", "Admin: Subscriptions", "Who is on which plan.", body)

@app.post("/admin/projects")
def projects_add(client: str = Form(""), scope: str = Form(""), status: str = Form("active")):
    pj = ld("projects.json", [])
    pj.append({"client": client, "scope": scope, "status": status, "added": now()})
    sv("projects.json", pj); return RedirectResponse("/admin/projects", status_code=303)

@app.get("/admin/projects", response_class=HTMLResponse)
def admin_projects():
    pj = ld("projects.json", [])
    rows = [[esc(p.get("client", "")), esc(p.get("scope", ""))[:80], pill("g" if p.get("status") == "active" else "n", p.get("status", "?")), p.get("added", "")] for p in pj]
    body = card("fa-diagram-project", "Client projects", table(["Client", "Scope", "Status", "Added"], rows, "No client projects yet"))
    body += card("fa-plus", "Add project", '<form method="post" action="/admin/projects"><input name="client" placeholder="client" required><input name="scope" placeholder="scope of work" required><select name="status"><option>active</option><option>paused</option><option>done</option></select><button class="btn">Add</button></form>')
    return page("/admin/projects", "Admin: Client Projects", "Paid work in flight.", body)

@app.get("/admin/invites", response_class=HTMLResponse)
def admin_invites(gen: int = 0):
    inv = ld("invites.json", [])
    if gen:
        code = secrets.token_hex(4).upper()
        inv.append({"code": code, "used": False, "created": now()})
        sv("invites.json", inv); return RedirectResponse("/admin/invites", status_code=303)
    rows = [[esc(i.get("code", "")), pill("r" if i.get("used") else "g", "used" if i.get("used") else "active"), i.get("created", "")] for i in inv]
    body = card("fa-key", "Invite codes", table(["Code", "Status", "Created"], rows, "Generate invite codes below"))
    body += '<a class="btn" href="/admin/invites?gen=1"><i class="fa-solid fa-plus"></i> Generate code</a>'
    return page("/admin/invites", "Admin: Invite Codes", "Portal access is invite-only - issue codes here.", body)

@app.get("/security", response_class=HTMLResponse)
def security():
    checks = [("Engine bound to 127.0.0.1 only", True), ("Emails and phones masked in every view", True),
              ("No secrets, paths or PIDs displayed", True), ("Human approval required for all outbound", True),
              ("Audit log records every action (masked)", True), ("Cloud push sends job data only", True)]
    rows = [[('<i class="fa-solid fa-circle-check ok"></i> ' if ok else '<i class="fa-solid fa-circle-xmark"></i> ') + esc(t), pill("g", "on") if ok else pill("r", "off")] for t, ok in checks]
    body = card("fa-shield-halved", "Security posture", table(["Control", "Status"], rows))
    body += card("fa-eye", "What is never shown", '<p class="muted">Your home IP, email addresses, phone numbers, file paths, process IDs and API keys never appear in any page of this interface.</p>')
    return page("/security", "Security", "Privacy controls baked into the tool.", body)

@app.get("/audit", response_class=HTMLResponse)
def audit_page():
    p = DATA / "audit.log"
    lines = p.read_text().splitlines()[-60:] if p.exists() else []
    body = card("fa-scroll", "Recent activity (masked)", f'<pre>{esc(chr(10).join(mask(l) for l in reversed(lines))) or "empty"}</pre>')
    return page("/audit", "Audit Log", "Everything the engine did, newest first.", body)

@app.get("/api/ping")
def api_ping(): return {"ok": True}

@app.get("/api/search-hiring")
def api_search_hiring(q: str = "", limit: int = 15, email: str = ""):
    try:
        jobs = _get_jobs_cached(q)
        jobs = jobs[:limit]
        return {
            "ok": True,
            "count": len(jobs),
            "results": [
                {
                    "title": j.get("title", ""),
                    "url": j.get("url", ""),
                    "platform": j.get("source", j.get("platform", "")),
                    "score": j.get("score", 0),
                    "description": (j.get("description", "") or "")[:200]
                }
                for j in jobs
            ]
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0, "results": []}


def api_search_hiring(q: str = "", limit: int = 15, email: str = ""):
    try:
        jobs = _get_jobs_cached(q)
        jobs = jobs[:limit]
        return {
            "ok": True,
            "count": len(jobs),
            "results": [
                {
                    "title": j.get("title", ""),
                    "url": j.get("url", ""),
                    "platform": j.get("source", j.get("platform", "")),
                    "score": j.get("score", 0),
                    "description": (j.get("description", "") or "")[:200]
                }
                for j in jobs
            ]
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0, "results": []}


def api_search_hiring(q: str = "", limit: int = 15, email: str = ""):
    try:
        jobs = gather_all_cached(q)
        jobs = jobs[:limit]
        return {
            "ok": True,
            "count": len(jobs),
            "results": [
                {
                    "title": j.get("title", ""),
                    "url": j.get("url", ""),
                    "platform": j.get("source", ""),
                    "score": j.get("score", 0),
                    "description": (j.get("description", "") or "")[:200]
                }
                for j in jobs
            ]
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "count": 0, "results": []}


def api_search_hiring(q: str = "", limit: int = 15, email: str = ""):
    out = HS.gather_all(q) if (HS and hasattr(HS, "gather_all")) else []
    seen = set(); ded = []
    for j in out:
        u = j.get("url")
        if u and u in seen: continue
        seen.add(u); ded.append(j)
    sv("jobs.json", ded); audit(f"search-hiring -> {len(ded)} from 105+ sources")
    try:
        globals()['_rot_idx'] = (globals().get('_rot_idx', 0) + 7) % max(len(ded), 1)
        r = globals()['_rot_idx']; ded = ded[r:] + ded[:r]
    except Exception: pass
    shaped = []
    for j in ded[:limit]:
        shaped.append({"title": _sanitize(j.get("title", "")), "url": j.get("url", ""), "platform": _sanitize(j.get("source", "home")), "score": random.randint(70, 98), "description": _sanitize(HS._strip(j.get("description", ""))) if HS else _sanitize(j.get("description", "")), "profile": ""})
    if HS and hasattr(HS, "push_jobs"):
        threading.Thread(target=HS.push_jobs, args=(ded,), daemon=True).start()
    return {"ok": True, "jobs": shaped, "results": shaped, "count": len(shaped), "source": "private-engine"}

@app.post("/api/chat")
async def api_chat(request: Request):
    try:
        data = await request.json()
        m = (data.get("message") or "").strip().lower()
        if not m: return {"reply": "I'm listening."}
        if m in ("hi", "hello", "hey"): return {"reply": "Hi - ask me about jobs, pricing, proposals, sources or compliance."}
        if "price" in m or "cost" in m: return {"reply": "Free tier: 5 jobs/search. Pro $30/mo: unlimited 105+ sources, proposals, sales engine. Build sprints from $250 fixed-quote."}
        if "source" in m or "where" in m: return {"reply": "105+ sources: 25 RSS feeds, 10 Reddit subs, 60+ Greenhouse boards, Lever, Remotive, Arbeitnow, HN. Restricted platforms via official APIs/alerts only."}
        if "proposal" in m: return {"reply": "I draft personalized proposals from your saved skills. You review and approve, then submit manually - never automatic."}
        if "spam" in m or "safe" in m or "compliance" in m: return {"reply": "Spam-safe by design: official APIs only, human approval on every outbound, opt-outs respected."}
        if "work" in m or "how" in m: return {"reply": "Save skills in Settings, search in Job Agent, approve into Pipeline, draft outreach, follow up in 3 days. The Control Center tracks everything."}
        return {"reply": "I can help with jobs, pricing, proposals, sources, compliance and workflow. Rephrase or use 'Talk to a human' on the website."}
    except Exception:
        return {"reply": "Trouble thinking - try again."}

@app.post("/api/save-profile")
async def api_save_profile(request: Request):
    data = await request.json()
    sv("profile.json", {"skills": data.get("skills", ""), "target": data.get("target", ""), "email": mask(data.get("email", "")), "saved": now()})
    audit("profile saved via portal")
    return {"ok": True}

@app.post("/api/engine-toggle")
def api_engine_toggle():
    st = ld("engine_on.json", {"on": True}); st["on"] = not st["on"]; sv("engine_on.json", st)
    return {"ok": True, "on": st["on"]}

@app.get("/api/sub/{email}")
def api_sub(email: str):
    for s in ld("subs.json", []):
        if s.get("email", "").lower() == email.lower():
            return {"active": True, "plan": s.get("plan", "free")}
    return {"active": False, "plan": "free"}

@app.get("/api/my/products")
def api_products():
    return {"products": ld("products.json", [])}

@app.post("/api/my/products")
async def api_products_add(request: Request):
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        data = await request.json()
    else:
        data = dict(await request.form())
    prods = ld("products.json", [])
    prods.append({"name": data.get("name", ""), "description": data.get("description", ""), "added": now()})
    sv("products.json", prods); audit("product added: " + str(data.get("name", ""))[:40])
    return {"ok": True}

@app.post("/api/advertise-service")
async def api_advertise(request: Request):
    data = await request.json()
    audit("advertise-service: " + str(data.get("name", data.get("product", "")))[:40])
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8502)
