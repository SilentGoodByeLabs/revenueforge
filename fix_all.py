from pathlib import Path
import json, hashlib

# 1. Fix webapp.py - revert broken changes and fix syntax
p = Path('app/ui/webapp.py')
w = p.read_text()

# Remove any broken host check that caused issues
w = w.replace('''    # Block if not from localhost/private console
    host = request.headers.get("host", "")
    if "localhost" not in host and "127.0.0.1" not in host:
        return JSONResponse({"error": "Not authorized"}, status_code=403)
''', '')

try:
    compile(w, 'webapp.py', 'exec')
    p.write_text(w)
    print("✓ webapp.py syntax fixed")
except SyntaxError as e:
    print(f"✗ Still broken at line {e.lineno}: {e.text}")
    exit(1)

# 2. Make admin@gmail.com a Pro user
users_file = Path('data/users.json')
users = {}
if users_file.exists():
    users = json.load(open(users_file))

# Add/update admin as Pro
admin_email = 'admin@gmail.com'
admin_pw = 'admin123'
users[admin_email] = {
    'name': 'Admin',
    'pw': hashlib.sha256(admin_pw.encode()).hexdigest(),
    'created': '2026-01-01',
    'plan': 'pro',  # Pro plan
    'trial_end': '2099-12-31'  # Never expires
}
users_file.parent.mkdir(exist_ok=True)
json.dump(users, open(users_file, 'w'), indent=2)
print(f"✓ admin@gmail.com created as Pro user (password: admin123)")

# 3. Fix homepage mobile layout
w2 = Path('app/ui/webapp.py').read_text()
if '.mbtn{display:none}' in w2:
    # Add compact mobile styles
    w2 = w2.replace(
        '.mbtn{display:none;background:none;border:0;color:#fff;font-size:26px;cursor:pointer;padding:4px 8px}',
        '.mbtn{display:none;background:none;border:0;color:#fff;font-size:26px;cursor:pointer;padding:4px 8px}@media(max-width:768px){nav{flex-wrap:wrap;height:auto!important;padding:12px 4%!important}.logo{font-size:20px!important}nav .links{display:none!important}.mbtn{display:block!important}#mmenu{display:none;background:#1e293b;border-top:1px solid #334155;padding:8px 6%;width:100%}#mmenu a{display:block;padding:13px 4px;color:#e2e8f0;text-decoration:none;border-bottom:1px solid #334155}}'
    )
    Path('app/ui/webapp.py').write_text(w2)
    print("✓ Homepage mobile layout fixed")

print("✓ All fixes applied")
