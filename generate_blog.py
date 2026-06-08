import anthropic
import os
import re
import glob
import calendar
from datetime import datetime

topics = [
    # Core managed IT topics
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
    # City-specific topics
    "Managed IT services for Beverly Hills law firms and entertainment companies",
    "IT support for Century City high-rise offices and financial services firms",
    "Cybersecurity best practices for Pasadena technology and healthcare companies",
    "Managed IT services for Irvine biotech and technology companies",
    "IT support for El Segundo aerospace and defense contractors",
    "Managed IT services for Torrance manufacturing and automotive companies",
    "IT support for Orange County businesses expanding into Los Angeles",
    "How Burbank entertainment and media companies manage their IT infrastructure",
    "Cybersecurity for Santa Monica startups and creative agencies",
    "IT services for Glendale healthcare and professional services firms",
    # Industry-specific topics
    "IT compliance checklist for Los Angeles financial advisors and wealth managers",
    "How Los Angeles manufacturers are using cloud technology to modernize operations",
    "IT infrastructure planning for growing Los Angeles professional services firms",
    "Zero trust security for remote and hybrid teams in Los Angeles",
    "Why Los Angeles businesses are moving to co-managed IT in 2026",
    "Endpoint security best practices for Los Angeles businesses in 2026",
    "Business email compromise how to protect your Los Angeles company",
    "IT budgeting guide for Los Angeles small and mid-size businesses",
]

# Topic selection.
#   * Manual runs can force a topic via the TOPIC_INDEX workflow input (0-29).
#   * Scheduled runs auto-rotate. The job runs every other day, so advancing by
#     (day_of_year // 2) moves exactly one topic forward each run and cycles
#     through the whole list before any topic repeats.
topic_override = os.environ.get("TOPIC_INDEX", "")
if topic_override.isdigit():
    topic_index = int(topic_override) % len(topics)
else:
    # Auto-rotation for scheduled runs. The cron fires on odd days of the month,
    # so we count how many of those "post days" have occurred this year and
    # advance exactly one topic per post. This guarantees a different topic every
    # run -- even across month boundaries (where two posts can land on back-to-back
    # calendar days) -- and full coverage before any topic repeats.
    _now = datetime.now()
    _posts_before_month = sum(
        (calendar.monthrange(_now.year, _m)[1] + 1) // 2 for _m in range(1, _now.month)
    )
    _posts_this_month = (_now.day + 1) // 2
    _run_number = _posts_before_month + _posts_this_month  # 1-based
    topic_index = (_run_number - 1) % len(topics)

topic = topics[topic_index]
date_str = datetime.now().strftime("%B %d, %Y")
date_iso = datetime.now().strftime("%Y-%m-%d")
# Full date + topic index in the slug keeps every run's URL unique.
slug_date = datetime.now().strftime("%Y-%m-%d")
slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
slug = f"{slug_date}-t{topic_index}-{slug[:55]}"

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
- A compelling H1 title on its own line prefixed with TITLE: (keep it UNDER 42 characters so the full SEO title stays under 60 once " | Pro Link Systems" is appended)
- A meta description of 150-160 characters prefixed with META:
- A LinkedIn caption prefixed with LINKEDIN: for posting this article on the company page. Make it:
  * 3-5 short lines; the first line a strong hook that makes people want to read.
  * Professional but human. Plain text only - NO parentheses, brackets, markdown, or emojis.
  * Do NOT include the article URL (LinkedIn adds a link preview card automatically).
  * End with 3-5 relevant hashtags, for example: #ManagedIT #Cybersecurity #LosAngeles #ITSupport
  * Under 1200 characters total.

