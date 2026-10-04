import os, re, json, secrets
from datetime import datetime
from pathlib import Path
from fastapi import Request, FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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

@app.get("/", response_class=HTMLResponse)
def daily():
    jobs = ld("jobs.json", [])
    apps = ld("applications.json", [])
    msgs = ld("messages.json", [])
    pl = ld("pipeline.json", {"Found": 0, "Contacted": 0, "Replied": 0, "Won": 0})

    html = "<div class='card'><h3><i class='fa-solid fa-sun'></i> Today</h3>"
    html += "<p><strong>" + str(len(jobs)) + "</strong> jobs hunted for you from home-IP sources.</p>"
    html += "<p><strong>" + str(len(apps)) + "</strong> jobs in your pipeline.</p>"
    html += "<p><strong>" + str(len(msgs)) + "</strong> outreach messages sent.</p>"
    if worker_alive():
        html += "<p class='ok'>Home worker running - auto-hunt every 30 minutes.</p>"
    else:
        html += "<p class='err'>Home worker stopped. Run: rf start</p>"
    html += "</div>"

    html += "<div class='card'><h3><i class='fa-solid fa-filter'></i> Pipeline at a glance</h3><table><tr><th>Stage</th><th>Count</th></tr>"
    for k in ["Found", "Contacted", "Replied", "Won"]:
        html += "<tr><td>" + k + "</td><td>" + str(pl.get(k, 0)) + "</td></tr>"
    html += "</table></div>"

    sources = {}
    for j in jobs:
        s = j.get("source", "?")
        sources[s] = sources.get(s, 0) + 1
    top = sorted(sources.items(), key=lambda x: -x[1])[:8]
    html += "<div class='card'><h3><i class='fa-solid fa-trophy'></i> Top platforms</h3><table><tr><th>Platform</th><th>Jobs</th></tr>"
    for s, c in top:
        html += "<tr><td>" + esc(str(s)) + "</td><td>" + str(c) + "</td></tr>"
    html += "</table></div>"

    return page("/", "Daily Briefing", html)


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


@app.post("/api/hunt-now")
def hunt_now():
    try:
        import subprocess, sys as _S
        subprocess.Popen([_S.executable, "scripts/live_hunt.py"], stdout=open("/tmp/live_hunt.log", "w"), stderr=subprocess.STDOUT)
        audit("manual live hunt triggered")
        return RedirectResponse("/jobagent", status_code=303)
    except Exception as _e:
        return RedirectResponse("/jobagent", status_code=303)


