#!/usr/bin/env python3
"""
chrome/build_blog_registry.py -- one-time bootstrap of editorial/blog_registry.json (redesign-2026, iteration 3).

Reads every blog/<slug>.html for the facts the Insights renderer needs (H1, meta description, JSON-LD dates,
robots, canonical, word count) and takes each post's category and local/executive flags from the article
classification (a JSON list passed as the first argument). Editorial settings (categories, practices, authors,
featured selection, CTA, index copy) are defined below. Re-running keeps any per-post edits already made in the
registry (category, author, approvals, reviewers, takeaways, summary, practice, related, cta).

    python chrome/build_blog_registry.py path/to/articles.json
After this, generate_blog.py maintains the registry: every new post adds its own entry.
"""
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import insights  # noqa: E402

CATEGORIES = [
    {"slug": "cybersecurity-risk", "name": "Cybersecurity & Risk", "practice": "cybersecurity",
     "summary": "Threats, controls and the decisions that reduce exposure.",
     "cta": "Schedule a Security Consultation",
     "alt": "Abstract illustration of layered security perimeters around a protected core"},
    {"slug": "ai-automation", "name": "Artificial Intelligence & Automation", "practice": "ai",
     "summary": "Adopting AI and automation with data governance first.",
     "cta": "Schedule an AI Strategy Consultation",
     "alt": "Abstract illustration of a layered network of connected nodes"},
    {"slug": "technology-leadership", "name": "Technology Leadership", "practice": "strategy",
     "summary": "Strategy, budgets and the operating model behind technology.",
     "cta": "Schedule a Technology Consultation",
     "alt": "Abstract illustration of a stepped roadmap with a current-position marker"},
    {"slug": "cloud-infrastructure", "name": "Cloud & Infrastructure", "practice": "cloud",
     "summary": "Microsoft 365, cloud platforms and the infrastructure underneath.",
     "cta": "Schedule a Cloud Consultation",
     "alt": "Abstract illustration of stacked infrastructure layers joined by a connector"},
    {"slug": "governance-compliance", "name": "Governance & Compliance", "practice": "strategy",
     "summary": "Policies, reviews and records that hold up under scrutiny.",
     "cta": "Schedule a Technology Consultation",
     "alt": "Abstract illustration of a control matrix with one highlighted cell"},
    {"slug": "business-continuity", "name": "Business Continuity", "practice": "continuity",
     "summary": "Recovery, resilience and planning for the day systems fail.",
     "cta": "Schedule a Continuity Consultation",
     "alt": "Abstract illustration of a recovery arc returning to its baseline"},
    {"slug": "industry-perspectives", "name": "Industry Perspectives", "practice": "managed",
     "summary": "How technology decisions play out in specific sectors.",
     "cta": "Schedule a Technology Consultation",
     "alt": "Abstract illustration of building blocks with one highlighted block"},
]

# The six practice areas, with the descriptions already used on the home page.
PRACTICES = {
    "managed": {"name": "Managed Technology Services", "url": "/outsourced-it-services-los-angeles",
                "line": "Day-to-day technology run by one accountable team: monitored, documented and supported around the clock.",
                "link": "Explore managed technology services"},
    "cybersecurity": {"name": "Cybersecurity & Risk", "url": "/cybersecurity-services",
                      "line": "Layered protection across identity, endpoints, email, network and cloud, with monitoring and documented controls.",
                      "link": "Explore the cybersecurity practice"},
    "cloud": {"name": "Cloud & Infrastructure Engineering", "url": "/cloud-services",
              "line": "Microsoft 365, Azure, AWS and hybrid environments, with continuity designed in from the start.",
              "link": "Explore cloud and infrastructure engineering"},
    "continuity": {"name": "Cloud & Infrastructure Engineering", "url": "/backup-disaster-recovery",
                   "line": "Microsoft 365, Azure, AWS and hybrid environments, with continuity designed in from the start.",
                   "link": "Explore business continuity and disaster recovery"},
    "strategy": {"name": "Technology Strategy & Consulting", "url": "/virtual-cio",
                 "line": "A virtual CIO at your leadership table, responsible for roadmaps, budgets, vendor strategy and risk reporting.",
                 "link": "Explore technology strategy and consulting"},
    "transformation": {"name": "Digital Transformation", "url": "/case-studies",
                       "line": "Migrations, consolidations and platform changes planned around how your organization actually operates.",
                       "link": "See transformation case studies"},
    "ai": {"name": "AI & Business Automation", "url": "/ai-automation-services",
           "line": "Private knowledge assistants, Copilot readiness and workflow automation, evaluated for privacy and security first.",
           "link": "Explore AI and business automation"},
}

