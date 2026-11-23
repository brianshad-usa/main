#!/usr/bin/env python3
"""
chrome/insights.py -- the one renderer for Insights (redesign-2026, iteration 3).

Everything an Insights page shows comes from editorial/blog_registry.json (categories, practices, authors, the
featured selection and per-article metadata) plus the article body itself. The same functions render:
  * every article page, blog/<slug>.html: the migration of existing posts AND each new post from generate_blog.py;
  * the Insights index, blog/index.html: a featured article and curated picks (chosen in the registry, not by
    date), the latest list with topic filter, keyword search and load-more (assets/js/insights.js), and a
    plain-link archive by topic that works without JavaScript;
  * the home page cards between the HOME_BLOG markers in index.html (never more than four);
  * profile pages, leadership/<author>.html, for Person authors that have a "profile".

    python chrome/insights.py --rebuild      # re-render every article, the index, home cards and profiles
    python chrome/insights.py --check        # validate the registry and its assets; exit 1 on any problem

Rules enforced here (Brian, 2026-11-21):
  - An article is attributed to a person who "requires_approval" (Brian Shad) only when its registry entry
    records that approval (approved_by). Otherwise it is published under the organization.
  - On existing posts the <title>, meta description, robots, canonical, Open Graph/Twitter tags, tracking scripts,
    dates and every JSON-LD block are kept, except the BlogPosting author node and the breadcrumb label
    ("Blog" -> "Insights"). The article body between <!-- PL:BODY --> markers is never rewritten, only given
    heading ids for the table of contents.
  - Filters and search never create URLs (hash only); the archive is plain links; there are no tag or category
    pages (/category/* and /author/* already 301 to /blog/).
Pages are written with the shared header/footer (chrome/header.html + footer.html via apply_chrome), so new
posts are born in the current design without a separate chrome step.
"""
import html
import io
import json
import math
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import apply_chrome  # noqa: E402
import insight_art   # noqa: E402

SITE = "https://prolinksystems.com"
REGISTRY = os.path.join(ROOT, "editorial", "blog_registry.json")
ART_DIR = "assets/insights"
JS_VERSION = "20261122"
PAGE_SIZE = 9             # cards shown before "Show more articles"
LATEST_MAX = 24           # cards available in the Latest section (the Library lists every article)
WORDS_PER_MINUTE = 230
TOC_MIN_SECTIONS = 4      # a table of contents appears when an article has at least this many H2 sections
HOME_CARDS = 4            # Brian: the home page features no more than four articles
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

E = lambda s: html.escape(s or "", quote=False)
A = lambda s: html.escape(s or "", quote=True)

TRACKING = """<script async src="https://www.googletagmanager.com/gtag/js?id=AW-1068497497"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'AW-1068497497');
gtag('config', 'G-SYTKYHZHWJ'); // GA4 — property 507517385
</script>
<!-- Microsoft UET tag (Bing Ads) — tag 97275167 -->
<script>
    (function(w, d, t, u, o) {
        w[u] = w[u] || [], o.ts = (new Date).getTime();
        var n = d.createElement(t);
        n.src = "https://bat.bing.net/bat.js?ti=" + o.ti + ("uetq" != u ? "&q=" + u : "");
        n.async = 1, n.onload = n.onreadystatechange = function() {
            var s = this.readyState;
            s && "loaded" !== s && "complete" !== s ||
            (o.q = w[u], w[u] = new UET(o), w[u].push("pageLoad"),
            n.onload = n.onreadystatechange = null)
    };
        var i = d.getElementsByTagName(t)[0];
        i.parentNode.insertBefore(n, i);
    })(window, document, "script", "uetq", {
        ti:"97275167",
        enableAutoSpaTracking: true
    });
</script>
"""
ICONS = ('<link rel="icon" type="image/x-icon" href="/favicon.ico">\n'
         '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">\n'
         '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">\n')


# ---------------------------------------------------------------------------------------------------------------
# registry + files

def load():
    with io.open(REGISTRY, encoding="utf-8") as fh:
        return json.load(fh)


def save(reg):
    reg["posts"] = dict(sorted(reg["posts"].items(), key=lambda kv: (kv[1].get("date_published", ""), kv[0]),
                               reverse=True))
    with io.open(REGISTRY, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")


def read(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return fh.read().decode("utf-8")


def write(rel, text):
    """Write only when the content changes; keep CRLF if the existing file uses it. Returns True on change."""
    path = os.path.join(ROOT, rel)
    old = read(rel) if os.path.exists(path) else None
    if old is not None and "\r\n" in old and "\r\n" not in text:
        text = text.replace("\n", "\r\n")
    if text == old:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))
    return True


def css_version():
    """The site-wide ?v= of _shared.css, taken from the home page so this module never carries its own copy."""
    m = re.search(r'_shared\.css\?v=([^"]+)"', read("index.html"))
    return m.group(1) if m else "1"


def chrome(text, rel):
    """Apply the shared header/footer, font preloads and pl.js exactly as chrome/apply_chrome.py does."""
    return apply_chrome.process_text(text, rel)


# ---------------------------------------------------------------------------------------------------------------
# lookups + small formatters

def category(reg, key):
    for c in reg["categories"]:
        if key in (c["name"], c["slug"]):
            return c
    for c in reg["categories"]:
        if c["slug"] == reg.get("default_category", "technology-leadership"):
            return c
    return reg["categories"][0]


def author_for(reg, p):
    key = p.get("author") or reg["default_author"]
    a = reg["authors"].get(key)
    if a is None or (a.get("requires_approval") and not p.get("approved_by")):
        key = reg["default_author"]
        a = reg["authors"][key]
    return key, a