@app.get("/proposal", response_class=HTMLResponse)
def proposal(title: str = "", url: str = "", source: str = ""):
    try:
        NL = chr(10)
        Q = chr(34)
        profile = ld("profile.json", {})
        skills = str(profile.get("skills", "software development"))
        target = str(profile.get("target", ""))
        experience = str(profile.get("experience", "Mid-Level"))
        location = str(profile.get("location", "Remote"))
        min_sal = str(profile.get("min_salary", ""))

        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        if not skill_list:
            skill_list = ["software development"]
        skills_txt = ", ".join(skill_list)
        primary = skill_list[0]

        L = []
        L.append("Subject: Application and Proposal - " + str(title))
        L.append("")
        L.append("Dear Hiring Team,")
        L.append("")
        L.append("I am writing to express my sincere interest in the " + str(title) + " position currently advertised on " + str(source) + ". After reviewing the role and your company's mission, I am convinced that my background in " + skills_txt + " and my proven ability to deliver end-to-end technical solutions make me a strong candidate for this opportunity. I would like to submit both a cover letter and a brief proposal for your consideration.")
        L.append("")
        L.append("COVER LETTER")
        L.append("--------------")
        L.append("")
        L.append("Over the past several years I have worked across the full product and engineering lifecycle - from requirements gathering, architecture and design, through implementation, testing, deployment and monitoring. My primary strength lies in " + primary + ", but I am equally comfortable working with " + skills_txt + " in production environments where reliability, performance and code quality matter.")
        L.append("")
        L.append("In my most recent work I have:")
        L.append("- Designed and shipped features that moved measurable business outcomes for " + (target if target else "fast-moving product teams") + ".")
        L.append("- Built maintainable, well-documented services backed by automated tests and clear observability.")
        L.append("- Collaborated closely with product, design and operations teams to translate ambiguous problems into shippable increments.")
        L.append("- Operated effectively in fully remote, asynchronous environments with clear written communication and proactive stakeholder updates.")
        L.append("")
        L.append("What sets me apart is my ownership mindset. I do not simply close tickets - I think about the long-term health of the systems I build, the experience of the users who depend on them, and the team that will maintain them after me. I treat every engagement as a partnership: your goals become my goals, and I iterate until we have a shared definition of done.")
        L.append("")
        L.append("PROPOSAL FOR ENGAGEMENT")
        L.append("-----------------------")
        L.append("")
        L.append("To demonstrate the value I can bring quickly, I propose the following structure for our working relationship:")
        L.append("")
        L.append("1. DISCOVERY (first 1-2 weeks)")
        L.append("   - Technical and product onboarding with your team.")
        L.append("   - Audit of current architecture, codebase, tooling and delivery process.")
        L.append("   - Delivery of a written findings document highlighting quick wins and medium-term risks.")
        L.append("")
        L.append("2. FIRST DELIVERY (weeks 2-6)")
        L.append("   - Pick one high-impact, well-scoped item from the findings.")
        L.append("   - Deliver it end-to-end with tests, documentation and deployment.")
        L.append("   - Weekly written status updates and a short demo at the end of each sprint.")
        L.append("")
        L.append("3. ONGOING ENGAGEMENT (month 2 onwards)")
        L.append("   - Continue delivering features with the same cadence.")
        L.append("   - Mentor junior engineers where helpful.")
        L.append("   - Propose improvements to architecture, tooling and process based on real patterns I observe in the codebase.")
        L.append("")
        L.append("I am comfortable working at " + (experience if experience else "Mid-Level") + " capacity, in " + (location if location else "Remote") + " settings, and I am available to begin immediately. Compensation expectations are in the range of " + (min_sal + " USD/year" if min_sal else "competitive, aligned with the role and scope") + " - but I am flexible and happy to discuss a structure that works for both sides, including a paid trial period to de-risk the engagement for you.")
        L.append("")
        L.append("NEXT STEPS")
        L.append("----------")
        L.append("")
        L.append("I would welcome a 30-minute conversation to:")
        L.append("- Understand the most important outcomes your team needs in the next 90 days.")
        L.append("- Walk you through one or two relevant projects from my recent work.")
        L.append("- Complete any technical exercise, take-home assignment or pair-programming session you feel would help assess fit.")
        L.append("")
        L.append("Please feel free to suggest a time that suits you, or to share any additional information you would find useful from my side. I am responsive and easy to reach.")
        L.append("")
        L.append("Thank you very much for your time and consideration. I look forward to the possibility of working together.")
        L.append("")
        L.append("Kind regards,")
        L.append("[Your full name]")
        L.append("[Your email]")
        L.append("[Your phone]")
        L.append("[Your portfolio / GitHub / LinkedIn]")
        proposal_text = NL.join(L)

        C = []
        C.append("CURRICULUM VITAE")
        C.append("================")
        C.append("")
        C.append("[YOUR FULL NAME]")
        C.append("[email]  |  [phone]  |  [city, country]  |  [github/portfolio link]")
        C.append("")
        C.append("PROFESSIONAL SUMMARY")
        C.append("Software professional specialised in " + skills_txt + ", with a track record of delivering reliable, production-grade systems in fast-moving " + (target if target else "product") + " environments. Comfortable working end-to-end from requirements through deployment and monitoring.")
        C.append("")
        C.append("CORE TECHNICAL SKILLS")
        C.append("- Languages and frameworks: " + skills_txt)
        C.append("- APIs, backend services, relational and document databases")
        C.append("- Testing strategies, CI/CD, infrastructure as code, observability")
        C.append("- Remote collaboration, written communication, code review, mentoring")
        C.append("")
        C.append("EXPERIENCE")
        C.append("")
        C.append("Most Recent Role - [Company] - [dates]")
        C.append("  * Led design and delivery of features using " + primary + " that shipped to production and drove measurable outcomes.")
        C.append("  * Improved system reliability through automated tests, monitoring and careful refactoring.")
        C.append("  * Mentored teammates and contributed to a strong engineering culture of ownership.")
        C.append("")
        C.append("Previous Role - [Company] - [dates]")
        C.append("  * Delivered end-to-end projects with modern tooling and clean code practices.")
        C.append("  * Partnered with product and design to translate ambiguous problems into shippable increments.")
        C.append("")
        C.append("EDUCATION AND CERTIFICATIONS")
        C.append("[Degree / certification - institution - year]")
        C.append("")
        C.append("SELECTED PROJECTS")
        C.append("  * [Project 1] - brief description and outcome.")
        C.append("  * [Project 2] - brief description and outcome.")
        C.append("")
        C.append("REFERENCES")
        C.append("Available on request.")
        cv_text = NL.join(C)

        h = []
        h.append("<div class='card'>")
        h.append("<h3><i class='fa-solid fa-file-lines'></i> Application and Proposal for: " + str(title) + "</h3>")
        if url:
            h.append("<p><a href='" + str(url) + "' target='_blank'>Open original job posting</a></p>")
        h.append("<pre id='prop' style='white-space:pre-wrap;background:#f5f5f5;padding:14px;border-radius:6px;max-height:600px;overflow:auto'>" + str(proposal_text) + "</pre>")
        h.append("<button onclick=" + Q + "copyEl('prop')" + Q + ">Copy proposal</button> ")
        h.append("<button onclick='window.print()'>Print / Save as PDF</button>")
        h.append("</div>")
        h.append("<div class='card'>")
        h.append("<h3><i class='fa-solid fa-id-card'></i> Matching CV</h3>")
        h.append("<pre id='cv' style='white-space:pre-wrap;background:#f5f5f5;padding:14px;border-radius:6px;max-height:600px;overflow:auto'>" + str(cv_text) + "</pre>")
        h.append("<button onclick=" + Q + "copyEl('cv')" + Q + ">Copy CV</button> ")
        h.append("<button onclick='window.print()'>Print / Save as PDF</button>")
        h.append("</div>")
        h.append("<script>function copyEl(id){var el=document.getElementById(id);if(!el)return;navigator.clipboard.writeText(el.innerText).then(function(){alert('Copied to clipboard');});}</script>")
        return page("/proposal", "Proposal and CV", NL.join(h))
    except Exception as _e:
        return "<h1>Error: " + str(_e) + "</h1>"

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
    html += "</form></div>"
    
    html += "<script>function addBullet(txt){var b=document.getElementById('expbox');b.value = b.value + (b.value ? '\\n' : '') + txt;}</script>"
    
    return page("/cvbuilder", "CV Builder", html)