Format exactly like this:
TITLE: Your title here
META: Your meta description here
LINKEDIN:
Your LinkedIn caption here
(may span multiple lines, ending with hashtags)
CONTENT:
[HTML content here]"""

message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)

response = message.content[0].text
lines = response.strip().split('\n')
title = ""
meta = ""
caption_lines = []
content_lines = []
state = None  # None | "linkedin" | "content"

for line in lines:
    if line.startswith("TITLE:"):
        title = line.split("TITLE:", 1)[1].strip()
        state = None
    elif line.startswith("META:"):
        meta = line.split("META:", 1)[1].strip()
        state = None
    elif line.startswith("LINKEDIN:"):
        first = line.split("LINKEDIN:", 1)[1].strip()
        if first:
            caption_lines.append(first)
        state = "linkedin"
    elif line.startswith("CONTENT:"):
        state = "content"
    elif state == "content":
        content_lines.append(line)
    elif state == "linkedin":
        caption_lines.append(line)

caption = '\n'.join(caption_lines).strip()
content = '\n'.join(content_lines).strip()
year = datetime.now().year

NAV = '''<nav class="site-nav" role="navigation" aria-label="Main navigation">
  <a href="/" class="nav-logo" aria-label="Pro Link Systems home">
    <img src="/logo.png" alt="Pro Link Systems" width="160" height="44">
  </a>
  <div class="nav-links">
    <a href="/">Home</a>
    <a href="/services">Services</a>
    <a href="/about">About</a>
    <a href="/blog/" class="active">Blog</a>
    <a href="/contact">Contact</a>
    <a href="tel:18008906133" class="nav-cta">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.22 2.18 2 2 0 012.18 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.16 6.16l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
      1-800-890-6133
    </a>
  </div>
  <button class="nav-hamburger" aria-label="Toggle menu" onclick="document.getElementById('mobile-menu').classList.toggle('open')">
    <span></span><span></span><span></span>
  </button>
</nav>
<div class="mobile-menu" id="mobile-menu">
  <a href="/" onclick="document.getElementById('mobile-menu').classList.remove('open')">Home</a>
  <a href="/services" onclick="document.getElementById('mobile-menu').classList.remove('open')">Services</a>
  <a href="/about" onclick="document.getElementById('mobile-menu').classList.remove('open')">About</a>
  <a href="/blog/" onclick="document.getElementById('mobile-menu').classList.remove('open')">Blog</a>
  <a href="/contact" onclick="document.getElementById('mobile-menu').classList.remove('open')">Contact</a>
  <a href="tel:18008906133" style="color:var(--gold);font-weight:700;" onclick="document.getElementById('mobile-menu').classList.remove('open')">&#128222; 1-800-890-6133</a>
</div>'''

FOOTER = f'''<footer class="site-footer" role="contentinfo">
  <div class="footer-grid">
    <div class="footer-brand">
      <img src="/logo.png" alt="Pro Link Systems" width="140" height="38">
      <p>Managed IT and cybersecurity for Los Angeles businesses. Founded 1999. Trusted by hundreds of organizations across California.</p>
    </div>
    <div class="footer-col">
      <h4>Services</h4>
      <a href="/services#helpdesk">24/7 Help Desk</a>
      <a href="/services#cybersecurity">Cybersecurity</a>
      <a href="/services#cloud">Cloud &amp; Infrastructure</a>
      <a href="/services#dr">Disaster Recovery</a>
      <a href="/services#consulting">IT Consulting</a>
      <a href="/services#remote">Remote Workplace</a>
    </div>
    <div class="footer-col">
      <h4>Company</h4>
      <a href="/">Home</a>
      <a href="/about">About Us</a>
      <a href="/contact">Contact</a>
      <a href="/blog/">Blog</a>
      <a href="/legal">Legal / Terms</a>
    </div>
    <div class="footer-col">
      <h4>Contact</h4>
      <div class="footer-contact-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.22 2.18 2 2 0 012.18 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.16 6.16l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
        <div><a href="tel:18008906133">1-800-890-6133</a><br><span style="font-size:.8rem;color:rgba(255,255,255,.45);">Sales &amp; Support</span></div>
      </div>
      <div class="footer-contact-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        <a href="mailto:info@prolinksystems.com">info@prolinksystems.com</a>
      </div>
      <div class="footer-contact-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span>21241 Ventura Blvd<br>Woodland Hills, CA 91364</span>
      </div>
    </div>
  </div>
  <div class="footer-areas">
    <h4>Areas We Serve</h4>
    <div class="footer-areas-links">
      <a href="/managed-it-services-woodland-hills">Woodland Hills</a>
      <a href="/managed-it-services-beverly-hills">Beverly Hills</a>
      <a href="/managed-it-services-century-city">Century City</a>
      <a href="/managed-it-services-pasadena">Pasadena</a>
      <a href="/it-support-burbank">Burbank</a>
      <a href="/managed-it-services-santa-monica">Santa Monica</a>
      <a href="/managed-it-services-glendale">Glendale</a>
      <a href="/managed-it-services-calabasas">Calabasas</a>
      <a href="/managed-it-services-thousand-oaks">Thousand Oaks</a>
      <a href="/managed-it-services-sherman-oaks">Sherman Oaks</a>
      <a href="/managed-it-services-encino">Encino</a>
      <a href="/managed-it-services-torrance">Torrance</a>
      <a href="/managed-it-services-el-segundo">El Segundo</a>
      <a href="/managed-it-services-irvine">Irvine</a>
      <a href="/managed-it-services-orange-county">Orange County</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; {year} Pro Link Systems, Inc. All rights reserved.</span>
    <span>9AM&ndash;6PM PST &nbsp;|&nbsp; <a href="mailto:info@prolinksystems.com">info@prolinksystems.com</a></span>
  </div>
</footer>'''

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<title>{title} | Pro Link Systems</title>
<meta name="description" content="{meta}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://prolinksystems.com/blog/{slug}.html">
<meta property="og:type" content="article">
<meta property="og:url" content="https://prolinksystems.com/blog/{slug}.html">
<meta property="og:title" content="{title} | Pro Link Systems">
<meta property="og:description" content="{meta}">
<meta property="og:image" content="https://prolinksystems.com/logo.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://prolinksystems.com/logo.png">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{meta}",
  "datePublished": "{date_iso}",
  "dateModified": "{date_iso}",
  "author": {{
    "@type": "Organization",
    "name": "Pro Link Systems",
    "url": "https://prolinksystems.com"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "Pro Link Systems",
    "logo": {{
      "@type": "ImageObject",
      "url": "https://prolinksystems.com/logo.png"
    }}
  }},
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "https://prolinksystems.com/blog/{slug}.html"
  }}
}}
</script>
<link rel="stylesheet" href="/_shared.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-1068497497"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'AW-1068497497');
</script>
<style>
.blog-hero {{
  background: linear-gradient(135deg, var(--navy-dark) 0%, #0d4d85 100%);
  padding: 60px 0 48px;
  text-align: center;
}}
.blog-hero .breadcrumb {{
  font-size: .8rem;
  color: rgba(255,255,255,.5);
  margin-bottom: 16px;
}}
.blog-hero .breadcrumb a {{
  color: rgba(255,255,255,.5);
  text-decoration: none;
}}
.blog-hero .breadcrumb a:hover {{ color: var(--gold); }}
.blog-hero .breadcrumb span {{ margin: 0 8px; }}
.blog-hero h1 {{
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  font-weight: 800;
  color: #fff;
  line-height: 1.25;
  letter-spacing: -.025em;
  max-width: 800px;
  margin: 0 auto 16px;
  padding: 0 24px;
}}
.blog-hero .post-meta {{
  font-size: .85rem;
  color: rgba(255,255,255,.55);
}}
.blog-hero .post-meta strong {{
  color: var(--gold);
  font-weight: 600;
}}
.blog-body {{
  max-width: 780px;
  margin: 0 auto;
  padding: 52px 24px 64px;
}}
.blog-body h2 {{
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--navy);
  margin: 2.5rem 0 1rem;
  letter-spacing: -.02em;
}}
.blog-body p {{
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text);
  margin-bottom: 1.25rem;
}}
.blog-body ul {{
  margin: 0 0 1.25rem 1.5rem;
  padding: 0;
}}
.blog-body li {{
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text);
  margin-bottom: .5rem;
}}
.blog-body strong {{ font-weight: 700; color: var(--navy); }}
.blog-cta-box {{
  background: linear-gradient(135deg, #f0f6ff 0%, #e8f0ff 100%);
  border: 1.5px solid rgba(23,98,168,.15);
  border-left: 4px solid var(--navy);
  border-radius: var(--r-lg);
  padding: 2rem 2rem 2rem 2.25rem;
  margin: 3rem 0 0;
}}
.blog-cta-box h2 {{
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--navy);
  margin: 0 0 .75rem;
  letter-spacing: -.02em;
}}
.blog-cta-box p {{
  font-size: .95rem;
  color: var(--text-muted);
  margin-bottom: 1.25rem;
  line-height: 1.65;
}}
.blog-cta-box .btn-group {{
  display: flex; gap: 12px; flex-wrap: wrap;
}}
</style>
</head>
<body>
{NAV}

<div class="blog-hero">
  <div class="breadcrumb">
    <a href="/">Home</a><span>/</span>
    <a href="/blog/">Blog</a><span>/</span>
    <span style="color:rgba(255,255,255,.7);">Article</span>
  </div>
  <h1>{title}</h1>
  <div class="post-meta">
    <strong>Pro Link Systems</strong> &nbsp;&middot;&nbsp; {date_str}
  </div>
</div>

<article class="blog-body">
{content}

<div class="blog-cta-box">
  <h2>Ready to talk to a real IT engineer?</h2>
  <p>Pro Link Systems has been protecting and managing IT for Los Angeles businesses since 1999. Book a free 15-minute discovery call &mdash; no pressure, no obligation, no scripts.</p>
  <div class="btn-group">
    <a href="/managed-it-services" class="btn btn-navy">Book a Free Discovery Call</a>
    <a href="tel:18008906133" class="btn btn-outline-navy">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.22 2.18 2 2 0 012.18 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.16 6.16l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
      1-800-890-6133
    </a>
  </div>
</div>
</article>

{FOOTER}
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
    t_match = re.search(r'<h1[^>]*>(.*?)</h1>', c, re.DOTALL)
    d_match = re.search(r'class="post-meta"[^>]*>.*?<\/strong>\s*&nbsp;&middot;&nbsp;\s*([^<]+)', c, re.DOTALL)
    t = t_match.group(1).strip() if t_match else s
    d = d_match.group(1).strip() if d_match else ""
    posts.append((s, t, d))

post_cards = ""
for s, t, d in posts:
    post_cards += f"""