def listed(reg):
    """Indexable posts, newest first (noindexed duplicates are never listed)."""
    items = [(s, p) for s, p in reg["posts"].items() if not p.get("noindex")]
    return sorted(items, key=lambda kv: (kv[1]["date_published"], kv[0]), reverse=True)


def long_date(iso):
    d = date.fromisoformat(iso[:10])
    return "%s %d, %d" % (MONTHS[d.month - 1], d.day, d.year)


def minutes(p):
    return max(2, int(math.ceil((p.get("words") or 900) / float(WORDS_PER_MINUTE))))


def word_count(body):
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", text))


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment or ""))).strip()


# Fallback classification for a new post when the model's CATEGORY line is missing or invalid. First match wins.
CATEGORY_RULES = [
    ("Industry Perspectives", r"\b(?:dental|law firms?|legal|accounting|cpa|property management|construction|insurance agenc|"
                              r"restaurants?|hospitality|architecture|engineering firms?|biotech|life sciences|veterinary|"
                              r"manufactur|healthcare|medical|clinics?|aerospace|defense contractors?|entertainment|media companies|"
                              r"agencies|schools?|nonprofits?|startups?)\b"),
    ("Artificial Intelligence & Automation", r"\b(?:ai|artificial intelligence|copilot|chatgpt|automat\w*|machine learning|"
                                             r"llm|deepfakes?|voice cloning|note-takers?)\b"),
    ("Business Continuity", r"\b(?:backups?|disaster|recovery|continuity|outages?|downtime|immutable|break-glass|shutoffs?)\b"),
    ("Governance & Compliance", r"\b(?:polic(?:y|ies)|governance|compliance|audits?|retention|vendor risk|supply-chain|"
                                r"insurance|access reviews?|frameworks?|nist|board)\b"),
    ("Cybersecurity & Risk", r"\b(?:security|cyber\w*|ransomware|phishing|mfa|passkeys?|passwordless|identity|passwords?|"
                             r"threats?|attacks?|breach\w*|malware|endpoints?|email|tokens?|oauth|edge devices?|firewalls?|"
                             r"vpns?|soc|mdr|zero trust|social engineering|insider)\b"),
    ("Cloud & Infrastructure", r"\b(?:cloud|microsoft 365|m365|sharepoint|onedrive|azure|aws|hybrid|networks?|infrastructure|"
                               r"windows|servers?|saas)\b"),
]
LOCAL_RX = re.compile(r"\b(?:los angeles|la|l\.a\.|socal|southern california|orange county|beverly hills|century city|"
                      r"pasadena|irvine|el segundo|torrance|burbank|santa monica|glendale|woodland hills|"
                      r"san fernando valley|ventura|long beach|calabasas|thousand oaks)\b", re.I)


def guess_category(text):
    t = (text or "").lower()
    for name, rx in CATEGORY_RULES:
        if re.search(rx, t):
            return name
    return "Technology Leadership"


def is_local(title):
    """A post reads as local when its headline names a place; local posts stay listed but are not featured."""
    return bool(LOCAL_RX.search(title or ""))


def art_rel(slug):
    return "%s/%s.svg" % (ART_DIR, slug)


def ensure_art(reg, slug):
    """(Re)generate the article's illustration; deterministic, so unchanged art is not rewritten."""
    p = reg["posts"][slug]
    cat = category(reg, p["category"])
    write(art_rel(slug), insight_art.art_svg(slug, cat["name"], cat["alt"]) + "\n")
    p["illustration"] = "/" + art_rel(slug)


def art_img(reg, slug, eager=False):
    """The article's illustration. Its alt text describes the drawing (chrome/art_scenes) when the article has its own."""
    cat = category(reg, reg["posts"][slug]["category"])
    load_attr = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return ('<img class="pl-art-img" src="/%s" width="1200" height="675" alt="%s" %s decoding="async">'
            % (art_rel(slug), A(insight_art.scene_alt(slug) or cat["alt"]), load_attr))


def dek(p):
    """The standfirst shown on the page (editorial `dek` when set, else the meta description)."""
    return p.get("dek") or p["summary"]


def time_tag(iso):
    return '<time datetime="%s">%s</time>' % (iso[:10], long_date(iso))


# ---------------------------------------------------------------------------------------------------------------
# shared blocks

def cta_band(reg, cat=None, override=None):
    c = reg["cta"]
    o = override or {}
    button = o.get("button") or (cat or {}).get("cta") or c["button"]
    href = o.get("href") or c["href"]
    sec = o.get("secondary")
    sec_html = ('<a href="%s" class="btn btn-outline-white">%s</a>' % (A(sec["href"]), E(sec["label"])) if sec else
                '<a href="tel:%s" class="btn btn-outline-white">%s</a>' % (re.sub(r"\D", "", c["phone"]), E(c["phone"])))
    return ('<section class="pl-cta" aria-labelledby="cta-heading">\n  <div class="pl-wrap">\n    <div>\n'
            '      <p class="pl-eyebrow">%s</p>\n      <h2 class="pl-h2" id="cta-heading">%s</h2>\n    </div>\n'
            '    <div>\n      <p>%s</p>\n      <div class="pl-actions">\n        <a href="%s" class="btn btn-light">%s</a>\n'
            '        %s\n      </div>\n    </div>\n  </div>\n</section>'
            % (E(c["eyebrow"]), E(c["heading"]), E(c["text"]), A(href), E(button), sec_html))


