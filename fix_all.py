import re
from pathlib import Path

# 1. Fix webapp.py (/api/chat endpoint)
p = Path('app/ui/webapp.py')
t = p.read_text()
if 'from fastapi import Request' not in t and 'from fastapi import' in t:
    t = t.replace('from fastapi import', 'from fastapi import Request,')
t = re.sub(r'@app\.post\("/api/chat"\).*?(?=\n@app\.|\nif __name__|\nuvicorn\.run|$)', '', t, flags=re.DOTALL)
new_chat = """

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
"""
if 'uvicorn.run' in t:
    t = t.replace('uvicorn.run', new_chat + '\nuvicorn.run')
else:
    t += new_chat
p.write_text(t)
print("✅ Fixed webapp.py")

# 2. Fix source count
p2 = Path('app/core/hiring_search.py')
t2 = p2.read_text()
t2 = re.sub(r'SOURCE_COUNT = \d+', 'SOURCE_COUNT = 105', t2)
if 'SOURCE_COUNT' not in t2:
    t2 += '\nSOURCE_COUNT = 105\n'
p2.write_text(t2)
print("✅ Fixed hiring_search.py")

# 3. Fix login redirect
p3 = Path('login.html')
t3 = p3.read_text()
if 'location.replace("signin.html"' not in t3:
    t3 = t3.replace('<head>', '<head>\n<script>location.replace("signin.html"+location.search);</script>')
    p3.write_text(t3)
    print("✅ Fixed login.html")