<article class="blog-card">
  <div class="blog-card-meta">{d}</div>
  <h2 class="blog-card-title"><a href="/blog/{s}.html">{t}</a></h2>
  <a href="/blog/{s}.html" class="blog-card-link">Read article
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
  </a>
</article>"""

index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<title>IT Blog &amp; Insights for Los Angeles Businesses | Pro Link Systems</title>
<meta name="description" content="Expert IT advice, cybersecurity tips, and managed IT insights for Los Angeles businesses from Pro Link Systems &mdash; serving LA since 1999.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://prolinksystems.com/blog/">
<link rel="stylesheet" href="/_shared.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-1068497497"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'AW-1068497497');
</script>
<style>
.blog-index-hero {{
  background: linear-gradient(135deg, var(--navy-dark) 0%, #0d4d85 100%);
  padding: 64px 0 52px;
  text-align: center;
}}
.blog-index-hero h1 {{
  font-size: clamp(1.8rem, 3.5vw, 2.8rem);
  font-weight: 800;
  color: #fff;
  letter-spacing: -.03em;
  margin: 0 0 12px;
}}
.blog-index-hero p {{
  font-size: 1rem;
  color: rgba(255,255,255,.65);
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.6;
}}
.blog-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 52px 24px 72px;
}}
.blog-card {{
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1.75rem;
  box-shadow: var(--sh-sm);
  transition: box-shadow .2s, transform .2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}}
.blog-card:hover {{
  box-shadow: var(--sh-md);
  transform: translateY(-2px);
}}
.blog-card-meta {{
  font-size: .8rem;
  color: var(--text-muted);
  font-weight: 500;
}}
.blog-card-title {{
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.4;
  margin: 0;
  flex: 1;
}}
.blog-card-title a {{
  color: var(--navy);
  text-decoration: none;
  transition: color .2s;
}}
.blog-card-title a:hover {{ color: var(--navy-light); }}
.blog-card-link {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: .85rem;
  font-weight: 600;
  color: var(--navy-light);
  text-decoration: none;
  transition: gap .2s;
}}
.blog-card-link:hover {{ gap: 10px; }}
</style>
</head>
<body>
{NAV}

<div class="blog-index-hero">
  <div class="container">
    <h1>IT Insights for Los Angeles Businesses</h1>
    <p>Expert advice on managed IT, cybersecurity, and technology strategy from Pro Link Systems &mdash; serving LA since 1999.</p>
  </div>
</div>

<div class="blog-intro" style="max-width:820px;margin:0 auto;padding:44px 24px 4px;">
  <p style="font-size:1rem;color:var(--text-muted);line-height:1.8;margin-bottom:16px;">Welcome to the Pro Link Systems blog &mdash; straightforward technology guidance for Los Angeles businesses. For more than 25 years we've helped LA-area organizations across healthcare, legal, finance, manufacturing, and dozens of other industries get more from their technology while staying secure and compliant. These articles share what we've learned along the way.</p>
  <p style="font-size:1rem;color:var(--text-muted);line-height:1.8;margin:0;">Here you'll find practical answers to the questions business owners actually ask: how to choose a managed IT provider, what managed IT really costs, how to defend against the cybersecurity threats targeting Southern California, when it makes sense to move to the cloud, and how to tell when you've outgrown your current IT support. Browse the latest articles below, or call us at <a href="tel:18008906133" style="color:var(--navy);font-weight:600;">1-800-890-6133</a> to talk through your situation with a real engineer.</p>
</div>

<div class="blog-grid">
{post_cards}
</div>

{FOOTER}
</body>
</html>"""

with open("blog/index.html", 'w') as f:
    f.write(index_html)

print(f"Blog index updated with {len(posts)} posts")

# --- Cross-post to the company LinkedIn page -------------------------------
# Safe by design: maybe_post() never raises, so a LinkedIn problem (expired
# token, outage, missing secrets) can never block the blog from publishing.
try:
    import linkedin_post

    post_url = f"https://prolinksystems.com/blog/{slug}.html"
    if not caption:
        caption = (
            f"{title}\n\n"
            f"New on the Pro Link Systems blog: {meta}\n\n"
            "#ManagedIT #Cybersecurity #LosAngeles #ITSupport"
        )
    linkedin_post.maybe_post(
        title=title, url=post_url, summary=meta, caption=caption
    )
except Exception as e:
    print(f"[linkedin] WARNING: cross-post step skipped: {e}")