def card(reg, slug, level="h3"):
    p = reg["posts"][slug]
    cat = category(reg, p["category"])
    topic = re.sub(r"^\d{4}-\d{2}(?:-\d{2})?-(?:t\d+-)?", "", slug).replace("-", " ")   # the original topic wording
    text = " ".join([p["title"], dek(p), cat["name"], topic]).lower()
    return ('<li class="pl-icard" data-cat="%s" data-text="%s"><a href="/blog/%s">%s<span class="pl-cat">%s</span>'
            '<%s>%s</%s><p>%s</p><span class="pl-meta">%s<span>%d min read</span></span></a></li>'
            % (cat["slug"], A(text), slug, art_img(reg, slug), E(cat["name"]), level, E(p["title"]), level,
               E(dek(p)), time_tag(p["date_published"]), minutes(p)))


# ---------------------------------------------------------------------------------------------------------------
# article page

RE_H2 = re.compile(r"<h2(\s[^>]*)?>(.*?)</h2>", re.S | re.I)


def add_heading_ids(body):
    seen = set(re.findall(r'\bid="([^"]+)"', body))
    heads = []

    def fix(m):
        attrs, inner = m.group(1) or "", m.group(2)
        text = plain(inner)
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if idm:
            hid = idm.group(1)
        else:
            base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:56].strip("-") or "section"
            hid, n = base, 2
            while hid in seen:
                hid, n = "%s-%d" % (base, n), n + 1
            seen.add(hid)
            attrs = ' id="%s"%s' % (hid, attrs)
        if "pl-refs-h" not in attrs:
            heads.append((hid, text))
        return "<h2%s>%s</h2>" % (attrs, inner)

    return RE_H2.sub(fix, body), heads


def related(reg, slug, n=3):
    p = reg["posts"][slug]
    pool = [s for s, q in listed(reg) if s != slug]
    same = [s for s in pool if reg["posts"][s]["category"] == p["category"]]
    ranked = ([s for s in p.get("related", []) if s in reg["posts"]] +
              [s for s in same if not reg["posts"][s].get("local")] + [s for s in same if reg["posts"][s].get("local")] +
              [s for s in pool if reg["posts"][s].get("executive")])
    out = []
    for s in ranked:
        if s not in out and not reg["posts"][s].get("noindex"):
            out.append(s)
        if len(out) == n:
            break
    return out


def byline(reg, p, a):
    if a["type"] == "Person":
        img = '<img src="%s" width="52" height="52" alt="%s" decoding="async">' % (A(a["photo"]), A(a["name"]))
        who = '<a href="%s"><strong>%s</strong></a>%s' % (A(a["profile"]), E(a["name"]), E(a["title"]))
    else:
        img = ('<img class="is-org" src="%s" width="52" height="52" alt="%s" decoding="async">'
               % (A(a["photo"]), A(a["name"] + " logo")))
        who = "<strong>%s</strong>%s" % (E(a["name"]), E(a.get("byline_line", "")))
    meta = time_tag(p["date_published"])
    if p.get("date_modified", "")[:10] > p["date_published"][:10]:
        meta += " &middot; Updated " + time_tag(p["date_modified"])
    meta += "<br>%d min read" % minutes(p)
    revs = [reg["authors"][r] for r in p.get("reviewers", []) if r in reg["authors"]]
    rev = ""
    if revs:
        rev = '<p class="pl-reviewed">Reviewed by %s</p>' % ", ".join(
            "%s, %s" % (E(r["name"]), E(r.get("title", ""))) if r.get("title") else E(r["name"]) for r in revs)
    return ('<div class="pl-byline">%s<div class="pl-byline-who">%s</div><div class="pl-byline-meta">%s</div></div>%s'
            % (img, who, meta, rev))


def author_box(a):
    if a["type"] == "Person":
        return ('<section class="pl-author" aria-labelledby="author-h"><img src="%s" width="96" height="96" alt="%s" '
                'loading="lazy" decoding="async"><div><p class="pl-author-k">About the author</p><h2 id="author-h">%s</h2>'
                '<p class="pl-author-title">%s</p><p class="pl-author-bio">%s</p><a class="pl-arrow" href="%s">'
                'Leadership profile</a></div></section>'
                % (A(a["photo"]), A(a["name"]), E(a["name"]), E(a["title"]), E(a["bio_short"]), A(a["profile"])))
    return ('<section class="pl-author pl-author--org" aria-labelledby="author-h"><img src="%s" width="96" height="96" '
            'alt="%s" loading="lazy" decoding="async"><div><p class="pl-author-k">Published by</p><h2 id="author-h">%s</h2>'
            '<p class="pl-author-bio">%s</p><a class="pl-arrow" href="%s">About Pro Link Systems</a></div></section>'
            % (A(a["photo"]), A(a["name"] + " logo"), E(a["name"]), E(a["bio_short"]), A(a["profile"])))


def capbox(reg, p, cat):
    pr = reg["practices"][p.get("practice") or cat["practice"]]
    return ('<aside class="pl-capbox" aria-label="Related practice"><p class="pl-capbox-k">Related practice</p><div>'
            '<strong>%s</strong><p>%s</p><a class="pl-arrow" href="%s">%s</a></div></aside>'
            % (E(pr["name"]), E(pr["line"]), A(pr["url"]), E(pr["link"])))


