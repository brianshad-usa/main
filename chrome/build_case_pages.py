#!/usr/bin/env python3
"""
chrome/build_case_pages.py -- build the Client Success hub (case-studies.html) and one page per major case study
(case-studies/<slug>.html) from the CASES data below. Facts come only from the case-study source files and
editorial/verified_facts.json; anything awaiting Brian's decision carries a neutral "Review R#" marker.

    python chrome/build_case_pages.py      # then: python chrome/apply_chrome.py

- Detail pages copy the tracking scripts from case-studies.html's <head>, get their own title, description,
  canonical, Open Graph and JSON-LD (BreadcrumbList + WebPage), and empty PL:HEADER / PL:FOOTER markers that
  apply_chrome.py fills.
- Cases with "noindex": True (pending a separate approval) get robots noindex and stay out of the sitemap.
- Indexable detail pages are added to sitemap.xml once (idempotent).
- The hub keeps its URL, title, description, canonical and JSON-LD; only its <main> is regenerated.
"""
import html
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://prolinksystems.com"
E = lambda s: html.escape(s, quote=False)
A = lambda s: html.escape(s, quote=True)
FLAG = lambda r: '<span class="pl-flag">Review %s</span>' % r

CASES = [
    {
        "slug": "global-holdings", "client": "Global Holdings", "sector": "Healthcare imaging", "current": False,
        "status": "Past engagement, 12+ years to 2021", "flags": ["R4"],
        "title": "Global Holdings Case Study: Imaging Network | Pro Link",
        "meta": "How Pro Link Systems designed and ran the network, AWS imaging platform and patient portal behind 19 diagnostic imaging facilities for 12+ years.",
        "h1": "A secure imaging backbone for 19 facilities and hundreds of partner sites.",
        "card": "Network, AWS imaging platform and secure portal for a regional diagnostic imaging provider.",
        "plate": ("19", "owned facilities on one network and imaging platform"),
        "summary": "For more than 12 years, to 2021, Pro Link Systems designed and operated the technology behind Global Holdings, a Southern California diagnostic imaging provider focused on MRI and CT. We built the network across its 19 owned facilities, consolidated imaging studies from every modality into an AWS environment we architected and managed, and ran a secure portal for referring doctors and patients.",
        "metrics": [("19", "owned facilities on one network"), ("Hundreds", "of partner facilities sending studies to the same platform"),
                    ("Thousands", "of imaging studies handled each month"), ("12+ yrs", "engagement, to 2021")],
        "snapshot": [("Industry", "Healthcare: diagnostic medical imaging, focused on MRI and CT"),
                     ("Location", "Southern California; 19 owned facilities and a referral network of hundreds of partner facilities"),
                     ("Size", "200+ employees"), ("Relationship", None),
                     ("Scope", "Network design, AWS cloud architecture, imaging (DICOM) workflows, secure patient portal, security")],
        "relationship": "More than 12 years, ending in 2021",
        "challenge": "Global Holdings ran 19 owned imaging facilities and referred patients to hundreds of partner facilities owned by other medical groups. Studies produced on many modalities, in many locations and under many ownership arrangements all had to reach one place for processing and clinician access.",
        "complexity": "This was protected health information, in an industry that has seen repeated, high-profile breaches. Patient records and imaging data needed airtight security and privacy, while referring doctors and patients needed convenient, appropriate access to studies. Sites averaged about five imaging modalities each.",
        "approach": ["A network designed from the ground up across all 19 owned facilities",
                     "DICOM ingestion from every modality at every location",
                     "A cloud environment on AWS, architected and managed by Pro Link, consolidating imagery for processing and access",
                     "Image transfer from hundreds of joint-venture and referral facilities into the same environment",
                     "A secure, access-controlled patient portal for referring doctors and patients",
                     "A security-and-privacy-first posture throughout the engagement"],
        "outcomes": ["A partnership of more than 12 years supporting 200+ employees across 19 facilities",
                     "One consolidated environment receiving studies from every owned modality and hundreds of partner sites",
                     "Thousands of imaging studies handled each month",
                     "No cybersecurity incident at any point during the engagement " + FLAG("R4")],
        "value": "A single, secure imaging platform that scaled with the referral network and gave clinicians and patients appropriate access to studies, maintained by the same partner for more than a decade.",
    },
    {
        "slug": "cunico", "client": "Cunico Corp.", "sector": "Precision manufacturing", "current": True,
        "status": "Current client since 2012", "flags": ["R1"],
        "title": "Cunico Case Study: 13-Year IT Partnership | Pro Link",
        "meta": "How Pro Link Systems has run and secured Cunico's multi-site technology since 2012, through growth and its 2022 acquisition by BWX Technologies.",
        "h1": "Thirteen years of technology governance, through growth and an acquisition.",
        "card": "Multi-site environments, hardened security and support through an acquisition by BWX Technologies.",
        "plate": ("13+ yrs", "continuously renewed partnership, since 2012"),
        "summary": "Since 2012, Pro Link Systems has been the outsourced IT and technology-governance partner for Cunico, a precision manufacturer with a legacy of more than 70 years. We maintain its on-premises and cloud environments across multiple sites, hardened its security with continuous monitoring, and supported its integration into BWX Technologies after the 2022 acquisition.",
        "metrics": [("13+ yrs", "continuously renewed partnership, since 2012"), ("Multi-site", "on-premises and cloud environments"),
                    ("2022", "integration into BWX Technologies")],
        "snapshot": [("Industry", "Precision manufacturing: valves, manifolds and fittings for marine and shipbuilding applications"),
                     ("Location", "Long Beach, California; multiple sites"), ("Size", "35 employees"), ("Relationship", None),
                     ("Scope", "Managed IT, cybersecurity, cloud, backup and disaster recovery, technology governance")],
        "relationship": "Client since May 2012",
        "challenge": "As Cunico grew, it needed rock-solid technology governance and infrastructure that matched the standards of the platforms it supplies. After its acquisition by BWX Technologies in April 2022, its systems also had to align with enterprise-grade practices while staying reliable day to day.",
        "approach": ["Architected, implemented and maintained local and cloud-native environments across Cunico’s multiple sites",
                     "Hardened its cybersecurity posture, with continuous monitoring and defense of critical systems",
                     "Designed and enforced workflows, backup and disaster-recovery strategies and access controls as the company scaled",
                     "Supported the integration into BWXT, aligning systems with enterprise-grade practices"],
        "outcomes": ["A continuously renewed partnership of more than 13 years",
                     "A well-governed environment that carried Cunico through its integration into BWXT"],
        "value": "Cunico operates today within BWXT’s Government Operations segment, on infrastructure secured and maintained by the same partner for more than a decade.",
    },
    {
        "slug": "lisi-aerospace", "client": "LISI Aerospace", "sector": "Aerospace manufacturing", "current": False,
        "status": "Past engagement, 2019–2021", "flags": ["R2"],
        "title": "LISI Aerospace Case Study: IT Stabilized | Pro Link",
        "meta": "How Pro Link Systems took ownership of LISI Aerospace's IT administration and stabilized operations within 90 days, through the move to remote work.",
        "h1": "Bringing order to a multinational manufacturer’s IT within 90 days.",
        "card": "IT administration taken over and stabilized within 90 days, then carried through the move to remote work.",
        "plate": ("90 days", "to stabilized IT operations"),
        "summary": "From October 2019 to August 2021, Pro Link Systems took ownership of IT administration for LISI Aerospace, a 700-person aerospace fastener manufacturer with its main plant in Torrance and facilities across North America. Operations stabilized within 90 days, and the environment stayed resilient through the move to remote work.",
        "metrics": [("90 days", "to stabilized operations"), ("700", "employees"), ("3 sites", "in Southern California managed by Pro Link")],
        "snapshot": [("Industry", "Aerospace manufacturing: fasteners and precision components"),
                     ("Location", "Main plant in Torrance, California, with facilities in Canada, Mexico and elsewhere in North America"),
                     ("Size", "700 employees"), ("Relationship", None),
                     ("Scope", "IT administration, network modernization, security agents, remote work")],
        "relationship": "October 2019 – August 2021",
        "challenge": "LISI Aerospace asked Pro Link to bring order to a disordered IT environment spanning its Torrance main plant and facilities across North America, and to take ownership of its IT administrative infrastructure: hosts, virtual machines, communication systems (voice, email and messaging) and security policies. The engagement would soon include the operational pressures of the COVID-19 pandemic.",
        "approach": ["A comprehensive IT management system", "A modernized network topology",
                     "Security agents deployed across the environment",
                     "Additional IT staff onboarded across California and eventually Canada",
                     "A transition to remote-work solutions during the pandemic"],
        "outcomes": ["Operations stabilized within 90 days of the engagement",
                     "Three Southern California sites managed by Pro Link",
                     "Continuity maintained through the move to remote work"],
        "value": "A comprehensive IT management system that carried a multinational manufacturer through the operational shock of 2020 without losing continuity.",
    },
    {
        "slug": "snitzer-law", "client": "Law Offices of Alan B. Snitzer", "sector": "Legal", "current": True,
        "status": "Current client for 18 years", "flags": [],
        "title": "Law Firm Case Study: 18 Years, Azure Cloud | Pro Link",
        "meta": "How Pro Link Systems moved the Law Offices of Alan B. Snitzer from an on-premises data center to Microsoft Azure over an 18-year partnership.",
        "h1": "From an on-premises data center to Azure, across 18 years of growth.",
        "card": "From a data center in the firm’s own office to Microsoft Azure, with every office move handled.",
        "plate": ("90%+", "of the firm’s environment now on Microsoft Azure"),
        "summary": "For 18 years, Pro Link Systems has been the only IT company for the Law Offices of Alan B. Snitzer in Pasadena. We have carried the firm from a data center in its own office to the cloud, where over 90% of its environment now runs on Microsoft Azure, and handled the infrastructure for its office moves along the way.",
        "metrics": [("18 yrs", "partnership that continues today"), ("90%+", "of the environment on Microsoft Azure"),
                    ("Multiple", "office relocations, infrastructure moved by Pro Link")],
        "snapshot": [("Industry", "Legal"), ("Location", "Pasadena, California"), ("Relationship", None),
                     ("Scope", "Managed IT, cloud migration to Microsoft Azure, security, office relocations")],
        "relationship": "Client for 18 years",
        "challenge": "The firm’s environment started entirely on premises, in a data center at its own office. As the practice grew, so did the demands on that infrastructure: more staff, more data, higher security expectations and a series of office relocations, each of which meant moving critical systems without disrupting the firm’s work or its confidentiality obligations.",
        "approach": ["Many migrations and upgrades across the entire environment as the practice scaled",
                     "A move from the on-premises data center to the cloud: today, over 90% of the firm’s environment runs on Microsoft Azure",
                     "A premium security umbrella around the firm’s data, appropriate to a law practice’s confidentiality obligations",
                     "The infrastructure move handled for each office relocation"],
        "outcomes": ["Over 90% of the environment running on Azure",
                     "Multiple office relocations completed with Pro Link managing the infrastructure",
                     "An 18-year relationship that continues today"],
        "value": "A practice that grew from a single on-premises data center to a modern, cloud-based firm without changing technology partners, under a premium security posture around client data.",
        "quote": ("ProLink has been our only IT company for almost 2 decades now, and they continue to excel in providing us with the highest level of safety, security, and service! I can’t recommend them highly enough! As our firm has steadily grown to almost 30 people, Prolink has adapted and grown, too, to meet our ever-increasing challenges!",
                  "Alan B. Snitzer, Esq.", "Principal Attorney · Google review"),
        "photo": ("/assets/photos/web/law-office-visit-972.webp", "/assets/photos/web/law-office-visit-720.webp 720w, /assets/photos/web/law-office-visit-972.webp 972w", 972, 720,
                  "A Pro Link Systems technician reviewing a document with a staff member in a law office"),
    },
    {
        "slug": "waverly-school", "client": "The Waverly School", "sector": "Independent K–12 education", "current": True,
        "status": "Current client for about 23 years", "flags": [],
        "title": "The Waverly School Case Study: 23 Years | Pro Link",
        "meta": "How Pro Link Systems has served as The Waverly School's outsourced IT department for about 23 years, including Google Workspace for staff and students.",
        "h1": "Twenty-three years as a school’s outsourced IT department.",
        "card": "The school’s outsourced IT department, including Google Workspace for staff and student accounts.",
        "plate": ("23 yrs", "as the school’s outsourced IT department"),
        "summary": "For about 23 years, Pro Link Systems has served as the outsourced IT department of The Waverly School, an independent K–12 school in Pasadena, including management and support of the Google Workspace environment that covers both staff and student accounts.",
        "metrics": [("23 yrs", "as the outsourced IT department"), ("Staff + students", "Google Workspace accounts managed")],
        "snapshot": [("Industry", "Independent K–12 education"), ("Location", "Pasadena, California"), ("Size", "60 staff"),
                     ("Relationship", None), ("Scope", "Outsourced IT department, Google Workspace management")],
        "relationship": "Client for about 23 years",
        "challenge": "A school’s technology has to serve two very different populations at once: staff who depend on reliable administrative systems, and students who hold their own accounts. The environment has to be secure, easy to administer and dependable across the school year, without a large in-house IT team to run it.",
        "approach": ["Pro Link acts as The Waverly School’s outsourced IT department",
                     "Management and support of the school’s Google Workspace environment, covering both staff and student accounts"],
        "outcomes": ["A relationship of about 23 years, among Pro Link’s longest-tenured"],
        "value": "A dependable technology environment for staff and students, run by the same outside partner for more than two decades.",
        "photo": ("/assets/photos/web/school-outdoor-meeting-1100.webp", "/assets/photos/web/school-outdoor-meeting-720.webp 720w, /assets/photos/web/school-outdoor-meeting-1100.webp 1100w", 1100, 619,
                  "Four people talking on a school lawn"),
    },
    {
        "slug": "cookes-crating", "client": "Cooke’s Crating", "sector": "Fine-art logistics", "current": True,
        "status": "Current client for 3+ years", "flags": ["R6"],
        "title": "Cooke's Crating Case Study: 5-Day Migration | Pro Link",
        "meta": "How Pro Link Systems moved Cooke's Crating off a former provider's locked infrastructure in five days, with zero downtime, and modernized it.",
        "h1": "Regaining control of a locked-out business in five days, with zero downtime.",
        "card": "An emergency migration off a former provider’s locked infrastructure, completed in five days.",
        "plate": ("5 days", "full migration, with zero downtime"),
        "summary": "Cooke’s Crating, a Los Angeles fine-art crating and logistics company, came to Pro Link Systems after its previous IT provider locked it out of its entire infrastructure, down to phone management. We migrated the whole environment onto new infrastructure in five days with zero downtime, modernized it, and have supported the company for more than three years since.",
        "metrics": [("5 days", "full environment migration"), ("Zero", "downtime during the cutover"), ("3+ yrs", "client since")],
        "snapshot": [("Industry", "Fine-art crating, shipping and logistics"), ("Location", "Los Angeles, California"),
                     ("Size", "33 employees"), ("Relationship", None), ("Scope", "Emergency migration, infrastructure modernization, security")],
        "relationship": "Client for more than 3 years",
        "challenge": "Cooke’s Crating came to Pro Link in a worst-case situation. A dispute with its previous IT provider had escalated until that provider locked the company out of its entire infrastructure, down to its phone management. It needed to regain control fast, without operations grinding to a halt.",
        "approach": ["An emergency migration of the entire environment onto new infrastructure designed by Pro Link",
                     "A full modernization of aging infrastructure, including an upgraded FileMaker environment",
                     "Current security frameworks rolled out across the new environment",
                     "Control regained over every system, including phone management"],
        "outcomes": ["Migration completed in five days, with zero downtime during the cutover",
                     "Full ownership and control of its infrastructure", "A client for more than three years since"],
        "value": "Full ownership and control of its own infrastructure, on a modernized environment secured with current security frameworks.",
    },
    {
        "slug": "crr", "client": "CR&R Incorporated", "sector": "Environmental services", "current": False,
        "status": "Past engagement, 2023–2025", "flags": ["R3 · separate approval"], "noindex": True,
        "title": "CR&R Case Study: De Facto CIO | Pro Link Systems",
        "meta": "How Pro Link Systems served as de facto CIO for CR&R Incorporated, unifying cybersecurity, cloud and network standards across its divisions.",
        "h1": "Acting as de facto CIO to unify a multi-division enterprise.",
        "card": "De facto CIO for a multi-division environmental services company.",
        "plate": ("450", "employees across divisions"),
        "summary": "From December 2023 to April 2025, Pro Link Systems served as de facto CIO for CR&R Incorporated, a Southern California waste collection, recycling and environmental services company with divisions including Haulaway and Recycle America, bringing consistent cybersecurity, cloud and network standards to an IT environment that had grown fragmented.",
        "metrics": [("450", "employees across divisions"), ("SOC + SIEM", "SentinelOne monitoring deployed")],
        "snapshot": [("Industry", "Waste collection, recycling and environmental services"),
                     ("Location", "Southern California; multi-division, multi-site"), ("Size", "450 employees"), ("Relationship", None),
                     ("Scope", "De facto CIO, cybersecurity, Microsoft 365 and Azure, network architecture, disaster recovery")],
        "relationship": "December 2023 – April 2025",
        "challenge": "CR&R operates across multiple divisions and subsidiaries, including Haulaway and Recycle America, and needed to modernize and unify an IT environment that had grown fragmented. It needed one partner to act as its de facto CIO and bring consistent cybersecurity, cloud and network standards to the whole organization.",
        "approach": ["Advanced cybersecurity deployment, including SentinelOne SOC and SIEM monitoring",
                     "Microsoft 365 and Azure integration, with a secure cloud migration", "Network architecture across divisions",
                     "Disaster-recovery automation", "Strategic vendor alignment across subsidiaries", "Ongoing systems administration"],
        "outcomes": ["One of Pro Link’s most comprehensive technology transformations",
                     "Greater efficiency, visibility and resilience across the company"],
        "value": "Consistent standards across divisions that had grown apart, delivered through a single accountable technology leader.",
    },
]
FEATURED = ["global-holdings", "cunico", "lisi-aerospace", "snitzer-law", "waverly-school", "cookes-crating"]
BY = {c["slug"]: c for c in CASES}


