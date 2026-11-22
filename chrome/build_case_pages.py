#!/usr/bin/env python3
"""
chrome/build_case_pages.py -- build the Client Success hub (case-studies.html: the client portfolio) and one page per
case study (case-studies/<slug>.html) from the CASES data below. Facts come only from the case-study source files and
editorial/verified_facts.json; anything awaiting Brian's decision carries a neutral "Review R#" marker. Company names,
industry classifications, company profiles and the portfolio order come from editorial/clients.json (chrome/clients.py).

    python chrome/build_case_pages.py      # then: python chrome/apply_chrome.py

- Detail pages copy the tracking scripts from case-studies.html's <head>, get their own title, description,
  canonical, Open Graph and JSON-LD (BreadcrumbList + WebPage), and empty PL:HEADER / PL:FOOTER markers that
  apply_chrome.py fills.
- Cases with "noindex": True (pending a separate approval) get robots noindex and stay out of the sitemap.
- Indexable detail pages are added to sitemap.xml once (idempotent).
- The hub keeps its URL, title, description, canonical and JSON-LD; only its <main> is regenerated.
- The featured clients on index.html are refreshed too (clients.write_home()).
"""
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://prolinksystems.com"
E = lambda s: html.escape(s, quote=False)
A = lambda s: html.escape(s, quote=True)
# the site-wide ?v= of _shared.css, read from the home page so this builder never carries its own copy
CSS_V = re.search(r'_shared\.css\?v=([^"]+)"', io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()).group(1)
FLAG = lambda r: '<span class="pl-flag">Review %s</span>' % r
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clients as CL  # noqa: E402

DATA = CL.load()