def article_main(reg, slug, body):
    p = reg["posts"][slug]
    cat = category(reg, p["category"])
    _, a = author_for(reg, p)
    body, heads = add_heading_ids(body.strip("\n"))
    toc = heads if len(heads) >= TOC_MIN_SECTIONS else []
    parts = ['<main class="pl-art">',
             '<header class="pl-arthead">\n  <div class="pl-wrap pl-arthead-grid">',
             '    <div class="pl-arthead-inner">',
             '      <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/blog/">Insights</a></nav>',
             '      <p class="pl-cat"><a href="/blog/#%s">%s</a></p>' % (cat["slug"], E(cat["name"])),
             '      <h1>%s</h1>' % E(p["title"]),
             '      <p class="pl-dek">%s</p>' % E(dek(p)),
             '      ' + byline(reg, p, a),
             '    </div>',
             '    <figure class="pl-arthead-fig">%s</figure>' % art_img(reg, slug, eager=True),
             '  </div>\n</header>',
             '<div class="pl-wrap">\n<div class="pl-art-layout%s">' % ("" if toc else " pl-art-layout--single")]
    if toc:
        parts.append('<nav class="pl-toc" aria-label="In this article"><details open><summary>In this article</summary><ol>%s</ol></details></nav>'
                     % "".join('<li><a href="#%s">%s</a></li>' % (h, E(x)) for h, x in toc))
    parts.append('<article class="pl-art-body">')
    if p.get("takeaways"):
        parts.append('<div class="pl-takeaways"><p>Key takeaways</p><ul>%s</ul></div>'
                     % "".join("<li>%s</li>" % E(x) for x in p["takeaways"]))
    parts += ["<!-- PL:BODY -->", body, "<!-- /PL:BODY -->", capbox(reg, p, cat), author_box(a), "</article>",
              "</div>\n</div>"]
    rel = related(reg, slug)
    if rel:
        parts.append('<section class="pl-section pl-mist pl-art-related" aria-labelledby="related-h">\n  <div class="pl-wrap">\n'
                     '    <div class="pl-head pl-head--stack"><p class="pl-eyebrow">Related perspectives</p>'
                     '<h2 class="pl-h2" id="related-h">Continue reading</h2></div>\n'
                     '    <ul class="pl-ins-grid">%s</ul>\n  </div>\n</section>' % "".join(card(reg, s) for s in rel))
    parts += [cta_band(reg, cat, p.get("cta")), "</main>"]
    return "\n".join(parts)


ARTICLE_JS = '<script src="/assets/js/article.js?v=%s" defer></script>' % JS_VERSION


def with_article_js(page):
    """Load the small article script (contents list + reading position) exactly once, before </body>."""
    page = re.sub(r'[ \t]*<script src="/assets/js/article\.js[^"]*" defer></script>\n?', "", page)
    k = page.rfind("</body>")
    return page[:k] + ARTICLE_JS + "\n" + page[k:]


def author_node(reg, p):
    _, a = author_for(reg, p)
    if a["type"] == "Person":
        return {"@type": "Person", "@id": a["id"], "name": a["name"], "jobTitle": a["job_title"],
                "url": SITE + a["profile"],
                "worksFor": {"@type": "Organization", "@id": SITE + "/#organization", "name": "Pro Link Systems"}}
    return {"@type": "Organization", "@id": a["id"], "name": a["name"], "url": SITE + "/"}


def _object_span(text, start):
    """Index just past the JSON object that opens at text[start] == '{' (string-aware)."""
    depth, i, in_str = 0, start, False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced JSON object")


def update_head(head, reg, slug):
    """Existing post <head>: drop the legacy blog <style>, set the author node, rename the breadcrumb label."""
    p = reg["posts"][slug]
    head = re.sub(r"[ \t]*<style>(?:(?!</style>).)*?\.blog-(?:hero|cta-box)(?:(?!</style>).)*</style>\n?", "", head,
                  flags=re.S)

    def fix_block(m):
        block = m.group(2)
        if '"BlogPosting"' in block:
            block = re.sub(r'("dateModified":\s*")[^"]*(")', lambda m_: m_.group(1) + p["date_modified"][:10] + m_.group(2), block)
            k = block.find('"author"')
            if k >= 0:
                s = block.find("{", k)
                e = _object_span(block, s)
                node = json.dumps(author_node(reg, p), ensure_ascii=False, indent=2).replace("\n", "\n  ")
                block = block[:s] + node + block[e:]
        elif '"BreadcrumbList"' in block:
            block = re.sub(r'("name":\s*)"Blog"(,\s*"item":\s*"https://prolinksystems\.com/blog/")', r'\1"Insights"\2',
                           block)
        json.loads(block)  # never write a block that no longer parses
        return m.group(1) + block + m.group(3)

    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', fix_block, head, flags=re.S)


def extract_body(text):
    m = re.search(r"<!-- PL:BODY -->\n?(.*?)\n?<!-- /PL:BODY -->", text, re.S)
    if m:
        return m.group(1)
    a = text.find('<article class="blog-body">')
    if a < 0:
        raise ValueError("no article body found")
    s = a + len('<article class="blog-body">')
    e = text.find('<div class="blog-cta-box">', s)
    if e < 0:
        e = text.find("</article>", s)
    return text[s:e].strip("\n")


def rebuild_post(reg, slug):
    """Re-render an existing article around its unchanged body. Returns True when the file changed."""
    rel = "blog/%s.html" % slug
    t = read(rel).replace("\r\n", "\n")
    body = extract_body(t)
    reg["posts"][slug]["words"] = word_count(body)
    a = t.index("<!-- /PL:HEADER -->") + len("<!-- /PL:HEADER -->")
    b = t.index("<!-- PL:FOOTER -->")
    h = t.index("</head>")
    page = update_head(t[:h], reg, slug) + t[h:a] + "\n\n" + article_main(reg, slug, body) + "\n\n" + t[b:]
    return write(rel, with_article_js(chrome(page, rel)))


