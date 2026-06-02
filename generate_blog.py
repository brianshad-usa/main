import anthropic
import os
import re
import glob
from datetime import datetime

topics = [
    "Why Los Angeles businesses are switching from break-fix IT to managed services in 2026",
    "HIPAA compliance checklist for Los Angeles medical practices",
    "How much does managed IT support cost for small businesses in Los Angeles",
    "Cybersecurity threats targeting Southern California businesses in 2026",
    "Microsoft 365 vs Google Workspace which is better for LA businesses",
    "Signs your Los Angeles business has outgrown your current IT provider",
    "How to choose a managed IT provider in Los Angeles",
    "IT disaster recovery planning for Los Angeles businesses",
    "Cloud migration guide for small businesses in Southern California",
    "What is a virtual CIO and does your LA business need one",
    "Ransomware protection for Los Angeles law firms",
    "IT support for healthcare clinics in Los Angeles",
]

month_index = datetime.now().month - 1
topic = topics[month_index % len(topics)]
date_str = datetime.now().strftime("%B %d, %Y")
slug_date = datetime.now().strftime("%Y-%m")
slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
slug = f"{slug_date}-{slug[:60]}"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

prompt = f"""Write a professional SEO-optimized blog post for Pro Link Systems, a managed IT services company based in Woodland Hills, Los Angeles, CA since 1999.

Topic: {topic}

Requirements:
- Length: 800-1000 words
- Tone: Professional but approachable
- Include naturally: managed IT services Los Angeles, IT support Los Angeles, Pro Link Systems
- Structure: Introduction, 3-4 main sections with H2 headings, conclusion with CTA
- CTA at end should direct readers to prolinksystems.com/managed-it-services
- Write in HTML using only these tags: p, h2, ul, li, strong
- Do not include DOCTYPE html head body tags
- No markdown, just clean HTML

Also provide:
- A compelling H1 title on its own line prefixed with TITLE:
- A meta description 150-160 characters prefixed with META:

Format exactly like this:
TITLE: Your title here
META: Your meta description here
CONTENT:
[HTML content here]"""

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)

response = message.content[0].text
lines = response.strip().split('\n')
title = ""
meta = ""
content_lines = []
in_content = False

for line in lines:
    if line.startswith("TITLE: "):
        title = line.replace("TITLE: ", "").strip()
    elif line.startswith("META: "):
        meta = line.replace("META: ", "").strip()
    elif line.startswith("CONTENT:"):
        in_content = True
    elif in_content:
        content_lines.append(line)