def status_html(c):
    cls = "pl-status is-current" if c["current"] else "pl-status"
    word = "Current" if c["current"] else "Past engagement"
    return '<span class="%s">%s</span> %s' % (cls, word, E(c["relationship"]))


def flags_html(c):
    return "".join('<p class="pl-flag-note"><span class="pl-flag">Review %s</span></p>' % E(r) for r in c["flags"])


def card(c, level="h3"):
    plate_n, plate_l = c["plate"]
    status = ("Current client" if c["current"] else c["status"].replace("Past engagement, ", ""))
    flag = "".join(" " + FLAG(E(r)) for r in c["flags"]) if c.get("noindex") else ""
    return ('<a class="pl-ccard" id="%s" href="/case-studies/%s">\n'
            '  <span class="pl-ccard-plate"><span class="pl-ccard-metric">%s</span><span>%s</span></span>\n'
            '  <span class="pl-case-sector">%s &middot; %s%s</span>\n'
            '  <%s>%s</%s>\n  <p>%s</p>\n  <span class="pl-arrow">Read the case study</span>\n</a>'
            % (c["slug"], c["slug"], E(plate_n), E(plate_l), E(c["sector"]), E(status), flag, level, E(c["h1"]), level, E(c["card"])))


def head_for(c, tracking):
    url = "%s/case-studies/%s" % (SITE, c["slug"])
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Client Success Stories", "item": SITE + "/case-studies"},
        {"@type": "ListItem", "position": 3, "name": c["client"], "item": url}]}
    page = {"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#webpage", "url": url,
            "name": c["title"], "description": c["meta"], "isPartOf": {"@id": SITE + "/#website"},
            "about": {"@type": "Organization", "name": c["client"]},
            "publisher": {"@type": "Organization", "name": "Pro Link Systems", "url": SITE}}
    robots = "noindex, nofollow" if c.get("noindex") else "index, follow"
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            + tracking +
            "<title>%s</title>\n<meta name=\"description\" content=\"%s\">\n<meta name=\"robots\" content=\"%s\">\n"
            "<link rel=\"canonical\" href=\"%s\">\n"
            "<meta property=\"og:type\" content=\"article\">\n<meta property=\"og:url\" content=\"%s\">\n"
            "<meta property=\"og:title\" content=\"%s\">\n<meta property=\"og:description\" content=\"%s\">\n"
            "<meta property=\"og:image\" content=\"%s/og/homepage.png\">\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n"
            "<link rel=\"icon\" type=\"image/x-icon\" href=\"/favicon.ico\">\n"
            "<link rel=\"icon\" type=\"image/png\" sizes=\"32x32\" href=\"/favicon-32.png\">\n"
            "<link rel=\"apple-touch-icon\" sizes=\"180x180\" href=\"/apple-touch-icon.png\">\n"
            "<link rel=\"stylesheet\" href=\"/_shared.css?v=20261120\">\n"
            "<script type=\"application/ld+json\">\n%s\n</script>\n<script type=\"application/ld+json\">\n%s\n</script>\n</head>\n"
            % (E(c["title"]), A(c["meta"]), robots, url, url, A(c["title"]), A(c["meta"]), SITE,
               json.dumps(crumbs, ensure_ascii=False), json.dumps(page, ensure_ascii=False)))