def new_post_page(reg, slug, seo_title, meta):
    """Complete page for a post generate_blog.py has just written (registry entry + body already set)."""
    p = reg["posts"][slug]
    url = "%s/blog/%s" % (SITE, slug)
    t, d = html.unescape(seo_title), html.unescape(meta)   # model text may arrive with or without entities
    posting = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
               "description": d, "author": author_node(reg, p),
               "publisher": {"@type": "Organization", "name": "Pro Link Systems",
                             "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"}},
               "datePublished": p["date_published"], "dateModified": p["date_modified"],
               "mainEntityOfPage": {"@type": "WebPage", "@id": url}, "url": url,
               "articleSection": category(reg, p["category"])["name"]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Insights", "item": SITE + "/blog/"},
        {"@type": "ListItem", "position": 3, "name": p["title"], "item": url}]}
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#webpage", "url": url,
               "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", "h1 + p"]}}
    ld = lambda o: '<script type="application/ld+json">\n%s\n</script>\n' % json.dumps(o, ensure_ascii=False, indent=2)
    head = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" + ICONS +
            "<title>%s</title>\n<meta name=\"description\" content=\"%s\">\n<meta name=\"robots\" content=\"index, follow\">\n"
            "<link rel=\"canonical\" href=\"%s\">\n<meta property=\"og:type\" content=\"article\">\n"
            "<meta property=\"og:url\" content=\"%s\">\n<meta property=\"og:title\" content=\"%s\">\n"
            "<meta property=\"og:description\" content=\"%s\">\n<meta property=\"og:image\" content=\"%s/logo.png\">\n"
            "<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:site\" content=\"@ProLink_Systems\">\n"
            "<meta name=\"twitter:image\" content=\"%s/logo.png\">\n<meta name=\"twitter:title\" content=\"%s\">\n"
            "<meta name=\"twitter:description\" content=\"%s\">\n"
            % (E(t), A(d), url, url, A(t), A(d), SITE, SITE, A(t), A(d))
            + ld(posting) +
            "<link rel=\"stylesheet\" href=\"/_shared.css?v=%s\">\n" % css_version() + TRACKING + ld(crumbs) + ld(webpage) +
            "</head>\n<body>\n<!-- PL:HEADER -->\n<!-- /PL:HEADER -->\n\n")
    body = p.pop("_body")
    page = head + article_main(reg, slug, body) + "\n\n<!-- PL:FOOTER -->\n<!-- /PL:FOOTER -->\n</body>\n</html>\n"
    return with_article_js(chrome(page, "blog/%s.html" % slug))


# ---------------------------------------------------------------------------------------------------------------
# Insights index

INDEX_TITLE = "IT Insights for Los Angeles Businesses | Pro Link Systems"
INDEX_META = ("Perspectives on technology leadership, cybersecurity, AI and IT strategy for Los Angeles businesses: analysis, "
              "checklists and guides from Pro Link Systems.")


def lead_panel(reg, slug):
    p = reg["posts"][slug]
    cat = category(reg, p["category"])
    _, a = author_for(reg, p)
    return ('<article class="pl-feature"><a href="/blog/%s"><div class="pl-lead-img">%s</div><div class="pl-lead-text">'
            '<p class="pl-lead-k">Featured analysis</p><span class="pl-cat">%s</span><h3 class="pl-lead-title">%s</h3>'
            '<p class="pl-lead-dek">%s</p><span class="pl-meta"><strong>%s</strong>%s<span>%d min read</span></span>'
            '<span class="pl-lead-more">Read the analysis</span></div></a></article>'
            % (slug, art_img(reg, slug, eager=True), E(cat["name"]), E(p["title"]), E(dek(p)), E(a["name"]),
               time_tag(p["date_published"]), minutes(p)))


def mini_card(reg, slug):
    p = reg["posts"][slug]
    return ('<li class="pl-mini"><a href="/blog/%s">%s<span class="pl-cat">%s</span><h3>%s</h3>'
            '<span class="pl-meta">%s<span>%d min read</span></span></a></li>'
            % (slug, art_img(reg, slug), E(category(reg, p["category"])["name"]), E(p["title"]),
               time_tag(p["date_published"]), minutes(p)))