CASES = [
    {
        "slug": "global-holdings",
        "status": "Historical client, 12+ years to 2021", "flags": ["R4"],
        "title": "Global Holdings: Imaging Network | Pro Link Systems",
        "meta": "How Pro Link Systems designed and ran the network, AWS imaging platform and patient portal behind 19 diagnostic imaging facilities for 12+ years.",
        "h1": "A secure imaging backbone for 19 facilities and hundreds of partner sites.",
        "card": "Network, AWS imaging platform and secure portal for a regional diagnostic imaging provider.",
        "plate": ("19", "owned facilities on one network and imaging platform"),
        "summary": "For more than 12 years, to 2021, Pro Link Systems designed and operated the technology behind Global Holdings, a Southern California diagnostic imaging provider focused on MRI and CT. We built the network across its 19 owned facilities, consolidated imaging studies from every modality into an AWS environment we architected and managed, and ran a secure portal for referring doctors and patients.",
        "metrics": [("19", "owned facilities on one network"), ("Hundreds", "of partner facilities sending studies to the same platform"),
                    ("Thousands", "of imaging studies handled each month"), ("12+ yrs", "engagement, to 2021")],
        "snapshot": [("Location", "Southern California; 19 owned facilities and a referral network of hundreds of partner facilities"),
                     ("Size", "200+ employees"), ("Relationship", None),
                     ("Scope", "Network design, AWS cloud architecture, imaging (DICOM) workflows, secure patient portal, security")],
        "relationship": "More than 12 years, ending in 2021",
        "challenge": "Global Holdings ran 19 owned imaging facilities and referred patients to hundreds of partner facilities owned by other medical groups. Studies produced on many modalities, in many locations and under many ownership arrangements all had to reach one place for processing and clinician access.",
        "complexity": "This was protected health information, in an industry that has seen repeated, high-profile breaches. Patient records and imaging data needed airtight security and privacy, while referring doctors and patients needed convenient, appropriate access to studies. Sites averaged about five imaging modalities each.",
        "approach": ["A network designed from the ground up across all 19 owned facilities",
                     "DICOM ingestion from every modality at every location",
                     "A cloud environment on AWS, architected and managed by Pro Link Systems, consolidating imagery for processing and access",
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
        "slug": "cunico",
        "status": "Current client since 2012", "flags": ["R1"],
        "title": "Cunico Case Study: 13-Year IT Partnership | Pro Link Systems",
        "meta": "How Pro Link Systems has run and secured Cunico's multi-site technology since 2012, through growth and its 2022 acquisition by BWX Technologies.",
        "h1": "Thirteen years of technology governance, through growth and an acquisition.",
        "card": "Multi-site environments, hardened security and support through an acquisition by BWX Technologies.",
        "plate": ("13+ yrs", "continuously renewed partnership, since 2012"),
        "summary": "Since 2012, Pro Link Systems has been the outsourced IT and technology-governance partner for Cunico, a precision manufacturer with a legacy of more than 70 years. We maintain its on-premises and cloud environments across multiple sites, hardened its security with continuous monitoring, and supported its integration into BWX Technologies after the 2022 acquisition.",
        "metrics": [("13+ yrs", "continuously renewed partnership, since 2012"), ("Multi-site", "on-premises and cloud environments"),
                    ("2022", "integration into BWX Technologies")],
        "snapshot": [("Location", "Long Beach, California; multiple sites"), ("Size", "35 employees"), ("Relationship", None),
                     ("Scope", "Managed IT, cybersecurity, cloud, backup and disaster recovery, technology governance")],
        "relationship": "Since May 2012",
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
        "slug": "lisi-aerospace",
        "status": "Past engagement, 2019–2021", "flags": ["R2"],
        "title": "LISI Aerospace Case Study: IT Stabilized | Pro Link Systems",
        "meta": "How Pro Link Systems took ownership of LISI Aerospace's IT administration and stabilized operations within 90 days, through the move to remote work.",
        "h1": "Bringing order to a multinational manufacturer’s IT within 90 days.",
        "card": "IT administration taken over and stabilized within 90 days, then carried through the move to remote work.",
        "plate": ("90 days", "to stabilized IT operations"),
        "summary": "From October 2019 to August 2021, Pro Link Systems took ownership of IT administration for LISI Aerospace, a 700-person aerospace fastener manufacturer with its main plant in Torrance and facilities across North America. Operations stabilized within 90 days, and the environment stayed resilient through the move to remote work.",
        "metrics": [("90 days", "to stabilized operations"), ("700", "employees"), ("3 sites", "in Southern California managed by Pro Link Systems")],
        "snapshot": [("Location", "Main plant in Torrance, California, with facilities in Canada, Mexico and elsewhere in North America"),
                     ("Size", "700 employees"), ("Relationship", None),
                     ("Scope", "IT administration, network modernization, security agents, remote work")],
        "relationship": "October 2019 – August 2021",
        "challenge": "LISI Aerospace asked Pro Link Systems to bring order to a disordered IT environment spanning its Torrance main plant and facilities across North America, and to take ownership of its IT administrative infrastructure: hosts, virtual machines, communication systems (voice, email and messaging) and security policies. The engagement would soon include the operational pressures of the COVID-19 pandemic.",
        "approach": ["A comprehensive IT management system", "A modernized network topology",
                     "Security agents deployed across the environment",
                     "Additional IT staff onboarded across California and eventually Canada",
                     "A transition to remote-work solutions during the pandemic"],
        "outcomes": ["Operations stabilized within 90 days of the engagement",
                     "Three Southern California sites managed by Pro Link Systems",
                     "Continuity maintained through the move to remote work"],
        "value": "A comprehensive IT management system that carried a multinational manufacturer through the operational shock of 2020 without losing continuity.",
    },
    {
        "slug": "snitzer-law",
        "status": "Current client for 18 years", "flags": [],
        "title": "Law Firm Case Study: 18 Years, Azure | Pro Link Systems",
        "meta": "How Pro Link Systems moved the Law Offices of Alan B. Snitzer from an on-premises data center to Microsoft Azure over an 18-year partnership.",
        "h1": "From an on-premises data center to Azure, across 18 years of growth.",
        "card": "From a data center in the firm’s own office to Microsoft Azure, with every office move handled.",
        "plate": ("90%+", "of the firm’s environment now on Microsoft Azure"),
        "summary": "For 18 years, Pro Link Systems has been the only IT company for the Law Offices of Alan B. Snitzer in Pasadena. We have carried the firm from a data center in its own office to the cloud, where over 90% of its environment now runs on Microsoft Azure, and handled the infrastructure for its office moves along the way.",
        "metrics": [("18 yrs", "partnership that continues today"), ("90%+", "of the environment on Microsoft Azure"),
                    ("Multiple", "office relocations, infrastructure moved by Pro Link Systems")],
        "snapshot": [("Location", "Pasadena, California"), ("Relationship", None),
                     ("Scope", "Managed IT, cloud migration to Microsoft Azure, security, office relocations")],
        "relationship": "For 18 years",
        "challenge": "The firm’s environment started entirely on premises, in a data center at its own office. As the practice grew, so did the demands on that infrastructure: more staff, more data, higher security expectations and a series of office relocations, each of which meant moving critical systems without disrupting the firm’s work or its confidentiality obligations.",
        "approach": ["Many migrations and upgrades across the entire environment as the practice scaled",
                     "A move from the on-premises data center to the cloud: today, over 90% of the firm’s environment runs on Microsoft Azure",
                     "A premium security umbrella around the firm’s data, appropriate to a law practice’s confidentiality obligations",
                     "The infrastructure move handled for each office relocation"],
        "outcomes": ["Over 90% of the environment running on Azure",
                     "Multiple office relocations completed with Pro Link Systems managing the infrastructure",
                     "An 18-year relationship that continues today"],
        "value": "A practice that grew from a single on-premises data center to a modern, cloud-based firm without changing technology partners, under a premium security posture around client data.",
        "quote": ("ProLink has been our only IT company for almost 2 decades now, and they continue to excel in providing us with the highest level of safety, security, and service! I can’t recommend them highly enough! As our firm has steadily grown to almost 30 people, Prolink has adapted and grown, too, to meet our ever-increasing challenges!",
                  "Alan B. Snitzer, Esq.", "Principal Attorney · Google review"),
        "photo": ("/assets/photos/web/law-office-visit-972.webp", "/assets/photos/web/law-office-visit-720.webp 720w, /assets/photos/web/law-office-visit-972.webp 972w", 972, 720,
                  "A Pro Link Systems technician reviewing a document with a staff member in a law office"),
    },
    {
        "slug": "waverly-school",
        "status": "Current client for about 23 years", "flags": [],
        "title": "The Waverly School Case Study: 23 Years | Pro Link Systems",
        "meta": "How Pro Link Systems has served as The Waverly School's outsourced IT department for about 23 years, including Google Workspace for staff and students.",
        "h1": "Twenty-three years as a school’s outsourced IT department.",
        "card": "The school’s outsourced IT department, including Google Workspace for staff and student accounts.",
        "plate": ("23 yrs", "as the school’s outsourced IT department"),
        "summary": "For about 23 years, Pro Link Systems has served as the outsourced IT department of The Waverly School, an independent K–12 school in Pasadena, including management and support of the Google Workspace environment that covers both staff and student accounts.",
        "metrics": [("23 yrs", "as the outsourced IT department"), ("Staff + students", "Google Workspace accounts managed")],
        "snapshot": [("Location", "Pasadena, California"), ("Size", "60 staff"),
                     ("Relationship", None), ("Scope", "Outsourced IT department, Google Workspace management")],
        "relationship": "For about 23 years",
        "challenge": "A school’s technology has to serve two very different populations at once: staff who depend on reliable administrative systems, and students who hold their own accounts. The environment has to be secure, easy to administer and dependable across the school year, without a large in-house IT team to run it.",
        "approach": ["Pro Link Systems acts as The Waverly School’s outsourced IT department",
                     "Management and support of the school’s Google Workspace environment, covering both staff and student accounts"],
        "outcomes": ["A relationship of about 23 years, among Pro Link Systems’ longest-tenured"],
        "value": "A dependable technology environment for staff and students, run by the same outside partner for more than two decades.",
        "photo": ("/assets/photos/web/school-outdoor-meeting-1100.webp", "/assets/photos/web/school-outdoor-meeting-720.webp 720w, /assets/photos/web/school-outdoor-meeting-1100.webp 1100w", 1100, 619,
                  "Four people talking on a school lawn"),
    },
    {
        "slug": "cookes-crating",
        "status": "Current client for 3+ years", "flags": ["R6"],
        "title": "Cooke's Crating: 5-Day Migration | Pro Link Systems",
        "meta": "How Pro Link Systems moved Cooke's Crating off a former provider's locked infrastructure in five days, with zero downtime, and modernized it.",
        "h1": "Regaining control of a locked-out business in five days, with zero downtime.",
        "card": "An emergency migration off a former provider’s locked infrastructure, completed in five days.",
        "plate": ("5 days", "full migration, with zero downtime"),
        "summary": "Cooke’s Crating, a Los Angeles fine-art crating and logistics company, came to Pro Link Systems after its previous IT provider locked it out of its entire infrastructure, down to phone management. We migrated the whole environment onto new infrastructure in five days with zero downtime, modernized it, and have supported the company for more than three years since.",
        "metrics": [("5 days", "full environment migration"), ("Zero", "downtime during the cutover"), ("3+ yrs", "client since")],
        "snapshot": [("Location", "Los Angeles, California"),
                     ("Size", "33 employees"), ("Relationship", None), ("Scope", "Emergency migration, infrastructure modernization, security")],
        "relationship": "For more than 3 years",
        "challenge": "Cooke’s Crating came to Pro Link Systems in a worst-case situation. A dispute with its previous IT provider had escalated until that provider locked the company out of its entire infrastructure, down to its phone management. It needed to regain control fast, without operations grinding to a halt.",
        "approach": ["An emergency migration of the entire environment onto new infrastructure designed by Pro Link Systems",
                     "A full modernization of aging infrastructure, including an upgraded FileMaker environment",
                     "Current security frameworks rolled out across the new environment",
                     "Control regained over every system, including phone management"],
        "outcomes": ["Migration completed in five days, with zero downtime during the cutover",
                     "Full ownership and control of its infrastructure", "A client for more than three years since"],
        "value": "Full ownership and control of its own infrastructure, on a modernized environment secured with current security frameworks.",
    },
    {
        "slug": "crr",
        "status": "Historical client, 2023–2025", "flags": ["R3 · separate approval"], "noindex": True,
        "title": "CR&R Case Study: De Facto CIO | Pro Link Systems",
        "meta": "How Pro Link Systems served as de facto CIO for CR&R, unifying cybersecurity, cloud and network standards across its divisions.",
        "h1": "Acting as de facto CIO to unify a multi-division enterprise.",
        "card": "De facto CIO for a multi-division environmental services company.",
        "plate": ("450", "employees across divisions"),
        "summary": "From December 2023 to April 2025, Pro Link Systems served as de facto CIO for CR&R Environmental Services, a Southern California waste collection, recycling and environmental services company with divisions including Haulaway and Recycle America, bringing consistent cybersecurity, cloud and network standards to an IT environment that had grown fragmented.",
        "metrics": [("450", "employees across divisions"), ("SOC + SIEM", "SentinelOne monitoring deployed")],
        "snapshot": [("Location", "Southern California; multi-division, multi-site"), ("Size", "450 employees"), ("Relationship", None),
                     ("Scope", "De facto CIO, cybersecurity, Microsoft 365 and Azure, network architecture, disaster recovery")],
        "relationship": "December 2023 – April 2025",
        "challenge": "CR&R operates across multiple divisions and subsidiaries, including Haulaway and Recycle America, and needed to modernize and unify an IT environment that had grown fragmented. It needed one partner to act as its de facto CIO and bring consistent cybersecurity, cloud and network standards to the whole organization.",
        "approach": ["Advanced cybersecurity deployment, including SentinelOne SOC and SIEM monitoring",
                     "Microsoft 365 and Azure integration, with a secure cloud migration", "Network architecture across divisions",
                     "Disaster-recovery automation", "Strategic vendor alignment across subsidiaries", "Ongoing systems administration"],
        "outcomes": ["One of Pro Link Systems’ most comprehensive technology transformations",
                     "Greater efficiency, visibility and resilience across the company"],
        "value": "Consistent standards across divisions that had grown apart, delivered through a single accountable technology leader.",
    },
    {
        "slug": "fralock",
        "status": "Past engagement, 2022–2023", "flags": ["R7"],
        "title": "Fralock Case Study: Multi-State IT | Pro Link Systems",
        "meta": "How Pro Link Systems unified network, security and IT operations for Fralock Holdings across sites, states and newly acquired subsidiaries.",
        "h1": "One framework for a manufacturer spread across sites, states and acquisitions.",
        "card": "Network, security and IT operations unified across several states and newly acquired subsidiaries.",
        "plate": ("Multi-state", "operations on one network and security framework"),
        "summary": "From January 2022 to July 2023, Pro Link Systems unified and secured the IT infrastructure of Fralock Holdings, an advanced-materials and precision manufacturer of about 350 people whose environment had become fragmented across multiple sites and newly acquired subsidiaries.",
        "metrics": [("350", "employees"), ("Multi-state", "sites and newly acquired subsidiaries"), ("One", "framework for network management and communications")],
        "snapshot": [("Location", "Los Angeles, California; sites in several states"), ("Size", "350 employees"), ("Relationship", None),
                     ("Scope", "Network restructuring, cybersecurity, IT operations, infrastructure for industrial systems")],
        "relationship": "January 2022 – July 2023",
        "challenge": "Fralock asked Pro Link Systems to unify and secure an IT infrastructure that had become fragmented across multiple sites and newly acquired subsidiaries. It needed network management, cybersecurity and IT operations standardized across several states, including the infrastructure behind key workloads and industrial systems in its manufacturing environments.",
        "approach": ["Internal network topology restructured", "Cybersecurity strengthened across the organization’s digital ecosystem",
                     "IT operations standardized across several states",
                     "Network management and communications brought under a single, cohesive framework",
                     "Infrastructure modernized for key workloads and industrial systems in manufacturing"],
        "outcomes": ["A complex, multi-site enterprise under unified, scalable management",
                     "Greater reliability, visibility and scalability across the company"],
        "value": "A rapid transformation: consistent network, security and operating standards across established sites and newly acquired subsidiaries, delivered within a short engagement.",
    },
    {
        "slug": "fsc-lighting",
        "status": "Past engagement, 2020–2024", "flags": ["R7"],
        "title": "FSC Lighting Case Study: IT Overhaul | Pro Link Systems",
        "meta": "How Pro Link Systems overhauled the network behind FSC Lighting's offices and production facilities and moved the manufacturer to cloud systems.",
        "h1": "A scalable technology foundation for a manufacturer in rapid expansion.",
        "card": "A complete network overhaul across offices and production facilities, with secure cloud systems.",
        "plate": ("4+ yrs", "managed IT partnership, 2020 to 2024"),
        "summary": "From March 2020 to August 2024, Pro Link Systems modernized the technology behind FSC Lighting, a Rancho Cucamonga manufacturer of energy-efficient and custom lighting, during a period of rapid expansion.",
        "metrics": [("4+ yrs", "managed IT partnership"), ("45", "employees"), ("Office + plant", "on one overhauled network")],
        "snapshot": [("Location", "Rancho Cucamonga, California"), ("Size", "45 employees"), ("Relationship", None),
                     ("Scope", "Network overhaul, cloud systems, centralized data management, managed IT")],
        "relationship": "March 2020 – August 2024",
        "challenge": "FSC Lighting was expanding rapidly and needed to modernize its IT infrastructure and improve operational efficiency. Communication between departments, spread across offices and production facilities, had to become faster and more reliable, on a technology foundation that could scale with new growth.",
        "approach": ["A complete network overhaul across offices and production facilities", "Secure cloud-based systems",
                     "Centralized data management", "Improved connectivity across engineering, production and sales teams"],
        "outcomes": ["Faster communication between departments", "Streamlined day-to-day operations",
                     "A stable, scalable foundation for FSC Lighting’s continued innovation"],
        "value": "A partnership of more than four years that supported the company’s growth in energy-efficient and custom lighting.",
    },
    {
        "slug": "hallmark-lighting",
        "status": "Past engagement, 2018–2020", "flags": ["R7", "R18"],
        "title": "Hallmark Lighting Case Study | Pro Link Systems",
        "meta": "How Pro Link Systems rebuilt Hallmark Lighting's IT from the ground up, connecting California design teams with an overseas manufacturing plant.",
        "h1": "An IT environment rebuilt to connect design and manufacturing across continents.",
        "card": "IT rebuilt from the ground up, connecting California design teams with an overseas plant.",
        "plate": ("Ground up", "IT environment rebuilt, 2018 to 2020"),
        "summary": "From December 2018 to July 2020, Pro Link Systems rebuilt the IT environment of Hallmark Lighting, a lighting design and manufacturing company with design teams in California and an overseas plant, during a period of rapid market growth.",
        "metrics": [("60", "employees"), ("Ground up", "rebuild of the IT environment"), ("Overseas", "manufacturing connected with California design teams")],
        "snapshot": [("Location", "Design teams in California; overseas manufacturing plant"), ("Size", "60 employees"), ("Relationship", None),
                     ("Scope", "IT rebuild, network modernization, secure and scalable systems")],
        "relationship": "December 2018 – July 2020",
        "challenge": "Hallmark Lighting needed to modernize its technology to support expanding global operations during rapid market growth. With an overseas manufacturing plant and design teams in California, it had to close a communication and workflow gap between continents so teams could collaborate faster and produce more efficiently.",
        "approach": ["A modernized network topology", "Secure, scalable systems",
                     "Communication and workflow connected between the California design teams and the overseas plant"],
        "outcomes": ["Faster collaboration between design and manufacturing", "Reliable performance across all departments",
                     "A technology environment able to meet rising demand"],
        "value": "A trusted industry name equipped to meet rising demand with speed and precision.",
    },
    {
        "slug": "m13",
        "status": "Past engagement, 2017–2018", "flags": ["R7"],
        "title": "M13 Case Study: Founding IT Platform | Pro Link Systems",
        "meta": "How Pro Link Systems helped design and build the founding technology and communications platform for M13, a venture capital firm.",
        "h1": "The founding technology platform for a venture firm.",
        "card": "A flexible, secure technology and communications platform for a growing venture portfolio.",
        "plate": ("Founding", "technology platform for a venture firm"),
        "summary": "In M13’s early days, from June 2017 to March 2018, Pro Link Systems helped design and build the technology platform beneath the firm: an IT and communications framework made to support collaboration, data security and operational scale across a growing venture portfolio.",
        "metrics": [("30", "employees"), ("2017–2018", "engagement"), ("One", "framework for collaboration across early ventures")],
        "snapshot": [("Location", "Los Angeles, California"), ("Size", "30 employees"), ("Relationship", None),
                     ("Scope", "Technology platform design, communications, data security")],
        "relationship": "June 2017 – March 2018",
        "challenge": "M13 needed a flexible, stable technology platform to serve as the foundation for a rapidly growing venture portfolio: an IT and communications framework that would enable collaboration, data security and operational scalability across its early ventures, built right from the start.",
        "approach": ["A flexible, stable technology platform to anchor the venture portfolio",
                     "An IT and communications framework for collaboration across early ventures",
                     "Data security appropriate to a venture organization", "Operational scalability as the portfolio grew"],
        "outcomes": ["The firm’s technical foundation in place in its early days", "A platform built to scale with the portfolio"],
        "value": "A solid technical foundation, laid early, beneath what became a prominent venture firm.",
    },
    {
        "slug": "veev-spirits",
        "status": "Past engagement, 2006–2013", "flags": ["R7", "R16"],
        "title": "VEEV Spirits Case Study: Seven Years | Pro Link Systems",
        "meta": "How Pro Link Systems designed and ran the technology behind VEEV Spirits for about seven years, from the founders' home to a multi-state operation.",
        "h1": "Technology that kept pace from the founders’ home to a multi-state brand.",
        "card": "Technology designed and run from inception through multi-state growth.",
        "plate": ("7 yrs", "from inception to a multi-state operation"),
        "summary": "VEEV Spirits engaged Pro Link Systems at its inception, when the company ran from its founders’ home in Beverly Hills. For about seven years, from July 2006 to September 2013, we designed, implemented and managed its technology as it grew into a multi-state operation.",
        "metrics": [("7 yrs", "engagement, 2006 to 2013"), ("Multi-state", "operation, from a home office"), ("40", "employees")],
        "snapshot": [("Location", "Beverly Hills, California, growing to several states"), ("Size", "40 employees"), ("Relationship", None),
                     ("Scope", "Information technology, communications infrastructure, online presence")],
        "relationship": "July 2006 – September 2013",
        "challenge": "VEEV needed technology that could scale with rapid national expansion. As the brand grew from a home office to a multi-state operation, its IT, communications and online presence had to let the team work without technology becoming a constraint on growth.",
        "approach": ["An information technology environment built from inception and scaled with the business",
                     "Communications infrastructure", "Online presence and web systems",
                     "Ongoing management, so the founders could focus on building the brand"],
        "outcomes": ["A partnership of about seven years, from startup to multi-state operation",
                     "Technology that kept pace with the brand’s growth"],
        "value": "One technology partner from the first day through national expansion, while the founders built the brand.",
    },
    {
        "slug": "optical-zonu",
        "status": "Current client", "flags": ["R10"],
        "title": "Optical Zonu Case Study: Managed IT | Pro Link Systems",
        "meta": "How Pro Link Systems serves as the primary IT management team for Optical Zonu, a fiber-optic and RF-over-fiber manufacturer.",
        "h1": "One accountable IT team for a photonics manufacturer.",
        "card": "Primary IT management team, including centralized domain and DNS management.",
        "plate": ("One team", "for IT management, domain and DNS"),
        "summary": "Pro Link Systems serves as the primary IT management team for Optical Zonu, a manufacturer of fiber-optic and RF-over-fiber technology, including centralized management of the company’s domain and DNS.",
        "metrics": [("Primary", "IT management team"), ("Domain + DNS", "managed centrally"), ("50", "employees")],
        "snapshot": [("Location", "Los Angeles, California"), ("Size", "50 employees"), ("Relationship", None),
                     ("Scope", "IT management, domain and DNS management")],
        "relationship": "Ongoing",
        "challenge": "A specialized photonics company depends on reliable infrastructure, protected intellectual property and dependable connectivity to run engineering and business operations. It needs a technology partner that can own IT management end to end, including its domain and DNS.",
        "approach": ["Pro Link Systems acts as Optical Zonu’s primary IT management team",
                     "Domain and DNS managed centrally, within Pro Link Systems’ managed DNS environment"],
        "outcomes": ["An ongoing managed IT partnership, with Pro Link Systems as the primary IT team"],
        "value": "One team accountable for the technology that engineering and business operations depend on.",
        "video": ("oz", "Optical Zonu on working with Pro Link Systems"),
    },
    {
        "slug": "global-garden",
        "status": "Current client", "flags": ["R7", "R17"],
        "title": "Global Garden Case Study: Email Security | Pro Link Systems",
        "meta": "How Pro Link Systems supports Global Garden with managed IT, including email security across all of the organization's mailboxes.",
        "h1": "Email security for a growing business.",
        "card": "Managed IT, with email security deployed across the organization’s mailboxes.",
        "plate": ("18", "mailboxes on one email security platform"),
        "summary": "Pro Link Systems supports Global Garden, based in Torrance, as its managed IT partner. A featured project deployed Proofpoint email security across all 18 of the organization’s mailboxes.",
        "metrics": [("18", "mailboxes protected"), ("Managed IT", "ongoing support")],
        "snapshot": [("Location", "Torrance, California"), ("Relationship", None), ("Scope", "Managed IT, email security (Proofpoint)")],
        "relationship": "Ongoing",
        "challenge": "A growing business needs its email and core systems to stay secure against increasingly sophisticated phishing and email-borne threats, while day-to-day operations keep running across its team and shared mailboxes.",
        "approach": ["Managed IT support", "Proofpoint email security scoped to user and shared mailboxes"],
        "outcomes": ["Email security in place across all 18 mailboxes", "Stronger protection against phishing and email-borne threats"],
        "value": "Email and day-to-day systems looked after by one managed IT partner.",
    },
]
BY = {c["slug"]: c for c in CASES}
for _c in CASES:
    _k = DATA["clients"][_c["slug"]]
    _c["client"], _c["sector"], _c["current"] = CL.case_name(_k), _k["industry"], _k["status"] == "current"
    _c["snapshot"].insert(0, ("Industry", _k["industry"]))
    if _k.get("ownership"):
        _c["snapshot"].insert(1, ("Ownership", _k["ownership"]))
CASE_ORDER = [s for s in DATA["order"] if s in BY and DATA["clients"][s].get("include", True)]


def related_to(c):
    """The next three case studies in portfolio order (wrapping around), so every page links to others and is linked to."""
    ring = [s for s in CASE_ORDER if not BY[s].get("noindex")]
    if c["slug"] in ring:
        i = ring.index(c["slug"])
        ring = ring[i + 1:] + ring[:i]
    return [BY[s] for s in ring[:3]]


def status_html(c):
    word, cls = CL.STATUS[DATA["clients"][c["slug"]]["status"]]
    return '<span class="pl-status%s">%s</span> %s' % (cls, word, E(c["relationship"]))


def flags_html(c):
    return "".join('<p class="pl-flag-note"><span class="pl-flag">Review %s</span></p>' % E(r) for r in c["flags"])


def card(c, level="h3"):
    plate_n, plate_l = c["plate"]
    status = ("Current client" if c["current"] else c["status"].replace("Past engagement, ", "").replace("Historical client, ", ""))
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
    k = DATA["clients"][c["slug"]]
    body = ["<h3>Company profile</h3>", "<p>%s</p>" % E(k["description"]),
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
    if c.get("video"):
        v, label = c["video"]
        body.append('<figure class="pl-case-video"><div class="pl-video-frame"><video controls playsinline preload="none" poster="/assets/video/%s-poster.webp" '
                    'aria-label="%s"><source src="https://videos.prolinksystems.com/%s.mp4" type="video/mp4"></video></div>'
                    '<figcaption>%s</figcaption></figure>' % (v, A(label), v, E(label)))
    if c.get("photo"):
        src, srcset, w, h, alt = c["photo"]
        body.append('<figure class="pl-case-photo"><img src="%s" srcset="%s" sizes="(max-width: 1024px) 92vw, 760px" '
                    'width="%d" height="%d" loading="lazy" decoding="async" alt="%s"></figure>' % (src, srcset, w, h, A(alt)))
    related = related_to(c)
    n = len(c["metrics"])
    return ('<main>\n\n<section class="pl-casehead" aria-labelledby="page-h1">\n  <div class="pl-wrap">\n'
            '    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/case-studies">Client Success</a><span>/</span>%s</nav>\n'
            '    <p class="pl-eyebrow">%s &middot; %s</p>\n'
            '    <h1 class="pl-h1" id="page-h1">%s</h1>\n'
            '    <p class="pl-lead"><b>Executive summary</b>%s</p>\n'
            '    <div class="pl-cmetrics" style="--n:%d">%s</div>\n  </div>\n</section>\n\n'
            '<section class="pl-section" aria-label="Case study detail">\n  <div class="pl-wrap">\n'
            '    <article class="pl-study">\n      <aside class="pl-study-meta">\n        <p class="pl-study-client">%s</p>\n'
            '        <dl>%s</dl>\n        <p class="pl-study-portfolio"><a class="pl-arrow" href="/case-studies#%s">In the client portfolio</a></p>\n        %s\n      </aside>\n      <div class="pl-study-body">\n        %s\n      </div>\n'
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
               E(c["client"]), "".join(snap), c["slug"], flags_html(c), "\n        ".join(body),
               "\n".join(card(r) for r in related)))


def hub_main():
    return ('''<main>

<section class="pl-pagehead" aria-labelledby="page-h1">
  <div class="pl-wrap">
    <nav class="pl-crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span>Client Success</nav>
    <h1 class="pl-h1" id="page-h1">Long partnerships with organizations that depend on technology.</h1>
    <p class="pl-lead">The complete client portfolio, from more than 25 years of managing, securing and modernizing technology. Each profile notes whether the relationship is current or past.</p>
  </div>
</section>

%s

<section class="pl-section--tight pl-dark" aria-label="Relationship tenure">
  <div class="pl-wrap">
    <div class="pl-figures">
      <div class="pl-figure"><strong>23 yrs</strong><span>The Waverly School</span><small>Current client</small></div>
      <div class="pl-figure"><strong>18 yrs</strong><span>Law Offices of Alan B. Snitzer</span><small>Current client</small></div>
      <div class="pl-figure"><strong>13+ yrs</strong><span>Cunico Corporation</span><small>Current client, since 2012</small></div>
      <div class="pl-figure"><strong>12+ yrs</strong><span>Global Holdings</span><small>Historical client, to 2021</small></div>
    </div>
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

</main>''' % CL.portfolio_html(DATA))


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
        page = head_for(c, tracking).replace("_shared.css?v=20261120", "_shared.css?v=" + CSS_V) + ("<body>\n\n<!-- PL:HEADER -->\n<!-- /PL:HEADER -->\n\n" + detail_main(c) +
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
        entry = ("  <url>\n    <loc>%s</loc>\n    <lastmod>2026-11-22</lastmod>\n    <changefreq>monthly</changefreq>\n"
                 "    <priority>0.6</priority>\n  </url>\n" % loc)
        nl = "\r\n" if "\r\n" in sm else "\n"
        sm = sm.replace("</urlset>", entry.replace("\n", nl) + "</urlset>")
        added.append(c["slug"])
    io.open(sm_path, "w", encoding="utf-8", newline="").write(sm)
    CL.write_home(DATA)
    print("built %d case pages + hub + home clients; sitemap added: %s" % (len(CASES), ", ".join(added) or "none"))


if __name__ == "__main__":
    main()