AUTHORS = {
    "brian-shad": {
        "type": "Person", "name": "Brian Shad", "job_title": "Founder & CEO", "title": "Founder & CEO, Pro Link Systems",
        "requires_approval": True,
        "id": "https://prolinksystems.com/about#brian-shad", "profile": "/leadership/brian-shad",
        "photo": "/assets/photos/web/brian-shad-avatar-160.webp",
        "same_as": ["https://www.linkedin.com/in/brianshad/"],
        "bio_short": ("Brian Shad founded Pro Link Systems in 1999. His more than 25 years of work span technology "
                      "leadership, enterprise infrastructure, cybersecurity, strategic consulting and digital transformation."),
        "bio": [
            "Brian Shad is the founder and CEO of Pro Link Systems, which he established in 1999. He leads the firm’s "
            "technology direction and works directly with client leadership teams on strategy, architecture and major initiatives.",
            "Over more than 25 years in technology leadership, his work has spanned enterprise infrastructure, cybersecurity, "
            "strategic consulting and digital transformation.",
        ],
        "focus": ["Technology leadership", "Enterprise infrastructure", "Cybersecurity", "Strategic consulting",
                  "Digital transformation"],
        "profile_page": {
            "title": "Brian Shad, Founder & CEO | Pro Link Systems",
            "meta": ("Brian Shad founded Pro Link Systems in 1999. Profile: 25+ years across technology leadership, "
                     "enterprise infrastructure, cybersecurity and strategy."),
            "heading": "Biography",
            "photo": "/assets/photos/web/brian-shad-portrait-1100.webp",
            "srcset": "/assets/photos/web/brian-shad-portrait-720.webp 720w, /assets/photos/web/brian-shad-portrait-1100.webp 1100w",
            "width": 1100, "height": 687,
            "alt": "Brian Shad in a navy blazer and striped tie, photographed outdoors",
            "caption": "Brian Shad, Founder & CEO",
            "lastmod": "2026-11-21",
            "flags": ["R12"],
        },
    },
    "pro-link-systems": {
        "type": "Organization", "name": "Pro Link Systems", "byline_line": "Insights",
        "id": "https://prolinksystems.com/#organization", "profile": "/about", "photo": "/apple-touch-icon.png",
        "bio_short": ("Pro Link Systems is an independent technology management, advisory and engineering firm, "
                      "serving organizations since 1999."),
    },
}

FEATURED = {
    "lead": "2026-09-23-t111-a-one-page-technology-risk-summary-for-your-board",
    "picks": [
        "2026-09-05-t102-modern-ransomware-is-data-theft-why-backups-alone-no-lo",
        "2026-08-29-t98-an-ai-acceptable-use-policy-your-los-angeles-employees-",
        "2026-09-09-t104-cyber-insurance-questionnaires-answering-accurately-bef",
        "2026-09-17-t108-technology-debt-how-deferred-it-decisions-compound-for-",
    ],
}

CTA = {
    "eyebrow": "Next step",
    "heading": "Discuss Your Technology Strategy",
    "text": ("Connect with our advisory team to explore how Pro Link Systems can help your organization strengthen its "
             "technology infrastructure, reduce risk, and advance its business objectives."),
    "button": "Schedule a Technology Consultation",
    "href": "/contact",
    "phone": "1-800-890-6133",
}