def index_page(reg):
    ix = reg["index"]
    items = listed(reg)
    f = reg["featured"]
    lead = f["lead"]
    picks = [s for s in f["picks"] if s in reg["posts"] and s != lead and not reg["posts"][s].get("noindex")][:4]
    shown = {lead} | set(picks)
    latest = [s for s, _ in items if s not in shown][:LATEST_MAX]
    counts = {}
    for _, p in items:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    plural = lambda n: "%d article%s" % (n, "" if n == 1 else "s")
    topics = "".join('<a href="#%s"><span>%s</span><small>%s</small></a>' % (c["slug"], E(c["name"]), plural(counts.get(c["name"], 0)))
                     for c in reg["categories"] if counts.get(c["name"])) + \
        '<a href="#library"><span>All perspectives</span><small>%s</small></a>' % plural(len(items))
    chips = '<button type="button" data-cat="" aria-pressed="true">All topics</button>' + "".join(
        '<button type="button" data-cat="%s" aria-pressed="false">%s</button>' % (c["slug"], E(c["name"]))
        for c in reg["categories"] if counts.get(c["name"]))
    sections = []
    for c in reg["categories"]:
        posts = [(s, p) for s, p in items if p["category"] == c["name"]]
        if not posts:
            continue
        rows = "".join(
            '<li class="pl-lib-row" data-text="%s"><a href="/blog/%s"><span>%s</span></a><span class="pl-lib-meta">%s'
            '<span>%d min</span></span></li>'
            % (A(" ".join([p["title"], dek(p), c["name"], re.sub(r"^\d{4}-\d{2}(?:-\d{2})?-(?:t\d+-)?", "", s).replace("-", " ")]).lower()),
               s, E(p["title"]), time_tag(p["date_published"]), minutes(p)) for s, p in posts)
        sections.append('<details class="pl-lib" id="%s" data-cat="%s"><summary><h3>%s</h3><span class="pl-lib-sum">%s</span>'
                        '<span class="pl-lib-n">%s</span></summary><ul>%s</ul></details>'
                        % (c["slug"], c["slug"], E(c["name"]), E(c["summary"]), plural(len(posts)), rows))
    main = "\n".join([
        '<main class="pl-ins">',
        '<header class="pl-inshead">\n  <div class="pl-wrap">',
        '    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span>Insights</nav>',
        '    <h1 class="pl-h1">%s</h1>' % E(ix["h1"]),
        '    <p class="pl-lead-in">%s</p>' % E(ix["lead"]),
        '    <nav class="pl-topics" aria-label="Topics">%s</nav>' % topics,
        '  </div>\n</header>',
        '<section class="pl-section pl-ins-featured" aria-labelledby="featured-h">\n  <div class="pl-wrap">',
        '    <h2 class="pl-eyebrow" id="featured-h">Featured</h2>',
        '    ' + lead_panel(reg, lead),
        '    <ul class="pl-minis">%s</ul>' % "".join(mini_card(reg, s) for s in picks),
        '  </div>\n</section>',
        '<section class="pl-section pl-mist pl-ins-latest" id="latest" aria-labelledby="latest-h">\n  <div class="pl-wrap">',
        '    <div class="pl-ins-tools"><h2 class="pl-h2" id="latest-h">Latest perspectives</h2>'
        '<a class="pl-arrow" href="#library">Browse all %d by topic</a></div>' % len(items),
        '    <ul class="pl-ins-grid" id="pl-ins-list" data-page="%d">%s</ul>' % (PAGE_SIZE, "".join(card(reg, s) for s in latest)),
        '    <div class="pl-ins-more pl-ins-js"><button type="button" class="btn btn-outline">Show more articles</button></div>',
        '  </div>\n</section>',
        '<section class="pl-section pl-ins-library" id="library" aria-labelledby="library-h">\n  <div class="pl-wrap">',
        '    <div class="pl-ins-tools"><h2 class="pl-h2" id="library-h">Library</h2>'
        '<div class="pl-ins-search pl-ins-js"><label for="pl-ins-q">Search all articles</label>'
        '<input type="search" id="pl-ins-q" placeholder="Search by keyword" autocomplete="off"></div></div>',
        '    <div class="pl-ins-filter pl-ins-js" role="group" aria-label="Filter by topic">%s</div>' % chips,
        '    <p class="pl-ins-count" aria-live="polite">%s</p>' % plural(len(items)),
        '    <div class="pl-libs">%s</div>' % "".join(sections),
        '    <p class="pl-ins-empty" hidden>No articles match that search. Try another keyword or topic.</p>',
        '  </div>\n</section>',
        cta_band(reg),
        '</main>'])
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Insights", "item": SITE + "/blog/"}]}
    coll = {"@context": "https://schema.org", "@type": "CollectionPage", "@id": SITE + "/blog/#webpage",
            "url": SITE + "/blog/", "name": "Insights", "headline": ix["h1"], "description": html.unescape(INDEX_META),
            "isPartOf": {"@id": SITE + "/#website"},
            "publisher": {"@type": "Organization", "@id": SITE + "/#organization", "name": "Pro Link Systems"},
            "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", "h1 + p"]}}
    ld = lambda o: '<script type="application/ld+json">\n%s\n</script>\n' % json.dumps(o, ensure_ascii=False, indent=2)
    page = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" + ICONS +
            "<title>%s</title>\n<meta name=\"description\" content=\"%s\">\n<meta name=\"robots\" content=\"index, follow\">\n"
            "<link rel=\"canonical\" href=\"%s/blog/\">\n" % (INDEX_TITLE, INDEX_META, SITE) +
            "<link rel=\"stylesheet\" href=\"/_shared.css?v=%s\">\n" % css_version() + TRACKING + ld(crumbs) + ld(coll) +
            "</head>\n<body>\n<!-- PL:HEADER -->\n<!-- /PL:HEADER -->\n\n" + main +
            "\n\n<!-- PL:FOOTER -->\n<!-- /PL:FOOTER -->\n"
            "<script src=\"/assets/js/insights.js?v=%s\" defer></script>\n</body>\n</html>\n" % JS_VERSION)
    return chrome(page, "blog/index.html")


def home_block(reg):
    items = listed(reg)
    newest = [s for s, p in items if p.get("executive")][:reg["home"].get("newest", 1)]
    order = newest + [reg["featured"]["lead"]] + reg["featured"]["picks"] + [s for s, _ in items]
    chosen = []
    for s in order:
        if s in reg["posts"] and not reg["posts"][s].get("noindex") and s not in chosen:
            chosen.append(s)
        if len(chosen) == HOME_CARDS:
            break
    cards = "".join('      <a class="home-blog-card" href="/blog/%s">\n        <div class="hb-meta">%s &nbsp;&middot;&nbsp; %s</div>\n'
                    '        <h3>%s</h3>\n      </a>\n'
                    % (s, E(category(reg, reg["posts"][s]["category"])["name"]), long_date(reg["posts"][s]["date_published"]),
                       E(reg["posts"][s]["title"])) for s in chosen)
    return "<!-- HOME_BLOG_START -->\n" + cards + "      <!-- HOME_BLOG_END -->"