@app.get("/cv", response_class=HTMLResponse)
def cv_preview():
    cv = ld("cv.json", {})
    name = cv.get("name") or "YOUR FULL NAME"
    title = cv.get("title") or "Software Engineer"
    email = cv.get("email") or "your.email@example.com"
    phone = cv.get("phone") or "+000 000 0000"
    city = cv.get("city") or "City, Country"
    links = cv.get("links") or "github.com/yourhandle  |  linkedin.com/in/yourhandle"
    summary = cv.get("summary") or "Results-driven software engineer with a proven record of designing and delivering scalable, production-grade systems. Combines deep technical expertise with clear written communication, an ownership mindset and a focus on measurable business outcomes."
    skills = cv.get("skills") or "Python, JavaScript, SQL, React, Docker, AWS, Git, REST APIs"
    experience = cv.get("experience") or ("Senior Software Engineer | TechCorp | 2023 - Present | Led delivery of scalable backend services serving 1M+ users; cut API latency by 45%" + chr(10) + "Software Engineer | StartupXYZ | 2021 - 2023 | Built REST APIs and dashboards; introduced automated testing raising coverage to 90%")
    education = cv.get("education") or "BSc Computer Science | University Name | 2017 - 2021"
    certs = cv.get("certs") or "AWS Certified Developer" + chr(10) + "Professional Scrum Master I"

    photo_html = ""
    pf = DATA / "cv_photo.b64"
    if pf.exists():
        photo_html = "<img class='cvphoto' src='data:image/jpeg;base64," + pf.read_text().strip() + "' alt='photo'>"

    skill_tags = ""
    for s in str(skills).split(","):
        s = s.strip()
        if s:
            skill_tags += "<span class='tag'>" + esc(s) + "</span>"

    exp_html = ""
    for line in str(experience).split(chr(10)):
        line = line.strip()
        if not line:
            continue
        parts = [x.strip() for x in line.split("|")]
        exp_html += "<div class='item'>"
        exp_html += "<div class='ihead'>" + esc(parts[0]) + "</div>"
        if len(parts) > 1:
            meta = esc(parts[1])
            if len(parts) > 2:
                meta += " &bull; " + esc(parts[2])
            exp_html += "<div class='imeta'>" + meta + "</div>"
        if len(parts) > 3:
            exp_html += "<div class='ibody'>" + esc(parts[3]) + "</div>"
        exp_html += "</div>"
    if not exp_html:
        exp_html = "<div class='ibody'>Add your experience in the CV Builder.</div>"

    edu_html = ""
    for line in str(education).split(chr(10)):
        if line.strip():
            edu_html += "<div class='item'><div class='ibody'>" + esc(line.strip()) + "</div></div>"

    cert_html = ""
    for line in str(certs).split(chr(10)):
        if line.strip():
            cert_html += "<li>" + esc(line.strip()) + "</li>"

    css = "<style>"
    css += "@media print { .noprint { display:none !important; } body { background:white !important; } .sheet { box-shadow:none !important; margin:0 !important; max-width:100% !important; } }"
    css += "body { background:#e8ecf1; margin:0; font-family:'Segoe UI',Arial,Helvetica,sans-serif; }"
    css += ".sheet { max-width:820px; margin:24px auto; background:white; box-shadow:0 2px 18px rgba(0,0,0,.18); }"
    css += ".head { display:flex; gap:26px; align-items:center; padding:36px 42px; background:#1f3b57; color:white; }"
    css += ".cvphoto { width:104px; height:104px; border-radius:50%; object-fit:cover; border:3px solid white; flex:none; }"
    css += ".head h1 { margin:0; font-size:30px; letter-spacing:1px; }"
    css += ".head h2 { margin:4px 0 10px; font-size:16px; font-weight:400; color:#bcd3e8; }"
    css += ".contact { font-size:13px; line-height:1.7; color:#dce8f3; }"
    css += ".body { padding:30px 42px 44px; }"
    css += "h3.sec { font-size:13px; letter-spacing:2px; color:#1f3b57; border-bottom:2px solid #1f3b57; padding-bottom:6px; margin:26px 0 14px; text-transform:uppercase; }"
    css += ".tag { display:inline-block; background:#eef3f8; color:#1f3b57; border:1px solid #c9d8e6; border-radius:14px; padding:3px 12px; font-size:12px; margin:0 6px 6px 0; }"
    css += ".item { margin-bottom:14px; border-left:3px solid #2e6da4; padding-left:14px; }"
    css += ".ihead { font-weight:600; color:#22303c; font-size:14.5px; }"
    css += ".imeta { font-size:12px; color:#7a8794; margin:2px 0; }"
    css += ".ibody { font-size:13.5px; color:#3d4a56; line-height:1.6; }"
    css += ".bar { position:fixed; top:12px; right:12px; }"
    css += ".bar a, .bar button { display:inline-block; margin-left:8px; padding:9px 16px; background:#2e6da4; color:white; border:none; border-radius:4px; text-decoration:none; font-size:13px; cursor:pointer; }"
    css += "</style>"

    h = css
    h += "<div class='bar noprint'><button onclick='window.print()'>Print / Save PDF</button><a href='/cvbuilder'>Edit CV</a></div>"
    h += "<div class='sheet'>"
    h += "<div class='head'>" + photo_html + "<div><h1>" + esc(name) + "</h1><h2>" + esc(title) + "</h2>"
    h += "<div class='contact'>" + esc(email) + " &bull; " + esc(phone) + " &bull; " + esc(city) + "<br>" + esc(links) + "</div></div></div>"
    h += "<div class='body'>"
    h += "<h3 class='sec'>Professional Summary</h3><p class='ibody'>" + esc(summary) + "</p>"
    h += "<h3 class='sec'>Core Skills</h3><div>" + skill_tags + "</div>"
    h += "<h3 class='sec'>Professional Experience</h3>" + exp_html
    h += "<h3 class='sec'>Education</h3>" + edu_html
    if cert_html:
        h += "<h3 class='sec'>Certifications</h3><ul class='ibody'>" + cert_html + "</ul>"
    h += "</div></div>"
    return HTMLResponse(content=h)


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