content = '\n'.join(content_lines).strip()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Pro Link Systems</title>
<meta name="description" content="{meta}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://prolinksystems.com/blog/{slug}.html">
<link rel="stylesheet" href="/_shared.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-1068497497"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'AW-1068497497');
</script>
</head>
<body>
<header style="background:#0a1628;padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;">
<a href="/"><img src="/logo.png" alt="Pro Link Systems" style="height:40px;"></a>
<nav style="display:flex;gap:2rem;">
<a href="/" style="color:#fff;text-decoration:none;">Home</a>
<a href="/services.html" style="color:#fff;text-decoration:none;">Services</a>
<a href="/about.html" style="color:#fff;text-decoration:none;">About</a>
<a href="/blog/" style="color:#fff;text-decoration:none;">Blog</a>
<a href="/contact.html" style="color:#fff;text-decoration:none;">Contact</a>
</nav>
</header>
<main style="max-width:800px;margin:3rem auto;padding:0 2rem;">
<p style="color:#666;font-size:0.9rem;margin-bottom:0.5rem;">{date_str} - Pro Link Systems</p>
<h1 style="font-size:2rem;font-weight:700;color:#0a1628;margin-bottom:2rem;line-height:1.3;">{title}</h1>
<div style="font-size:1.05rem;line-height:1.8;color:#333;">
{content}
</div>
<div style="background:#f0f4ff;border-left:4px solid #2563eb;padding:2rem;margin:3rem 0;border-radius:0 8px 8px 0;">
<h2 style="color:#0a1628;margin-top:0;">Ready to talk to a real IT engineer?</h2>
<p>Pro Link Systems has been serving Los Angeles businesses since 1999. Book a free 15-minute discovery call.</p>
<a href="/managed-it-services" style="background:#2563eb;color:#fff;padding:0.75rem 1.5rem;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Book a Free Discovery Call</a>
</div>
</main>
<footer style="background:#0a1628;color:#fff;padding:2rem;text-align:center;margin-top:4rem;">
<p style="margin:0;">2026 Pro Link Systems - 21241 Ventura Blvd Suite 193, Woodland Hills, CA 91364 - 1-800-890-6133</p>
</footer>
</body>
</html>"""

os.makedirs("blog", exist_ok=True)
filepath = f"blog/{slug}.html"
with open(filepath, 'w') as f:
    f.write(html)

print(f"Generated: {filepath}")
print(f"Title: {title}")

# Update blog index
posts = []
for fp in sorted(glob.glob("blog/*.html"), reverse=True):
    fname = os.path.basename(fp)
    if fname == "index.html":
        continue
    s = fname.replace(".html", "")
    with open(fp, 'r') as f:
        c = f.read()
    t_match = re.search(r'<h1[^>]*>(.*?)</h1>', c)
    d_match = re.search(r'<p[^>]*>(\w+ \d+, \d{4})', c)
    t = t_match.group(1) if t_match else s
    d = d_match.group(1) if d_match else ""
    posts.append((s, t, d))

post_cards = ""
for s, t, d in posts[:12]:
    post_cards += f"""
<article style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:1.5rem;">
<p style="color:#666;font-size:0.85rem;margin:0 0 0.5rem;">{d}</p>
<h2 style="font-size:1.1rem;margin:0 0 1rem;"><a href="/blog/{s}.html" style="color:#0a1628;text-decoration:none;">{t}</a></h2>
<a href="/blog/{s}.html" style="color:#2563eb;font-size:0.9rem;font-weight:500;">Read article</a>
</article>"""

index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IT Blog and Insights for Los Angeles Businesses | Pro Link Systems</title>
<meta name="description" content="Expert IT advice, cybersecurity tips, and managed IT insights for Los Angeles businesses from Pro Link Systems since 1999.">
<link rel="canonical" href="https://prolinksystems.com/blog/">
<link rel="stylesheet" href="/_shared.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-1068497497"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'AW-1068497497');
</script>
</head>
<body>
<header style="background:#0a1628;padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;">
<a href="/"><img src="/logo.png" alt="Pro Link Systems" style="height:40px;"></a>
<nav style="display:flex;gap:2rem;">
<a href="/" style="color:#fff;text-decoration:none;">Home</a>
<a href="/services.html" style="color:#fff;text-decoration:none;">Services</a>
<a href="/about.html" style="color:#fff;text-decoration:none;">About</a>
<a href="/blog/" style="color:#e2a818;text-decoration:none;font-weight:600;">Blog</a>
<a href="/contact.html" style="color:#fff;text-decoration:none;">Contact</a>
</nav>
</header>
<main style="max-width:900px;margin:3rem auto;padding:0 2rem;">
<h1 style="font-size:2rem;font-weight:700;color:#0a1628;margin-bottom:0.5rem;">IT Insights for Los Angeles Businesses</h1>
<p style="color:#666;margin-bottom:3rem;">Expert advice on managed IT, cybersecurity, and technology strategy from Pro Link Systems since 1999.</p>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem;">
{post_cards}
</div>
</main>
<footer style="background:#0a1628;color:#fff;padding:2rem;text-align:center;margin-top:4rem;">
<p style="margin:0;">2026 Pro Link Systems - 21241 Ventura Blvd Suite 193, Woodland Hills, CA 91364 - 1-800-890-6133</p>
</footer>
</body>
</html>"""

with open("blog/index.html", 'w') as f:
    f.write(index_html)

print(f"Blog index updated with {len(posts)} posts")