def write_home(reg):
    t = read("index.html")
    if "<!-- HOME_BLOG_START -->" not in t or "<!-- HOME_BLOG_END -->" not in t:
        print("[insights] home markers not found; home cards skipped")
        return False
    nl = "\r\n" if "\r\n" in t else "\n"
    block = home_block(reg).replace("\n", nl)
    return write("index.html", re.sub(r"<!-- HOME_BLOG_START -->.*?<!-- HOME_BLOG_END -->", lambda _m: block, t, flags=re.S))


# ---------------------------------------------------------------------------------------------------------------
# profile pages

def profile_page(reg, key):
    a = reg["authors"][key]
    pr = a["profile_page"]
    url = SITE + a["profile"]
    rel = a["profile"].strip("/") + ".html"
    about = read("about.html").replace("\r\n", "\n")
    head_src = about[:about.index("</head>")]
    tracking = "".join(m.group(0) + "\n" for m in re.finditer(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>", head_src, re.S))
    person = {"@type": "Person", "@id": a["id"], "name": a["name"], "jobTitle": a["job_title"],
              "description": pr["meta"], "image": SITE + pr["photo"], "url": url, "sameAs": a.get("same_as", []),
              "worksFor": {"@type": "Organization", "@id": SITE + "/#organization", "name": "Pro Link Systems",
                           "url": SITE + "/"},
              "knowsAbout": a.get("focus", [])}
    if a.get("alumni_of"):
        person["alumniOf"] = {"@type": "CollegeOrUniversity", "name": a["alumni_of"]}
    prof = {"@context": "https://schema.org", "@type": "ProfilePage", "@id": url + "#webpage", "url": url,
            "name": pr["title"], "isPartOf": {"@id": SITE + "/#website"}, "mainEntity": person}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "About", "item": SITE + "/about"},
        {"@type": "ListItem", "position": 3, "name": a["name"], "item": url}]}
    ld = lambda o: '<script type="application/ld+json">\n%s\n</script>\n' % json.dumps(o, ensure_ascii=False, indent=2)
    mine = [s for s, p in listed(reg) if author_for(reg, p)[0] == key]
    flags = "".join('<span class="pl-flag">Review %s</span>' % r for r in pr.get("flags", []))
    main = "\n".join([
        '<main>',
        '<section class="pl-pagehead">\n  <div class="pl-wrap">',
        '    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/about">About</a><span>/</span>%s</nav>' % E(a["name"]),
        '    <p class="pl-eyebrow">Leadership</p>',
        '    <h1 class="pl-h1">%s</h1>' % E(a["name"]),
        '    <p class="pl-lead">%s</p>' % E(a["title"]),
        '  </div>\n</section>',
        '<section class="pl-section" aria-labelledby="bio-h">\n  <div class="pl-wrap">\n    <div class="pl-split pl-split--wide-text pl-profile">',
        '      <div>',
        '        <h2 class="pl-h2" id="bio-h">%s</h2>' % E(pr["heading"]),
        '        <div class="pl-body" style="margin-top:28px">%s</div>' % "".join("<p>%s</p>" % E(x) for x in a["bio"]),
        ('        <p class="pl-flag-note">%s</p>' % flags) if flags else "",
        '        <p class="pl-profile-k">Areas of focus</p>',
        '        <ul class="pl-checks">%s</ul>' % "".join("<li>%s</li>" % E(x) for x in a.get("focus", [])),
        '        <div class="pl-actions">%s<a class="pl-arrow" href="/about">About Pro Link Systems</a></div>'
        % "".join('<a class="pl-arrow" href="%s" rel="me">LinkedIn profile</a>' % A(u) for u in a.get("same_as", [])[:1]),
        '      </div>',
        '      <figure>\n        <img src="%s" srcset="%s" sizes="(max-width: 1024px) 92vw, 520px" width="%d" height="%d" '
        'alt="%s" decoding="async">\n        <figcaption>%s</figcaption>\n      </figure>'
        % (A(pr["photo"]), A(pr["srcset"]), pr["width"], pr["height"], A(pr["alt"]), E(pr["caption"])),
        '    </div>\n  </div>\n</section>'])
    if mine:
        main += ('\n<section class="pl-section pl-mist" aria-labelledby="by-h">\n  <div class="pl-wrap">\n'
                 '    <div class="pl-head pl-head--stack"><p class="pl-eyebrow">Insights</p><h2 class="pl-h2" id="by-h">'
                 'Perspectives by %s</h2></div>\n    <ul class="pl-ins-grid">%s</ul>\n  </div>\n</section>'
                 % (E(a["name"]), "".join(card(reg, s) for s in mine[:6])))
    main += "\n" + cta_band(reg) + "\n</main>"
    page = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" + tracking +
            "<title>%s</title>\n<meta name=\"description\" content=\"%s\">\n<meta name=\"robots\" content=\"index, follow\">\n"
            "<link rel=\"canonical\" href=\"%s\">\n<meta property=\"og:type\" content=\"profile\">\n"
            "<meta property=\"og:url\" content=\"%s\">\n<meta property=\"og:title\" content=\"%s\">\n"
            "<meta property=\"og:description\" content=\"%s\">\n<meta property=\"og:image\" content=\"%s/og/about.png\">\n"
            "<meta name=\"twitter:card\" content=\"summary_large_image\">\n"
            % (E(pr["title"]), A(pr["meta"]), url, url, A(pr["title"]), A(pr["meta"]), SITE) + ICONS +
            "<link rel=\"stylesheet\" href=\"/_shared.css?v=%s\">\n" % css_version() + ld(crumbs) + ld(prof) +
            "</head>\n<body>\n\n<!-- PL:HEADER -->\n<!-- /PL:HEADER -->\n\n" + main +
            "\n\n<!-- PL:FOOTER -->\n<!-- /PL:FOOTER -->\n\n</body>\n</html>\n")
    return rel, chrome(page, rel)


