import re, os, shutil

# --- 1) Newest-first sort key (mirrors generate_blog.py) ---
def post_date_key(path):
    fn = os.path.basename(path)
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})-', fn)
    if m: return (int(m.group(1)), int(m.group(2)), int(m.group(3)), fn)
    m = re.match(r'(\d{4})-(\d{2})-', fn)
    if m: return (int(m.group(1)), int(m.group(2)), 0, fn)
    return (0, 0, 0, fn)

files = [
    "blog/2026-06-t0-why.html",          # old undated June
    "blog/2026-06-t9-vcio.html",         # old undated June
    "blog/2026-06-09-t12-new.html",      # new dated Jun 9
    "blog/2026-06-11-t13-newer.html",    # new dated Jun 11
    "blog/2026-07-01-t20-july.html",     # July
]
order = [os.path.basename(p) for p in sorted(files, key=post_date_key, reverse=True)]
print("Newest-first:", order)
assert order[0].startswith("2026-07-01")     # July on top
assert order[1].startswith("2026-06-11")     # then newest June dated
assert order[2].startswith("2026-06-09")
assert order[3].startswith("2026-06-t") and order[4].startswith("2026-06-t")  # undated last
print("DATE_SORT_OK")

# --- 2) Home-page marker replacement against the real index.html ---
shutil.copy("index.html", "_tmp_index.html")
home = open("_tmp_index.html", encoding="utf-8").read()
assert "<!-- HOME_BLOG_START -->" in home and "<!-- HOME_BLOG_END -->" in home, "markers missing!"
before = home.split("<!-- HOME_BLOG_START -->")[0]
after = home.split("<!-- HOME_BLOG_END -->")[1]

fake = [
    ("2026-06-11-t13-newer", "Newer Post Title", "June 11, 2026"),
    ("2026-06-09-t12-new", "New Post Title", "June 09, 2026"),
    ("2026-06-t9-vcio", "Older VCIO Post", "June 2026"),
]

def render(posts):
    arrow = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>')
    cards = ""
    for s, t, d in posts[:8]:
        cards += (f'      <a class="home-blog-card" href="/blog/{s}.html">\n'
                  f'        <div class="hb-meta">{d}</div>\n'
                  f'        <h3>{t}</h3>\n'
                  f'        <span class="hb-read">Read article {arrow}</span>\n'
                  f'      </a>\n')
    return "<!-- HOME_BLOG_START -->\n" + cards + "      <!-- HOME_BLOG_END -->"

def apply(text, posts):
    nb = render(posts)
    return re.sub(r"<!-- HOME_BLOG_START -->.*?<!-- HOME_BLOG_END -->", lambda _m: nb, text, flags=re.DOTALL)

out1 = apply(home, fake)
out2 = apply(out1, fake)
os.remove("_tmp_index.html")

assert out1.split("<!-- HOME_BLOG_START -->")[0] == before, "content before markers changed!"
assert out1.split("<!-- HOME_BLOG_END -->")[1] == after, "content after markers changed!"
assert out1.count('class="home-blog-card"') == 3, "wrong card count"
assert "Newer Post Title" in out1 and "/blog/2026-06-11-t13-newer.html" in out1
assert "What Is a Virtual CIO" not in out1, "old hardcoded card not replaced"
assert out1 == out2, "not idempotent"
assert out1.count("<!-- HOME_BLOG_START -->") == 1 and out1.count("<!-- HOME_BLOG_END -->") == 1
print("HOME_REPLACE_OK (cards swapped, markers intact, rest of page untouched, idempotent)")
print("ALL_OK")