def detail_main(c):
    metrics = "".join('<div><strong>%s</strong><span>%s</span></div>' % (E(n), E(l)) for n, l in c["metrics"])
    snap = []
    for k, v in c["snapshot"]:
        snap.append("<dt>%s</dt><dd>%s</dd>" % (E(k), status_html(c) if k == "Relationship" else E(v)))
    body = ['<p class="pl-case-sector">%s &middot; %s</p>' % (E(c["sector"]), E(c["status"])),
            "<h3>The challenge</h3>", "<p>%s</p>" % E(c["challenge"])]
    if c.get("complexity"):
        body += ["<h3>Complexity</h3>", "<p>%s</p>" % E(c["complexity"])]
    body += ["<h3>Our approach</h3>", '<ul class="pl-checks">%s</ul>' % "".join("<li>%s</li>" % E(x) for x in c["approach"]),
             "<h3>Outcomes</h3>", '<ul class="pl-checks">%s</ul>' % "".join(
                 "<li>%s</li>" % (x if "pl-flag" in x else E(x)) for x in c["outcomes"]),
             "<h3>Long-term value</h3>", "<p>%s</p>" % E(c["value"])]
    if c.get("quote"):
        q, who, role = c["quote"]
        body.append('<figure class="pl-quote pl-quote--inline"><blockquote>&ldquo;%s&rdquo;</blockquote>'
                    '<figcaption><strong>%s</strong> &middot; %s</figcaption></figure>' % (E(q), E(who), E(role)))
    if c.get("photo"):
        src, srcset, w, h, alt = c["photo"]
        body.append('<figure class="pl-case-photo"><img src="%s" srcset="%s" sizes="(max-width: 1024px) 92vw, 760px" '
                    'width="%d" height="%d" loading="lazy" decoding="async" alt="%s"></figure>' % (src, srcset, w, h, A(alt)))
    related = [BY[s] for s in FEATURED if s != c["slug"]][:3]
    n = len(c["metrics"])
    return ('<main>\n\n<section class="pl-casehead" aria-labelledby="page-h1">\n  <div class="pl-wrap">\n'
            '    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/case-studies">Client Success</a><span>/</span>%s</nav>\n'
            '    <p class="pl-eyebrow">%s &middot; %s</p>\n'
            '    <h1 class="pl-h1" id="page-h1">%s</h1>\n'
            '    <p class="pl-lead"><b>Executive summary</b>%s</p>\n'
            '    <div class="pl-cmetrics" style="--n:%d">%s</div>\n  </div>\n</section>\n\n'
            '<section class="pl-section" aria-label="Case study detail">\n  <div class="pl-wrap">\n'
            '    <article class="pl-study">\n      <aside class="pl-study-meta">\n        <p class="pl-study-client">%s</p>\n'
            '        <dl>%s</dl>\n        %s\n      </aside>\n      <div class="pl-study-body">\n        %s\n      </div>\n'
            '    </article>\n  </div>\n</section>\n\n'
            '<section class="pl-section pl-mist" aria-labelledby="related-h">\n  <div class="pl-wrap">\n'
            '    <div class="pl-head"><div><p class="pl-eyebrow">More client success</p><h2 class="pl-h2" id="related-h">Related engagements.</h2></div>'
            '<p class="pl-lead"><a class="pl-arrow" href="/case-studies">All client stories</a></p></div>\n'
            '    <div class="pl-related">\n%s\n    </div>\n  </div>\n</section>\n\n'
            '<section class="pl-cta" aria-labelledby="cta-heading">\n  <div class="pl-wrap">\n'
            '    <div><p class="pl-eyebrow">Next step</p><h2 class="pl-h2" id="cta-heading">Facing a similar challenge?</h2></div>\n'
            '    <div><p>Tell us about your environment and what you need it to do. We&rsquo;ll review it with you and outline practical next steps.</p>\n'
            '      <div class="pl-actions"><a href="/contact" class="btn btn-light">Schedule a Technology Consultation</a>'
            '<a href="/services" class="btn btn-outline-white">Explore Our Capabilities</a></div></div>\n  </div>\n</section>\n\n</main>'
            % (E(c["client"]), E(c["sector"]), E(c["status"]), E(c["h1"]), E(c["summary"]), n, metrics,
               E(c["client"]), "".join(snap), flags_html(c), "\n        ".join(body),
               "\n".join(card(r) for r in related)))