def add_to_sitemap(loc, lastmod):
    sm = read("sitemap.xml")
    if "<loc>%s</loc>" % loc in sm:
        return False
    nl = "\r\n" if "\r\n" in sm else "\n"
    entry = ("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n    <changefreq>monthly</changefreq>\n"
             "    <priority>0.6</priority>\n  </url>\n" % (loc, lastmod)).replace("\n", nl)
    return write("sitemap.xml", sm.replace("</urlset>", entry + "</urlset>"))


def sync_sitemap_dates(reg):
    """lastmod of an article in sitemap.xml = the date its content last changed (registry date_modified)."""
    sm = read("sitemap.xml")
    changed = 0
    for slug, p in reg["posts"].items():
        if p.get("noindex"):
            continue
        loc = "%s/blog/%s" % (SITE, slug)
        pat = re.compile(r"(<loc>%s</loc>\s*<lastmod>)([^<]+)(</lastmod>)" % re.escape(loc))
        m = pat.search(sm)
        want = p.get("date_modified") or p["date_published"]
        if m and m.group(2)[:10] != want[:10] and want[:10] > p["date_published"][:10]:
            sm = pat.sub(lambda g: g.group(1) + want[:10] + g.group(3), sm, count=1)
            changed += 1
    if changed:
        write("sitemap.xml", sm)
    return changed


# ---------------------------------------------------------------------------------------------------------------
# validation + CLI

def check(reg):
    probs = []
    names = [c["name"] for c in reg["categories"]]
    if len(names) != 7 or len(set(names)) != 7:
        probs.append("expected exactly 7 distinct categories, found %d" % len(set(names)))
    for c in reg["categories"]:
        if c["practice"] not in reg["practices"]:
            probs.append("category %s: unknown practice %s" % (c["slug"], c["practice"]))
    f = reg["featured"]
    for s in [f["lead"]] + f["picks"]:
        if s not in reg["posts"]:
            probs.append("featured post not in registry: " + s)
        elif reg["posts"][s].get("noindex"):
            probs.append("featured post is noindexed: " + s)
    if not 3 <= len(f["picks"]) <= 4:
        probs.append("featured picks: expected 3-4, found %d" % len(f["picks"]))
    for s, p in reg["posts"].items():
        if p["category"] not in names:
            probs.append("%s: unknown category %r" % (s, p["category"]))
        key = p.get("author") or reg["default_author"]
        if key not in reg["authors"]:
            probs.append("%s: unknown author %r" % (s, key))
        elif reg["authors"][key].get("requires_approval") and not p.get("approved_by"):
            probs.append("%s: attributed to %s without a recorded approval" % (s, key))
        for r in p.get("reviewers", []):
            if r not in reg["authors"]:
                probs.append("%s: unknown reviewer %r" % (s, r))
        if not os.path.exists(os.path.join(ROOT, "blog", s + ".html")):
            probs.append("%s: blog/%s.html is missing" % (s, s))
        if not os.path.exists(os.path.join(ROOT, art_rel(s))):
            probs.append("%s: illustration %s is missing" % (s, art_rel(s)))
        if len(p.get("takeaways", [])) not in (0, 3, 4, 5):
            probs.append("%s: takeaways should be 3-5 bullets" % s)
    on_disk = {os.path.splitext(n)[0] for n in os.listdir(os.path.join(ROOT, "blog")) if n.endswith(".html")} - {"index"}
    for s in sorted(on_disk - set(reg["posts"])):
        probs.append("blog/%s.html has no registry entry" % s)
    for key, a in reg["authors"].items():
        for fld in ("photo",):
            if not os.path.exists(os.path.join(ROOT, a[fld].lstrip("/"))):
                probs.append("author %s: %s %s missing" % (key, fld, a[fld]))
    return probs


def rebuild(reg):
    changed = []
    for s in reg["posts"]:
        ensure_art(reg, s)
        if rebuild_post(reg, s):
            changed.append("blog/%s.html" % s)
    if write("blog/index.html", index_page(reg)):
        changed.append("blog/index.html")
    if write_home(reg):
        changed.append("index.html")
    if sync_sitemap_dates(reg):
        changed.append("sitemap.xml")
    for key, a in reg["authors"].items():
        if a.get("profile_page"):
            rel, text = profile_page(reg, key)
            if write(rel, text):
                changed.append(rel)
            add_to_sitemap(SITE + a["profile"], a["profile_page"]["lastmod"])
    return changed


def main():
    reg = load()
    if "--rebuild" in sys.argv:
        changed = rebuild(reg)
        save(reg)
        print("[insights] rebuilt; %d file(s) changed" % len(changed))
    probs = check(reg)
    if probs:
        print("[insights] registry problems (%d):\n  %s" % (len(probs), "\n  ".join(probs)))
        sys.exit(1)
    print("[insights] registry OK: %d posts, %d listed, featured %s + %d picks"
          % (len(reg["posts"]), len(listed(reg)), reg["featured"]["lead"][:32], len(reg["featured"]["picks"])))


if __name__ == "__main__":
    main()