INDEX = {
    "eyebrow": "Insights",
    "h1": "Perspectives on Technology, Security and Business Strategy.",
    "lead": ("Expert analysis and practical perspectives on technology leadership, cybersecurity, artificial "
             "intelligence, and the evolving challenges facing modern organizations."),
}

# Per-post settings that cannot be read from the page.
APPROVED = {  # Brian's recorded approvals (commit de7b063 published his approved wording, 2026-11-20)
    "2026-11-20-what-a-microsoft-365-security-assessment-checks": {"approved_by": "brian-shad", "approved_on": "2026-11-20"},
}
CTA_OVERRIDES = {
    "2026-08-07-t20-wildfire-season-power-shutoff-continuity-checklist-la": {
        "secondary": {"label": "Get the continuity checklist", "href": "/continuity-checklist"}},
    "2026-11-20-what-a-microsoft-365-security-assessment-checks": {
        "secondary": {"label": "See the Microsoft 365 Security Assessment", "href": "/m365-security-assessment"}},
}
KEEP = ("category", "author", "approved_by", "approved_on", "reviewers", "takeaways", "summary", "dek", "practice", "related",
        "cta", "local", "executive")


def facts(slug):
    t = io.open(os.path.join(ROOT, "blog", slug + ".html"), encoding="utf-8").read()
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    meta = re.search(r'<meta name="description" content="([^"]*)"', t)
    pub = re.search(r'"datePublished":\s*"([^"]+)"', t)
    mod = re.search(r'"dateModified":\s*"([^"]+)"', t)
    robots = re.search(r'<meta name="robots" content="([^"]*)"', t)
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', t)
    body = insights.extract_body(t)
    return {
        "title": insights.plain(h1.group(1)),
        "summary": html.unescape(meta.group(1)).strip() if meta else "",
        "date_published": pub.group(1)[:10],
        "date_modified": (mod.group(1) if mod else pub.group(1))[:10],
        "noindex": bool(robots and "noindex" in robots.group(1)),
        "canonical": canon.group(1) if canon else "",
        "words": insights.word_count(body),
    }


def main():
    cls = {x["slug"]: x for x in json.load(io.open(sys.argv[1], encoding="utf-8"))}
    old = insights.load() if os.path.exists(insights.REGISTRY) else {"posts": {}}
    reg = {
        "_comment": ("Single source of truth for Insights (blog) presentation: categories, practices, authors, featured "
                     "selection and per-article metadata. Rendered by chrome/insights.py; new posts are added by "
                     "generate_blog.py. Brian 2026-11-21: attribute an article to Brian Shad only with a recorded "
                     "approval (author + approved_by); everything else is published under the organization."),
        "version": 1,
        "default_author": "pro-link-systems",
        "default_category": "technology-leadership",
        "categories": CATEGORIES, "practices": PRACTICES, "authors": AUTHORS, "featured": FEATURED,
        "home": {"newest": 1}, "cta": CTA, "index": INDEX, "posts": {},
    }
    slugs = sorted(os.path.splitext(n)[0] for n in os.listdir(os.path.join(ROOT, "blog"))
                   if n.endswith(".html") and n != "index.html")
    for slug in slugs:
        c = cls[slug]
        p = facts(slug)
        p.update({"category": c["category"], "local": bool(c["local"]), "executive": bool(c["executive"]),
                  "author": "pro-link-systems", "reviewers": [], "takeaways": []})
        if slug in APPROVED:
            p.update(APPROVED[slug], author="brian-shad")
        if slug in CTA_OVERRIDES:
            p["cta"] = CTA_OVERRIDES[slug]
        for k in KEEP:
            if k in old["posts"].get(slug, {}):
                p[k] = old["posts"][slug][k]
        p["illustration"] = "/" + insights.art_rel(slug)
        reg["posts"][slug] = p
    insights.save(reg)
    print("registry: %d posts (%d noindex) -> %s" % (len(reg["posts"]), sum(p["noindex"] for p in reg["posts"].values()),
                                                     os.path.relpath(insights.REGISTRY, ROOT)))


if __name__ == "__main__":
    main()