def hub_main():
    featured = "\n".join(card(BY[s], "h2") for s in FEATURED)
    crr = card(BY["crr"], "h2")
    return ('''<main>

<section class="pl-pagehead" aria-labelledby="page-h1">
  <div class="pl-wrap">
    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span>Client Success</nav>
    <h1 class="pl-h1" id="page-h1">Long partnerships with organizations that depend on technology.</h1>
    <p class="pl-lead">Representative engagements from more than 25 years of managing, securing and modernizing technology. Each story notes whether the relationship is current or a past engagement.</p>
  </div>
</section>

<section class="pl-section--tight pl-dark" aria-label="Relationship tenure">
  <div class="pl-wrap">
    <div class="pl-figures">
      <div class="pl-figure"><strong>23 yrs</strong><span>The Waverly School</span><small>Current client</small></div>
      <div class="pl-figure"><strong>18 yrs</strong><span>Law Offices of Alan B. Snitzer</span><small>Current client</small></div>
      <div class="pl-figure"><strong>13+ yrs</strong><span>Cunico Corp.</span><small>Current client, since 2012</small></div>
      <div class="pl-figure"><strong>12+ yrs</strong><span>Global Holdings</span><small>Past engagement, to 2021</small></div>
    </div>
  </div>
</section>

<section class="pl-section" aria-labelledby="featured-h">
  <div class="pl-wrap">
    <div class="pl-head">
      <div><p class="pl-eyebrow">Case studies</p><h2 class="pl-h2" id="featured-h">Engineering, infrastructure and long-term leadership.</h2></div>
      <p class="pl-lead">Each case study has an executive summary, the complexity involved, our approach and the outcomes.</p>
    </div>
    <div class="pl-ccards">
%s
    </div>
  </div>
</section>

<section class="pl-section pl-mist" aria-labelledby="more-h">
  <div class="pl-wrap">
    <div class="pl-head">
      <div><p class="pl-eyebrow">More engagements</p><h2 class="pl-h2" id="more-h">Other organizations we support and have supported.</h2></div>
      <p class="pl-lead">Optical Zonu, a photonics manufacturer, relies on Pro Link as its primary IT management team, including domain and DNS management. <span class="pl-flag">Review R10</span></p>
    </div>
    <div class="pl-ccards" style="margin-bottom:56px">
%s
    </div>
    <p class="pl-flag-note"><span class="pl-flag">Review R7</span></p>
    <table class="pl-table">
      <thead><tr><th scope="col">Client</th><th scope="col">Sector</th><th scope="col">Engagement</th><th scope="col">Highlights</th></tr></thead>
      <tbody>
        <tr><td>FSC Lighting</td><td>Lighting manufacturing, Rancho Cucamonga</td><td>2020&ndash;2024</td><td>Network overhaul across offices and production facilities; cloud systems; centralized data management</td></tr>
        <tr><td>Fralock Holdings</td><td>Advanced materials and precision manufacturing, multi-state</td><td>2022&ndash;2023</td><td>Network restructuring, security and IT operations standardized across states and newly acquired subsidiaries</td></tr>
        <tr><td>Hallmark Lighting</td><td>Lighting design, California and an overseas plant</td><td>2018&ndash;2020</td><td>IT rebuilt from the ground up, connecting California teams with overseas manufacturing</td></tr>
        <tr><td>M13</td><td>Venture firm, Los Angeles</td><td>2017&ndash;2018</td><td>Founding technology platform</td></tr>
        <tr><td>VEEV Spirits</td><td>Spirits, Beverly Hills to multi-state</td><td>2006&ndash;2013</td><td>About seven years of growth, through a sale to new ownership</td></tr>
        <tr><td>Global Garden</td><td>Torrance</td><td>Ongoing</td><td>Email security across the organization&rsquo;s mailboxes</td></tr>
      </tbody>
    </table>
  </div>
</section>

<section class="pl-section pl-dark" id="stories" aria-labelledby="stories-h">
  <div class="pl-wrap">
    <div class="pl-head">
      <div><p class="pl-eyebrow">In their own words</p><h2 class="pl-h2" id="stories-h">Hear it from our clients.</h2></div>
      <p class="pl-lead">Three long-standing clients on what the partnership means. <a class="pl-arrow" href="https://share.google/ab8YpK16DxCYbt1Hd" target="_blank" rel="noopener">Read our Google reviews</a></p>
    </div>
    <div class="pl-video">
      <div class="pl-video-frame">
        <video id="pl-video" controls playsinline preload="none" poster="/assets/video/oz-poster.webp" aria-label="Client video">
          <source src="https://videos.prolinksystems.com/oz.mp4" type="video/mp4">
        </video>
      </div>
      <ul class="pl-video-list">
        <li><button type="button" class="is-active" data-src="https://videos.prolinksystems.com/oz.mp4" data-poster="/assets/video/oz-poster.webp"><span>Client</span>Optical Zonu</button></li>
        <li><button type="button" data-src="https://videos.prolinksystems.com/snitzer.mp4" data-poster="/assets/video/snitzer-poster.webp"><span>Client</span>Law Offices of Alan B. Snitzer</button></li>
        <li><button type="button" data-src="https://videos.prolinksystems.com/waverly.mp4" data-poster="/assets/video/waverly-poster.webp"><span>Client</span>The Waverly School</button></li>
        <li><button type="button" data-src="https://videos.prolinksystems.com/pls.mp4" data-poster="/assets/video/pls-poster.webp"><span>Our story</span>Pro Link Systems: who we are</button></li>
      </ul>
    </div>
  </div>
</section>

<section class="pl-cta" aria-labelledby="cta-heading">
  <div class="pl-wrap">
    <div><p class="pl-eyebrow">Next step</p><h2 class="pl-h2" id="cta-heading">Start a partnership built to last.</h2></div>
    <div>
      <p>Tell us about your organization and where technology is holding it back. We&rsquo;ll review your environment and outline practical next steps.</p>
      <div class="pl-actions"><a href="/contact" class="btn btn-light">Schedule a Technology Consultation</a><a href="/services" class="btn btn-outline-white">Explore Our Capabilities</a></div>
    </div>
  </div>
</section>

</main>''' % (featured, crr))


