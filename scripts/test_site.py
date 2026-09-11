from playwright.sync_api import sync_playwright
BASE="https://silentgoodbyelabs.github.io/revenueforge"
R=[]
def ok(n,c): R.append((n,c)); print(("PASS " if c else "FAIL ")+n)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); ctx=b.new_context(); pg=ctx.new_page()
    pg.set_default_timeout(20000)
    def nav(v):
        pg.click("#burger")
        pg.wait_for_selector('#side.open', timeout=3000)
        pg.wait_for_timeout(400)
        pg.click('.nav-i[data-view="%s"]'%v)
        pg.wait_for_selector(f'#view-{v}[style*="block"], #view-{v}:not([style])', timeout=5000)
    try:
        pg.goto(BASE+"/login.html")
        pg.wait_for_timeout(3000)
        has_new = pg.locator("#li_email").count() > 0
        has_old = pg.locator("#em").count() > 0
        ok("login loads", has_new or has_old)
    except Exception as e:
        ok("login loads", False)
        print(f"    ERROR: {str(e).split(chr(10))[0]}")
    try:
        pg.goto(BASE+"/signup.html"); ok("signup loads", pg.locator("form").count()>0)
    except Exception: ok("signup loads", False)
    try:
        pg.goto(BASE+"/support.html"); ok("support page loads", pg.locator("#ms").count()>0)
    except Exception: ok("support page loads", False)
    try:
        r=pg.request.get(BASE+"/audit.html"); ok("audit page removed", r.status==404)
    except Exception: ok("audit page removed", False)
    try:
        pg.goto(BASE+"/portal.html?authed=admin@gmail.com"); pg.wait_for_timeout(2500)
        ok("portal logged in", pg.locator(".nav-i").count()>=10)
    except Exception: ok("portal logged in", False)
    try:
        pg.click("#burger")
        pg.wait_for_selector('#side.open', timeout=3000)
        ok("burger opens drawer", True)
        pg.click('.nav-i[data-view="eng"]')
        pg.wait_for_selector('#view-eng[style*="block"]', timeout=3000)
        ok("nav eng", True)
    except Exception: ok("drawer + nav eng", False)
    try:
        pg.evaluate("localStorage.removeItem('rf_cfg::admin@gmail.com')")
        pg.fill("#skills",""); pg.click("#saveBtn"); pg.wait_for_timeout(400)
        ok("save blocked when skills empty", pg.evaluate("!localStorage.getItem('rf_cfg::admin@gmail.com')"))
    except Exception: ok("save gate", False)
    try:
        pg.fill("#skills","python automation"); pg.fill("#target","startups"); pg.click("#saveBtn"); pg.wait_for_timeout(600)
        ok("save works with skills", pg.evaluate("!!localStorage.getItem('rf_cfg::admin@gmail.com')"))
        ok("save shows Saved", "Saved" in pg.locator("#saveMsg").inner_text())
    except Exception: ok("save works", False)
    try:
        pg.click("#startBtn"); pg.wait_for_timeout(4500)
        ok("start engine searches", pg.locator("#view-jobs").is_visible() or "Running" in pg.locator("#engStat").inner_text())
    except Exception: ok("start engine", False)
    try:
        nav("eng"); pg.click("#stopBtn"); pg.wait_for_timeout(500)
        ok("stop engine", "Stopped" in pg.locator("#engStat").inner_text())
    except Exception: ok("stop engine", False)
    try:
        ok("run button removed", pg.locator("#runBtn").count()==0)
    except Exception: ok("run button removed", False)
    for v in ["jobs","serv","social","pros","ana","plan","set","help","ov"]:
        try:
            # Extra retry for 'set' which can be slow
            if v == "set":
                for attempt in range(3):
                    try:
                        nav(v); ok("nav "+v, True); break
                    except:
                        if attempt == 2: raise
                        pg.wait_for_timeout(1000)
            else:
                nav(v); ok("nav "+v, True)
        except Exception as e:
            ok("nav "+v, False)
            print(f"    ERROR: {str(e).split(chr(10))[0]}")
    try:
        pg.click("#supBtn"); pg.fill("#supIn","how do I use it"); pg.click("#supSend"); pg.wait_for_timeout(700)
        ok("bot answers specifically", "Quick start" in pg.locator("#supMsgs").inner_text())
    except Exception: ok("support bot", False)
    try:
        nav("jobs"); nav("serv"); nav("pros")
        pg.go_back(); pg.wait_for_timeout(600); ok("back 1 (pros->serv)", pg.locator("#view-serv").is_visible())
        pg.go_back(); pg.wait_for_timeout(600); ok("back 2 (serv->jobs)", pg.locator("#view-jobs").is_visible())
    except Exception: ok("back button", False)
    try:
        nav("jobs"); pg.reload(); pg.wait_for_timeout(2000)
        ok("refresh stays on jobs", pg.locator("#view-jobs").is_visible())
    except Exception: ok("refresh keeps place", False)
    b.close()
print("SUMMARY:", sum(1 for _,c in R if c), "passed /", len(R))
for n,c in R:
    if not c: print("  NEEDS FIX:", n)
