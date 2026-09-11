from playwright.sync_api import sync_playwright
BASE="https://silentgoodbyelabs.github.io/revenueforge"
PAGES = [
    "index.html","pricing.html","marketplace.html","about.html","services.html",
    "blog.html","faq.html","contact.html","testimonials.html","case-studies.html",
    "demo.html","video.html","privacy.html","terms.html","404.html",
    "login.html","signin.html","signup.html","register.html","support.html","audit.html","portal.html"
]
results=[]
def ok(n,c,detail=""):
    results.append((n,c))
    print(("PASS " if c else "FAIL ")+n+((" | "+detail) if detail and not c else ""))
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    print("\n========== PART 1: ALL PAGES LOAD CLEAN ==========")
    for page in PAGES:
        ctx=b.new_context(); pg=ctx.new_page()
        errs=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        try:
            pg.goto(BASE+"/"+page, timeout=20000)
            pg.wait_for_timeout(1500)
            clean = len(errs)==0
            ok(f"page {page}", clean, "; ".join(errs[:2]))
        except Exception as e:
            ok(f"page {page}", False, str(e).split(chr(10))[0])
        ctx.close()
    print("\n========== PART 2: MOBILE (390x844) ==========")
    for page in ["index.html","pricing.html","portal.html","signup.html"]:
        ctx=b.new_context(viewport={"width":390,"height":844}, user_agent="Mozilla/5.0 (iPhone)")
        pg=ctx.new_page()
        try:
            url = BASE+"/"+page + ("?authed=admin@gmail.com" if page=="portal.html" else "")
            pg.goto(url); pg.wait_for_timeout(2000)
            body_w = pg.evaluate("document.body.scrollWidth")
            no_hscroll = body_w <= 400
            ok(f"mobile {page} no horizontal scroll", no_hscroll, f"width={body_w}")
        except Exception as e:
            ok(f"mobile {page}", False, str(e).split(chr(10))[0])
        ctx.close()
    print("\n========== PART 3: PORTAL FULL FUNCTION ==========")
    ctx=b.new_context(); pg=ctx.new_page()
    pg.set_default_timeout(20000)
    def nav(v):
        pg.click("#burger"); pg.wait_for_selector('#side.open', timeout=3000); pg.wait_for_timeout(300)
        pg.click(f'.nav-i[data-view="{v}"]'); pg.wait_for_selector(f'#view-{v}', timeout=3000); pg.wait_for_timeout(400)
    try:
        pg.goto(BASE+"/portal.html?authed=admin@gmail.com"); pg.wait_for_timeout(2500)
        ok("portal logged in", pg.locator(".nav-i").count()>=10)
    except Exception as e: ok("portal logged in", False)
    for v in ["ov","eng","jobs","serv","social","pros","ana","plan","set","help"]:
        try:
            nav(v); ok("portal nav "+v, pg.locator("#view-"+v).is_visible())
        except Exception as e: ok("portal nav "+v, False, str(e).split(chr(10))[0])
    # save gate + save (skills are in view-eng, NOT view-set)
    try:
        nav("eng")
        pg.evaluate("localStorage.removeItem('rf_cfg::admin@gmail.com')")
        pg.fill("#skills",""); pg.click("#saveBtn"); pg.wait_for_timeout(400)
        ok("save blocked empty", pg.evaluate("!localStorage.getItem('rf_cfg::admin@gmail.com')"))
        pg.fill("#skills","python automation"); pg.fill("#target","startups"); pg.click("#saveBtn"); pg.wait_for_timeout(600)
        ok("save works", pg.evaluate("!!localStorage.getItem('rf_cfg::admin@gmail.com')"))
    except Exception as e: ok("save flow", False, str(e).split(chr(10))[0])
    # engine start/stop (already on view-eng)
    try:
        pg.click("#startBtn"); pg.wait_for_timeout(4000)
        ok("engine starts", "Running" in pg.locator("#engStat").inner_text() or pg.locator("#view-jobs").is_visible())
        pg.click("#stopBtn"); pg.wait_for_timeout(500)
        ok("engine stops", "Stopped" in pg.locator("#engStat").inner_text())
    except Exception as e: ok("engine flow", False, str(e).split(chr(10))[0])
    try:
        pg.click("#supBtn"); pg.fill("#supIn","how do I use it"); pg.click("#supSend"); pg.wait_for_timeout(700)
        ok("support bot replies", "Quick start" in pg.locator("#supMsgs").inner_text())
    except Exception as e: ok("support bot", False)
    try:
        nav("jobs"); nav("serv")
        pg.go_back(); pg.wait_for_timeout(600)
        ok("back button", pg.locator("#view-jobs").is_visible())
        pg.reload(); pg.wait_for_timeout(2000)
        ok("refresh keeps place", pg.locator("#view-jobs").is_visible())
    except Exception as e: ok("back/refresh", False)
    ctx.close()
    print("\n========== PART 4: API ENDPOINTS ==========")
    ctx=b.new_context(); pg=ctx.new_page()
    api="https://revenueforge-api.onrender.com"
    for ep in ["/health","/api/sub/admin@gmail.com"]:
        try:
            r=pg.request.get(api+ep, timeout=20000)
            ok("api "+ep, r.status==200, f"status={r.status}")
        except Exception as e:
            ok("api "+ep, False, str(e).split(chr(10))[0])
    ctx.close()
    b.close()
print("\n"+"="*50)
print("FINAL SCORE:", sum(1 for _,c in results if c), "passed /", len(results))
fails=[n for n,c in results if not c]
if fails:
    print("FAILED:", len(fails))
    for n in fails: print("  -", n)
else:
    print("EVERYTHING PASSES - READY TO ADVERTISE")