def main():
    hub_path = os.path.join(ROOT, "case-studies.html")
    hub = io.open(hub_path, encoding="utf-8", newline="").read()
    crlf = "\r\n" in hub
    h = hub.replace("\r\n", "\n")
    head = h[:h.index("</head>")]
    tracking = "".join(m.group(0) + "\n" for m in re.finditer(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>", head, re.S))
    assert "googletagmanager.com/gtag/js" in tracking and "bat.bing.net" in tracking, "tracking scripts not found in hub head"

    os.makedirs(os.path.join(ROOT, "case-studies"), exist_ok=True)
    for c in CASES:
        assert len(html.unescape(c["title"])) <= 60, ("title too long", c["slug"])
        assert len(c["meta"]) <= 160, ("meta too long", c["slug"], len(c["meta"]))
        page = head_for(c, tracking) + ("<body>\n\n<!-- PL:HEADER -->\n<!-- /PL:HEADER -->\n\n" + detail_main(c) +
                                        "\n\n<!-- PL:FOOTER -->\n<!-- /PL:FOOTER -->\n\n</body>\n</html>\n")
        path = os.path.join(ROOT, "case-studies", c["slug"] + ".html")
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old is not None and "<!-- /PL:HEADER -->" in old:   # keep already-applied chrome; apply_chrome refreshes it
            hdr = re.search(r"<!-- PL:HEADER -->.*?<!-- /PL:HEADER -->", old, re.S).group(0)
            ftr = re.search(r"<!-- PL:FOOTER -->.*?<!-- /PL:FOOTER -->", old, re.S).group(0)
            page = page.replace("<!-- PL:HEADER -->\n<!-- /PL:HEADER -->", hdr).replace("<!-- PL:FOOTER -->\n<!-- /PL:FOOTER -->", ftr)
        io.open(path, "w", encoding="utf-8", newline="\n").write(page)

    m = re.search(r"<main>.*?</main>", h, re.S)
    h = h[:m.start()] + hub_main() + h[m.end():]
    if crlf:
        h = h.replace("\n", "\r\n")
    io.open(hub_path, "w", encoding="utf-8", newline="").write(h)

    sm_path = os.path.join(ROOT, "sitemap.xml")
    sm = io.open(sm_path, encoding="utf-8", newline="").read()
    added = []
    for c in CASES:
        loc = "%s/case-studies/%s" % (SITE, c["slug"])
        if c.get("noindex") or ("<loc>%s</loc>" % loc) in sm:
            continue
        entry = ("  <url>\n    <loc>%s</loc>\n    <lastmod>2026-11-21</lastmod>\n    <changefreq>monthly</changefreq>\n"
                 "    <priority>0.6</priority>\n  </url>\n" % loc)
        nl = "\r\n" if "\r\n" in sm else "\n"
        sm = sm.replace("</urlset>", entry.replace("\n", nl) + "</urlset>")
        added.append(c["slug"])
    io.open(sm_path, "w", encoding="utf-8", newline="").write(sm)
    print("built %d case pages + hub; sitemap added: %s" % (len(CASES), ", ".join(added) or "none"))


if __name__ == "__main__":
    main()
