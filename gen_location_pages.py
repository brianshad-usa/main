#!/usr/bin/env python3
"""
gen_location_pages.py -- build city landing pages from the current location
template (managed-it-services-glendale.html, Sep-2026 deployment: LocalBusiness
+GeoCoordinates, BreadcrumbList, FAQPage, Organization, Speakable WebPage,
Nearby-areas section, footer "Other Areas We Serve").

The template file's <head> boilerplate (gtag, CSS, Organization schema), nav,
footer and FAQ script are reused verbatim; every city-specific block is
rendered from CITIES below. Refuses to overwrite an existing page unless
--force, so re-running cannot clobber hand edits.

Usage:  python gen_location_pages.py            # writes missing pages only
        python gen_location_pages.py --force    # rewrite all CITIES pages
"""
import os, re, sys, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "managed-it-services-glendale.html")

# Canonical footer list (30). Order mirrors the existing footer, new cities
# appended in geographic groups. Used by update_footers.py as well.
FOOTER_AREAS = [
    ("managed-it-services-los-angeles", "Los Angeles"),
    ("managed-it-services-downtown-los-angeles", "Downtown LA"),
    ("managed-it-services-woodland-hills", "Woodland Hills"),
    ("managed-it-services-tarzana", "Tarzana"),
    ("managed-it-services-west-hills", "West Hills"),
    ("managed-it-services-chatsworth", "Chatsworth"),
    ("managed-it-services-beverly-hills", "Beverly Hills"),
    ("managed-it-services-century-city", "Century City"),
    ("managed-it-services-west-los-angeles", "West Los Angeles"),
    ("managed-it-services-pasadena", "Pasadena"),
    ("it-support-burbank", "Burbank"),
    ("managed-it-services-studio-city", "Studio City"),
    ("managed-it-services-north-hollywood", "North Hollywood"),
    ("managed-it-services-santa-monica", "Santa Monica"),
    ("managed-it-services-culver-city", "Culver City"),
    ("managed-it-services-glendale", "Glendale"),
    ("managed-it-services-calabasas", "Calabasas"),
    ("managed-it-services-agoura-hills", "Agoura Hills"),
    ("managed-it-services-thousand-oaks", "Thousand Oaks"),
    ("managed-it-services-simi-valley", "Simi Valley"),
    ("managed-it-services-sherman-oaks", "Sherman Oaks"),
    ("managed-it-services-van-nuys", "Van Nuys"),
    ("managed-it-services-northridge", "Northridge"),
    ("managed-it-services-santa-clarita", "Santa Clarita"),
    ("managed-it-services-encino", "Encino"),
    ("managed-it-services-torrance", "Torrance"),
    ("managed-it-services-el-segundo", "El Segundo"),
    ("managed-it-services-long-beach", "Long Beach"),
    ("managed-it-services-irvine", "Irvine"),
    ("managed-it-services-orange-county", "Orange County"),
]

# --------------------------------------------------------------------------
# City content. No fabricated stats, clients, or testimonials (CONVENTIONS).
# Landmarks are public, well-known anchors used for geographic context only.
# --------------------------------------------------------------------------
CITIES = [
 {
  "slug": "managed-it-services-tarzana", "city": "Tarzana", "state": "CA",
  "h1_city": "Tarzana, CA", "zips": "91356 and 91357", "zip_short": "91356 – 91357",
  "title": "Managed IT Services Tarzana CA | Pro Link Systems",
  "meta": "Managed IT for Tarzana businesses. Cybersecurity and 24/7 help desk for medical practices, professional firms, and Ventura Blvd offices. Flat-rate since 1999.",
  "og_desc": "IT support for Tarzana's medical offices, professional services firms, and businesses along the Ventura Boulevard corridor — minutes from our Woodland Hills headquarters. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Tarzana businesses. Medical practices, professional services, and more. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Tarzana businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for Tarzana Businesses",
  "hero_p": "Comprehensive IT support for Tarzana's business community — medical and dental practices near Providence Cedars-Sinai Tarzana Medical Center, professional services firms, and the offices lining the Ventura Boulevard corridor in zip codes 91356 and 91357.",
  "region_phrase": "the central San Fernando Valley",
  "intro_label": "Why Tarzana Businesses Choose Us",
  "intro_h2": "IT support from <em>right next door</em>",
  "intro_p1": "Tarzana sits directly east of our Woodland Hills headquarters along Ventura Boulevard — which makes it the closest community we serve. The neighborhood blends a dense medical corridor anchored by Providence Cedars-Sinai Tarzana Medical Center with professional practices, financial advisors, real estate offices, and the small and mid-size businesses that fill the Boulevard's office buildings.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, and Tarzana is quite literally our backyard. Our managed IT services cover the 91356 and 91357 zip codes — from the medical office buildings around Reseda Boulevard and Etiwanda Avenue to the professional suites along Ventura Boulevard and the businesses tucked into Tarzana Village.",
  "intro_p3": "Every Tarzana client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, Tarzana is a short drive from our Woodland Hills office — often the fastest dispatch anywhere in our service area.",
  "point2_p": "We support Tarzana's medical and dental practices, financial advisors, and legal offices with the HIPAA, PCI, and compliance infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for Tarzana businesses",
  "svc_sec": "essential for medical practices and financial advisors handling sensitive client data",
  "svc_cloud": "Tarzana organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in Tarzana",
  "ind_h2": "Built for Tarzana's medical and professional community",
  "ind_sub": "From the medical corridor around Providence Cedars-Sinai Tarzana to the professional practices and small businesses along Ventura Boulevard.",
  "industries": [
   ("🏥", "Medical &amp; Dental Practices", "Tarzana's medical corridor is one of the densest in the West Valley. We provide HIPAA-compliant IT, EHR and practice-management support, and signed BAAs for physician groups, specialty clinics, dental offices, and allied health providers."),
   ("💼", "Financial Advisors &amp; CPAs", "Wealth managers, tax professionals, and accounting firms along Ventura Boulevard handle highly sensitive client data. Our cybersecurity stack and compliance-aligned practices protect both your clients and your firm's reputation."),
   ("🏠", "Real Estate &amp; Escrow", "Brokerages, escrow offices, and property managers in Tarzana face constant wire-fraud and phishing attempts. We harden email, enforce MFA, and train staff to recognize the scams that target real estate transactions."),
   ("⚖️", "Law Firms", "Legal professionals in Tarzana need secure document management, encrypted client communications, and IT systems that support California Bar guidance on protecting confidential client information."),
   ("🧘", "Wellness &amp; Specialty Clinics", "Physical therapy, dermatology, behavioral health, and aesthetic practices depend on scheduling, imaging, and billing systems that must stay up. We keep them running and secure."),
   ("🏢", "Professional Services", "Insurance agencies, consultants, staffing firms, and small corporate offices in Tarzana that need dependable IT management without the overhead of an internal IT team."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond Tarzana",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the central and west San Fernando Valley since 1999. Just outside Tarzana? We cover these nearby communities too:",
  "nearby": [("managed-it-services-woodland-hills","Woodland Hills"),("managed-it-services-encino","Encino"),("managed-it-services-sherman-oaks","Sherman Oaks"),("managed-it-services-van-nuys","Van Nuys")],
  "faq_h2": "Tarzana IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Tarzana?", "Yes. Tarzana is the closest community to our Woodland Hills office, and we serve businesses throughout the 91356 and 91357 zip codes. Remote support connects within 15 minutes of your call, and on-site technicians can be dispatched to Tarzana faster than almost anywhere else in our service area — typically the same business day."),
   ("Can you support medical practices near Providence Cedars-Sinai Tarzana?", "Absolutely. We specialize in HIPAA-compliant IT for medical and dental practices throughout Greater Los Angeles. Every healthcare engagement includes a signed Business Associate Agreement (BAA), infrastructure designed around the HIPAA Security Rule, and support for EHR and practice-management platforms."),
   ("Do you help Tarzana real estate and escrow offices with wire-fraud protection?", "Yes. Wire fraud and business email compromise are the top threats to real estate transactions. We implement advanced email security, enforce multi-factor authentication, and run security awareness training so your staff recognize the impersonation attempts that target escrow and closing communications."),
   ("We are a small business in Tarzana — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Tarzana team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Tarzana location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-agoura-hills", "city": "Agoura Hills", "state": "CA",
  "h1_city": "Agoura Hills &amp; Westlake Village", "zips": "91301, 91376, 91361, and 91362", "zip_short": "91301 – 91376 &amp; 91361 – 91362",
  "title": "Managed IT Services Agoura Hills CA | Pro Link Systems",
  "meta": "Managed IT for Agoura Hills and Westlake Village. Cybersecurity and 24/7 help desk for biotech, corporate offices, and professional firms. Flat-rate since 1999.",
  "og_desc": "IT support for the Conejo Valley's corporate headquarters, biotech and life-science companies, financial firms, and professional practices along the 101 corridor in Agoura Hills and Westlake Village. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Agoura Hills and Westlake Village businesses. Biotech, corporate offices, financial services, and more. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Agoura Hills and Westlake Village businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for the Conejo Valley",
  "hero_p": "Comprehensive IT support for the Conejo Valley's business corridor — corporate headquarters and biotech campuses along the 101, financial and professional services firms, and the growing companies of Agoura Hills and Westlake Village in zip codes 91301, 91376, 91361, and 91362.",
  "region_phrase": "the Conejo Valley and western San Fernando Valley",
  "intro_label": "Why Conejo Valley Businesses Choose Us",
  "intro_h2": "IT built for the <em>101 corridor's</em> corporate community",
  "intro_p1": "Agoura Hills and Westlake Village form one of Southern California's most concentrated corporate corridors. Office parks along the 101 Freeway house regional and national headquarters, biotechnology and life-science companies, financial services firms, and the professional practices that support them — an environment where IT reliability and security posture are board-level concerns, not back-office details.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, and the Conejo Valley is a short drive west on the 101 from our Woodland Hills headquarters. Our managed IT services cover Agoura Hills (91301, 91376) and Westlake Village (91361, 91362) — from the Agoura Road and Kanan Road business parks to the Westlake office campuses around Lindero Canyon and Via Colinas.",
  "intro_p3": "Every Conejo Valley client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians to Agoura Hills and Westlake Village businesses the same business day.",
  "point2_p": "We support the Conejo Valley's life-science companies, financial firms, and corporate offices with SOC 2, HIPAA, PCI, and compliance infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for Agoura Hills &amp; Westlake Village",
  "svc_sec": "essential for biotech companies and financial firms protecting intellectual property and client data",
  "svc_cloud": "Conejo Valley organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in the Conejo Valley",
  "ind_h2": "Built for Agoura Hills and Westlake Village's corporate community",
  "ind_sub": "From biotech and life-science companies to corporate headquarters, financial services, and the professional firms along the 101 corridor.",
  "industries": [
   ("🧬", "Biotech &amp; Life Sciences", "The Conejo Valley is a recognized life-science hub. We support research and lab environments with secure data handling, validated backup, identity and access controls, and infrastructure that protects intellectual property and research data."),
   ("🏢", "Corporate Headquarters", "Regional and national headquarters along the 101 need enterprise-grade uptime, secure multi-site connectivity, and an IT partner that can scale with headcount — without the cost of a full in-house department."),
   ("💼", "Financial Services &amp; Wealth Management", "Investment advisors, wealth managers, and insurance firms in Westlake Village handle highly regulated client data. Our cybersecurity stack supports SEC, FINRA, and GLBA-aligned practices."),
   ("🏥", "Medical &amp; Specialty Practices", "Physician groups, surgical centers, and specialty clinics across Agoura Hills and Westlake Village get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("⚖️", "Law Firms", "Legal professionals in the Conejo Valley need secure document management, encrypted client communications, and IT systems that support California Bar guidance on protecting confidential client information."),
   ("🚀", "Technology &amp; Growth Companies", "Software, e-commerce, and fast-growing companies that need SOC 2-ready cloud, identity, and endpoint management as they scale — delivered at a predictable per-user rate."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond the Conejo Valley",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the Conejo Valley and western San Fernando Valley since 1999. Just outside Agoura Hills or Westlake Village? We cover these nearby communities too:",
  "nearby": [("managed-it-services-calabasas","Calabasas"),("managed-it-services-thousand-oaks","Thousand Oaks"),("managed-it-services-woodland-hills","Woodland Hills"),("managed-it-services-west-hills","West Hills")],
  "faq_h2": "Agoura Hills &amp; Westlake Village IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Agoura Hills and Westlake Village?", "Yes. We serve businesses throughout Agoura Hills (91301, 91376) and Westlake Village (91361, 91362), including the Ventura County side of Westlake. Our Woodland Hills office is a short drive east on the 101; remote support connects within 15 minutes and on-site technicians are dispatched the same business day."),
   ("Can you support biotech and life-science companies in the Conejo Valley?", "Yes. We support research, lab, and corporate environments with secure data handling, validated and tested backups, strict identity and access controls, and endpoint protection designed to safeguard intellectual property and research data."),
   ("Do you work with corporate headquarters that have multiple offices?", "Absolutely. Many Conejo Valley companies run a headquarters here with satellite offices elsewhere in California or nationally. We manage secure site-to-site connectivity, cloud-based collaboration, and consistent security policy across every location from one flat-rate agreement."),
   ("We are a small business in Agoura Hills — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Westlake Village team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Agoura Hills or Westlake Village location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-studio-city", "city": "Studio City", "state": "CA",
  "h1_city": "Studio City, CA", "zips": "91604 and 91614", "zip_short": "91604 – 91614",
  "title": "Managed IT Services Studio City CA | Pro Link Systems",
  "meta": "Managed IT for Studio City businesses. Cybersecurity and 24/7 help desk for production companies, talent agencies, and medical practices. Flat-rate since 1999.",
  "og_desc": "IT support for Studio City's production companies, post-production houses, talent and management agencies, medical practices, and the businesses along Ventura Boulevard. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Studio City businesses. Entertainment, production, medical, and professional services. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Studio City businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for Studio City Businesses",
  "hero_p": "Comprehensive IT support for Studio City's entertainment-driven economy — production and post-production companies near Radford Studio Center, talent and management agencies, medical and dental practices, and the businesses along Ventura Boulevard in zip codes 91604 and 91614.",
  "region_phrase": "the southeast San Fernando Valley",
  "intro_label": "Why Studio City Businesses Choose Us",
  "intro_h2": "IT built for <em>Studio City's creative economy</em>",
  "intro_p1": "Studio City is where the entertainment industry and the Valley's neighborhood business community meet. Production and post-production companies cluster around Radford Studio Center, talent managers and entertainment attorneys work from Ventura Boulevard offices, and medical, dental, and professional practices serve one of the most affluent residential areas in the San Fernando Valley.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, including media and entertainment companies with the content-security and large-file workflows that define the industry. Our managed IT services cover Studio City's 91604 and 91614 zip codes — from the Radford and Laurel Canyon corridor to the Ventura Boulevard commercial strip and the offices around Tujunga Village.",
  "intro_p3": "Every Studio City client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians to Studio City businesses the same business day.",
  "point2_p": "We support Studio City's production companies, medical practices, and financial firms with the TPN-aligned content security, HIPAA, and compliance infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for Studio City businesses",
  "svc_sec": "essential for production companies protecting pre-release content and medical practices handling patient data",
  "svc_cloud": "Studio City organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in Studio City",
  "ind_h2": "Built for Studio City's entertainment and professional community",
  "ind_sub": "From production companies near Radford Studio Center to talent agencies, medical practices, and professional firms along Ventura Boulevard.",
  "industries": [
   ("🎬", "Production &amp; Post-Production", "Studio City's production community needs high-speed storage and transfer, secure review-and-approval workflows, and content security aligned with studio vendor requirements. We keep deadline-driven pipelines running and protected."),
   ("🎭", "Talent &amp; Management Agencies", "Agencies and management firms handle contracts, financials, and personal data for high-profile clients. We provide encrypted communications, strict access controls, and the discretion the industry expects."),
   ("🏥", "Medical &amp; Dental Practices", "Physician groups, dental offices, and specialty clinics serving Studio City's residential community get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("⚖️", "Entertainment &amp; Business Law", "Entertainment attorneys and business law practices in Studio City need secure document management, encrypted client communications, and IT that supports California Bar confidentiality guidance."),
   ("💼", "Business Managers &amp; CPAs", "Business management and accounting firms serving entertainment clients handle highly sensitive financial data. Our cybersecurity stack and compliance-aligned practices protect clients and reputations."),
   ("🏢", "Professional Services", "Marketing agencies, consultants, real estate offices, and small corporate teams in Studio City that need dependable IT management without the overhead of an internal IT team."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond Studio City",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the southeast San Fernando Valley and the Burbank media corridor since 1999. Just outside Studio City? We cover these nearby communities too:",
  "nearby": [("managed-it-services-sherman-oaks","Sherman Oaks"),("managed-it-services-north-hollywood","North Hollywood"),("it-support-burbank","Burbank"),("managed-it-services-encino","Encino")],
  "faq_h2": "Studio City IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Studio City?", "Yes. We serve businesses throughout Studio City's 91604 and 91614 zip codes. While our office is in Woodland Hills, we provide full remote support within 15 minutes of your call and dispatch on-site technicians to Studio City for hardware or infrastructure needs — typically the same business day."),
   ("Can you support production and post-production companies in Studio City?", "Yes. We understand the IT demands of production environments — high-speed shared storage, secure file transfer and review workflows, render and editing workstation support, and content security aligned with studio and TPN-style vendor requirements. We have supported media and entertainment businesses in Greater LA for over two decades."),
   ("Do you work with talent agencies and business management firms?", "Absolutely. Agencies, managers, and business-management CPAs handle contracts, financial records, and personal data for high-profile clients. We provide encrypted email, strict identity and access controls, secure document management, and the discretion the entertainment industry expects."),
   ("We are a small business in Studio City — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Studio City team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Studio City location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-north-hollywood", "city": "North Hollywood", "state": "CA",
  "h1_city": "North Hollywood, CA", "zips": "91601 through 91606", "zip_short": "91601 – 91606",
  "title": "Managed IT Services North Hollywood CA | Pro Link Systems",
  "meta": "Managed IT for North Hollywood. Cybersecurity and 24/7 help desk for media vendors, manufacturers, and NoHo Arts District firms. Flat-rate since 1999.",
  "og_desc": "IT support for North Hollywood's media and production-support companies, light manufacturers, healthcare providers, and the creative businesses of the NoHo Arts District. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for North Hollywood businesses. Media, manufacturing, healthcare, and creative firms. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for North Hollywood businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for North Hollywood Businesses",
  "hero_p": "Comprehensive IT support for North Hollywood's working economy — media and production-support companies, light manufacturers and distributors along Lankershim and Vineland, healthcare providers, and the creative businesses of the NoHo Arts District in zip codes 91601 through 91606.",
  "region_phrase": "the east San Fernando Valley",
  "intro_label": "Why North Hollywood Businesses Choose Us",
  "intro_h2": "IT built for <em>NoHo's working economy</em>",
  "intro_p1": "North Hollywood is one of the San Fernando Valley's most varied business districts. The NoHo Arts District around Lankershim Boulevard and the Metro B Line station has become a hub for theaters, creative agencies, and tech-enabled small businesses, while the industrial corridors along Vineland, Vanowen, and Sherman Way house equipment rental houses, production-support vendors, light manufacturers, and distributors that keep Burbank's studios and the wider region running.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999. Our managed IT services cover all of North Hollywood's 91601 through 91606 zip codes — from the Arts District and Valley Village to the industrial parks near the Burbank border and the medical offices along Riverside Drive and Magnolia Boulevard.",
  "intro_p3": "Every North Hollywood client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians to North Hollywood businesses the same business day.",
  "point2_p": "We support North Hollywood's healthcare providers, manufacturers, and media vendors with the HIPAA, PCI, and content-security infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for North Hollywood businesses",
  "svc_sec": "essential for media vendors handling studio content and healthcare providers protecting patient data",
  "svc_cloud": "North Hollywood organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in North Hollywood",
  "ind_h2": "Built for North Hollywood's diverse business community",
  "ind_sub": "From production-support vendors and light manufacturers to healthcare providers, creative agencies, and the NoHo Arts District.",
  "industries": [
   ("🎥", "Media &amp; Production Support", "Equipment rental houses, post facilities, and production vendors serving the Burbank studios need secure file handling, reliable networks, and content-security practices aligned with studio vendor requirements."),
   ("🏭", "Light Manufacturing &amp; Distribution", "Manufacturers and distributors along Vineland and Sherman Way depend on ERP, inventory, and shop-floor systems that must stay connected. We manage the network, the servers, and the security around them."),
   ("🏥", "Healthcare &amp; Clinics", "Medical groups, urgent care, dental, and behavioral-health practices across North Hollywood get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("🎨", "Creative Agencies &amp; Studios", "Design, marketing, and small production studios in the NoHo Arts District need fast shared storage, cloud collaboration, and endpoint security for hybrid creative teams."),
   ("🏢", "Professional Services", "Accounting firms, insurance agencies, consultants, and corporate offices in North Hollywood and Valley Village that need dependable IT management without an internal IT team."),
   ("🚚", "Logistics &amp; Field Services", "Dispatch-driven businesses — delivery, installation, and service companies — rely on mobile devices, routing software, and always-on connectivity. We keep the whole stack secure and running."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond North Hollywood",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the east San Fernando Valley and the Burbank media corridor since 1999. Just outside North Hollywood? We cover these nearby communities too:",
  "nearby": [("it-support-burbank","Burbank"),("managed-it-services-studio-city","Studio City"),("managed-it-services-van-nuys","Van Nuys"),("managed-it-services-sherman-oaks","Sherman Oaks")],
  "faq_h2": "North Hollywood IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in North Hollywood?", "Yes. We serve businesses throughout North Hollywood's 91601 through 91606 zip codes, including Valley Village and the NoHo Arts District. While our office is in Woodland Hills, remote support connects within 15 minutes of your call and on-site technicians are dispatched the same business day."),
   ("Can you support production vendors that work with the Burbank studios?", "Yes. Equipment houses, post facilities, and production-support companies are often required to meet studio content-security standards. We implement the access controls, network segmentation, encrypted transfer, and endpoint protection those vendor assessments look for, and we have supported media businesses in Greater LA for over two decades."),
   ("Do you support manufacturers and distributors in North Hollywood's industrial areas?", "Absolutely. We support ERP and inventory systems, warehouse Wi-Fi, barcode and label printing, and the servers and networks behind them — plus the backup and security that keep a production floor from going dark."),
   ("We are a small business in North Hollywood — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our North Hollywood team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your North Hollywood location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-santa-clarita", "city": "Santa Clarita", "state": "CA",
  "h1_city": "Santa Clarita, CA", "zips": "91321, 91350, 91351, 91354, 91355, and 91387", "zip_short": "91321 – 91390",
  "title": "Managed IT Services Santa Clarita CA | Pro Link Systems",
  "meta": "Managed IT for Santa Clarita Valley. Cybersecurity and 24/7 help desk for aerospace, manufacturing, medical, and Valencia offices. Flat-rate since 1999.",
  "og_desc": "IT support for the Santa Clarita Valley — aerospace and biomedical manufacturers in the Valencia industrial centers, healthcare providers, logistics companies, and professional firms across Valencia, Newhall, Saugus, and Canyon Country. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Santa Clarita businesses. Aerospace, manufacturing, healthcare, logistics, and professional services. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Santa Clarita Valley businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for the Santa Clarita Valley",
  "hero_p": "Comprehensive IT support for the Santa Clarita Valley's fast-growing economy — aerospace and biomedical manufacturers in the Valencia industrial centers, healthcare providers near Henry Mayo Newhall Hospital, logistics operations, and professional firms across Valencia, Newhall, Saugus, and Canyon Country.",
  "region_phrase": "the Santa Clarita Valley and north San Fernando Valley",
  "intro_label": "Why Santa Clarita Businesses Choose Us",
  "intro_h2": "IT built for <em>Santa Clarita's manufacturing and growth economy</em>",
  "intro_p1": "Santa Clarita is one of Los Angeles County's fastest-growing business markets. The Valencia Industrial Center and Valencia Commerce Center host aerospace and defense suppliers, biomedical device manufacturers, and distribution operations, while healthcare, professional services, and corporate offices have followed the population boom across Valencia, Newhall, Saugus, Canyon Country, and Stevenson Ranch.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, including manufacturers and defense contractors that must meet CMMC and ITAR-driven security requirements. Our managed IT services cover the Santa Clarita Valley's 91321, 91350, 91351, 91354, 91355, 91387, and 91390 zip codes — from the industrial parks along Avenue Stanford and Rye Canyon to the office corridors on Valencia Boulevard and Town Center Drive.",
  "intro_p3": "Every Santa Clarita client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians up the 5 to Santa Clarita businesses the same business day.",
  "point2_p": "We support Santa Clarita's aerospace suppliers, manufacturers, and healthcare providers with the CMMC-ready, HIPAA, and compliance infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for Santa Clarita businesses",
  "svc_sec": "essential for aerospace suppliers handling controlled data and healthcare providers protecting patient records",
  "svc_cloud": "Santa Clarita organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in Santa Clarita",
  "ind_h2": "Built for the Santa Clarita Valley's business community",
  "ind_sub": "From aerospace and biomedical manufacturers in Valencia to healthcare, logistics, and professional firms across the valley.",
  "industries": [
   ("✈️", "Aerospace &amp; Defense Suppliers", "Santa Clarita's aerospace supply chain faces CMMC and ITAR requirements. We prepare and manage environments for controlled unclassified information — segmented networks, access controls, logging, and documented policies — so assessments go smoothly."),
   ("🏭", "Manufacturing &amp; Biomedical Devices", "Device makers and precision manufacturers in the Valencia industrial centers depend on ERP, quality systems, and connected shop floors. We manage the servers, networks, and security that keep production running."),
   ("🏥", "Healthcare &amp; Medical Groups", "Physician groups, surgical centers, and specialty clinics near Henry Mayo Newhall Hospital get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("🚚", "Logistics &amp; Distribution", "Warehouses and distribution operations along the 5 corridor rely on WMS, scanning, warehouse Wi-Fi, and EDI connections. We keep the whole stack reliable and secure."),
   ("🏢", "Professional &amp; Financial Services", "CPAs, insurance agencies, engineering firms, and corporate offices across Valencia and Stevenson Ranch that need dependable IT management without an internal IT team."),
   ("🏗️", "Construction &amp; Engineering", "Contractors and engineering firms building out the Santa Clarita Valley need secure project document management, field connectivity, and protection against the invoice-fraud scams that target the trades."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond Santa Clarita",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the Santa Clarita Valley and the north San Fernando Valley since 1999. Just outside Santa Clarita? We cover these nearby communities too:",
  "nearby": [("managed-it-services-northridge","Northridge"),("managed-it-services-chatsworth","Chatsworth"),("it-support-burbank","Burbank"),("managed-it-services-woodland-hills","Woodland Hills")],
  "faq_h2": "Santa Clarita IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Santa Clarita?", "Yes. We serve businesses throughout the Santa Clarita Valley — Valencia, Newhall, Saugus, Canyon Country, and Stevenson Ranch (zip codes 91321 through 91390). While our office is in Woodland Hills, remote support connects within 15 minutes of your call and on-site technicians are dispatched up the 5 the same business day."),
   ("Can you help our aerospace supplier prepare for CMMC?", "Yes. We prepare and manage IT environments to meet CMMC and NIST 800-171 requirements — network segmentation for controlled unclassified information, multi-factor authentication, logging and monitoring, encrypted backups, and the documented policies assessors expect. Certification itself is performed by an independent C3PAO; our role is to build and maintain an environment that is ready for it."),
   ("Do you support manufacturers in the Valencia Industrial Center?", "Absolutely. We support ERP and quality-management systems, shop-floor connectivity, industrial Wi-Fi, and the servers and backups behind them — along with the security controls that keep a production line from going down to ransomware."),
   ("We are a small business in Santa Clarita — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Santa Clarita team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Santa Clarita location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-simi-valley", "city": "Simi Valley", "state": "CA",
  "h1_city": "Simi Valley, CA", "zips": "93063 and 93065", "zip_short": "93063 – 93065",
  "title": "Managed IT Services Simi Valley CA | Pro Link Systems",
  "meta": "Managed IT for Simi Valley businesses. Cybersecurity and 24/7 help desk for aerospace, manufacturing, healthcare, and professional firms. Flat-rate since 1999.",
  "og_desc": "IT support for Simi Valley's aerospace and defense contractors, manufacturers, healthcare providers, and professional services firms along the 118 corridor. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Simi Valley businesses. Aerospace, manufacturing, healthcare, and professional services. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Simi Valley businesses. Serving Greater Los Angeles and eastern Ventura County since 1999.",
  "badge": "Full-Service IT Support for Simi Valley Businesses",
  "hero_p": "Comprehensive IT support for Simi Valley's industrial and professional economy — aerospace and defense contractors, precision manufacturers along the 118 corridor, healthcare providers, and the professional firms serving one of Ventura County's largest cities in zip codes 93063 and 93065.",
  "region_phrase": "eastern Ventura County and the west San Fernando Valley",
  "intro_label": "Why Simi Valley Businesses Choose Us",
  "intro_h2": "IT built for <em>Simi Valley's aerospace and manufacturing base</em>",
  "intro_p1": "Simi Valley has a long industrial heritage. Aerospace and defense contractors, precision machine shops, electronics manufacturers, and their suppliers cluster in the business parks along the 118 Freeway, Los Angeles Avenue, and Easy Street — many of them subject to CMMC, ITAR, and customer-driven security requirements. Around them, healthcare providers, financial firms, and professional practices serve a city of more than 120,000 residents.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, including defense suppliers that must document and maintain a hardened IT environment. Our managed IT services cover Simi Valley's 93063 and 93065 zip codes — a straight shot west on the 118 from our Woodland Hills headquarters — from the industrial parks on the east side to the Madera Road and First Street commercial corridors.",
  "intro_p3": "Every Simi Valley client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians west on the 118 to Simi Valley businesses the same business day.",
  "point2_p": "We support Simi Valley's defense contractors, manufacturers, and healthcare providers with the CMMC-ready, HIPAA, and compliance infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for Simi Valley businesses",
  "svc_sec": "essential for defense contractors handling controlled data and healthcare providers protecting patient records",
  "svc_cloud": "Simi Valley organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in Simi Valley",
  "ind_h2": "Built for Simi Valley's industrial and professional community",
  "ind_sub": "From aerospace and defense contractors along the 118 to manufacturers, healthcare providers, and professional firms citywide.",
  "industries": [
   ("✈️", "Aerospace &amp; Defense Contractors", "Simi Valley's defense suppliers face CMMC and ITAR obligations. We prepare and manage environments for controlled unclassified information — segmented networks, MFA, logging, encrypted backups, and documented policies — so assessments go smoothly."),
   ("🏭", "Precision Manufacturing &amp; Electronics", "Machine shops, electronics assemblers, and component manufacturers depend on ERP, CAD/CAM, and connected production equipment. We manage the servers, networks, and security that keep the floor running."),
   ("🏥", "Healthcare &amp; Medical Practices", "Physician groups, urgent care, dental, and specialty clinics across Simi Valley get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("💼", "Financial &amp; Insurance Services", "CPAs, financial advisors, and insurance agencies handle highly sensitive client data. Our cybersecurity stack and compliance-aligned practices protect both your clients and your firm's reputation."),
   ("🏗️", "Construction &amp; Trades", "Contractors and specialty trades need secure project document management, field connectivity, and protection against the invoice and payment-redirect fraud that targets the construction industry."),
   ("🏢", "Professional Services", "Engineering firms, law offices, consultants, and corporate branch offices in Simi Valley that need dependable IT management without the overhead of an internal IT team."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond Simi Valley",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across eastern Ventura County and the west San Fernando Valley since 1999. Just outside Simi Valley? We cover these nearby communities too:",
  "nearby": [("managed-it-services-chatsworth","Chatsworth"),("managed-it-services-west-hills","West Hills"),("managed-it-services-thousand-oaks","Thousand Oaks"),("managed-it-services-northridge","Northridge")],
  "faq_h2": "Simi Valley IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Simi Valley?", "Yes. We serve businesses throughout Simi Valley's 93063 and 93065 zip codes. Our Woodland Hills office is a direct drive west on the 118; remote support connects within 15 minutes of your call and on-site technicians are dispatched the same business day."),
   ("Can you help our defense contractor meet CMMC requirements?", "Yes. We prepare and manage IT environments to meet CMMC and NIST 800-171 requirements — network segmentation for controlled unclassified information, multi-factor authentication, logging and monitoring, encrypted backups, and the documented policies assessors expect. Certification itself is performed by an independent C3PAO; our role is to build and maintain an environment that is ready for it."),
   ("Do you support manufacturers with production equipment on the network?", "Absolutely. We segment and secure operational technology from office networks, support ERP and CAD/CAM systems, manage industrial Wi-Fi, and maintain the backups and recovery plans that keep a production line from going dark to ransomware or hardware failure."),
   ("We are a small business in Simi Valley — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Simi Valley team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Simi Valley location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-downtown-los-angeles", "city": "Downtown Los Angeles", "state": "CA",
  "h1_city": "Downtown Los Angeles", "zips": "90012 through 90017, 90021, and 90071", "zip_short": "90012 – 90071",
  "title": "Managed IT Services Downtown Los Angeles | Pro Link Systems",
  "meta": "Managed IT for Downtown Los Angeles. Cybersecurity and 24/7 help desk for law firms, finance, and Arts District creative and tech firms. Flat-rate since 1999.",
  "og_desc": "IT support for Downtown LA's law firms and financial companies on Bunker Hill, creative and tech firms in the Arts District, apparel businesses in the Fashion District, and healthcare providers across the urban core. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for Downtown Los Angeles businesses. Law, finance, creative, tech, healthcare, and more. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for Downtown Los Angeles businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for Downtown LA Businesses",
  "hero_p": "Comprehensive IT support for Downtown Los Angeles — law firms and financial companies in the Bunker Hill and Financial District towers, creative and technology companies in the Arts District, apparel and wholesale businesses in the Fashion District, and healthcare providers across the urban core in zip codes 90012 through 90071.",
  "region_phrase": "Downtown Los Angeles and the central city",
  "intro_label": "Why Downtown LA Businesses Choose Us",
  "intro_h2": "IT built for <em>Downtown's high-rise and high-growth economy</em>",
  "intro_p1": "Downtown Los Angeles is the densest professional market in Southern California. Law firms, banks, investment managers, and accounting practices fill the towers of Bunker Hill and the Financial District; architecture, media, and technology companies have transformed the Arts District; the Fashion District runs on wholesale and e-commerce; and hospitals, clinics, and civic organizations serve the region from the Civic Center south to the Figueroa Corridor.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999, and Downtown has always been part of that footprint — our description of service has read \"from Woodland Hills to Downtown LA\" for years. Our managed IT services cover zip codes 90012 through 90017, 90021, and 90071 — high-rise suites with building-managed connectivity, converted warehouse offices, and everything in between.",
  "intro_p3": "Every Downtown client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes — critical in a high-rise where on-site access takes coordination. For hardware and on-site needs, we dispatch technicians to Downtown businesses the same business day.",
  "point2_p": "We support Downtown's law firms, financial companies, and healthcare providers with the compliance infrastructure their industries demand — from California Bar confidentiality guidance to SEC, FINRA, PCI, and HIPAA.",
  "services_h2": "Complete IT coverage for Downtown Los Angeles businesses",
  "svc_sec": "essential for law firms and financial companies entrusted with privileged and regulated client data",
  "svc_cloud": "Downtown organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve Downtown",
  "ind_h2": "Built for Downtown Los Angeles's professional and creative community",
  "ind_sub": "From law and finance on Bunker Hill to the Arts District's creative and tech firms, the Fashion District, and the urban core's healthcare providers.",
  "industries": [
   ("⚖️", "Law Firms", "Downtown is home to more law firms than anywhere else in the region. We deliver secure document and matter management, encrypted client communications, litigation-support connectivity, and IT that supports California Bar guidance on protecting confidential client information."),
   ("💼", "Banking, Finance &amp; Accounting", "Investment managers, lenders, CPAs, and insurance companies in the Financial District handle highly regulated data. Our cybersecurity stack supports SEC, FINRA, GLBA, and PCI-aligned practices."),
   ("🎨", "Arts District Creative &amp; Tech", "Architecture studios, media companies, software startups, and agencies in converted warehouse spaces need fast shared storage, cloud collaboration, SOC 2-ready security, and support for hybrid teams."),
   ("👗", "Fashion District &amp; Wholesale", "Apparel wholesalers, showrooms, and e-commerce operations depend on inventory and order systems, POS, and payment security. We keep them connected and PCI-aligned."),
   ("🏥", "Healthcare &amp; Clinics", "Medical groups, community clinics, and specialty practices across the urban core get HIPAA-compliant IT, EHR support, and signed Business Associate Agreements."),
   ("🏛️", "Nonprofits &amp; Civic Organizations", "Foundations, associations, and community organizations around the Civic Center need grant-compliant, cost-conscious IT with the same security posture as any corporate office."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond Downtown",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across Los Angeles since 1999. Just outside Downtown? We cover these nearby communities too:",
  "nearby": [("managed-it-services-los-angeles","Los Angeles"),("managed-it-services-glendale","Glendale"),("managed-it-services-pasadena","Pasadena"),("managed-it-services-culver-city","Culver City")],
  "faq_h2": "Downtown Los Angeles IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in Downtown Los Angeles?", "Yes. We serve businesses throughout Downtown LA — Bunker Hill, the Financial District, the Arts District, the Fashion District, Little Tokyo, Chinatown, and the Civic Center (zip codes 90012 through 90017, 90021, and 90071). While our office is in Woodland Hills, remote support connects within 15 minutes of your call and on-site technicians are dispatched the same business day."),
   ("Can you support a law firm in a Downtown high-rise?", "Absolutely. We work within building-managed connectivity and security requirements, support document and practice-management platforms, deliver encrypted email and secure client portals, and provide the audit trails and access controls that law-firm clients and cyber-insurance carriers increasingly require."),
   ("Do you work with creative and technology companies in the Arts District?", "Yes. Converted warehouse offices bring their own challenges — Wi-Fi coverage in brick-and-timber buildings, large-file collaboration, and hybrid teams. We design the network, manage cloud storage and Microsoft 365 or Google Workspace, and build SOC 2-ready security without slowing creative work down."),
   ("We are a small business Downtown — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our Downtown team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your Downtown Los Angeles location the same business day."),
  ],
 },
 {
  "slug": "managed-it-services-west-los-angeles", "city": "West Los Angeles", "state": "CA",
  "h1_city": "West Los Angeles", "zips": "90025, 90064, 90049, and 90024", "zip_short": "90024 – 90064",
  "title": "Managed IT Services West Los Angeles | Pro Link Systems",
  "meta": "Managed IT for West LA, Brentwood, and Westwood. Cybersecurity and 24/7 help desk for medical, legal, entertainment, and tech firms. Flat-rate since 1999.",
  "og_desc": "IT support for West LA's medical practices, law firms, entertainment and technology companies, and professional offices across Sawtelle, Brentwood, Westwood, and the Olympic and Pico corridors. Flat-rate, 24/7, no surprises.",
  "tw_desc": "Managed IT, cybersecurity, and 24/7 help desk for West Los Angeles businesses. Medical, legal, entertainment, tech, and professional services. Flat-rate plans. Serving Greater Los Angeles since 1999.",
  "schema_desc": "Managed IT services and cybersecurity for West Los Angeles businesses. Serving Greater Los Angeles since 1999.",
  "badge": "Full-Service IT Support for West LA Businesses",
  "hero_p": "Comprehensive IT support for West Los Angeles — medical and specialty practices around the Westwood medical corridor, law firms and financial offices in Brentwood, entertainment and technology companies along the Olympic and Pico corridors, and the businesses of Sawtelle and West LA in zip codes 90025, 90064, 90049, and 90024.",
  "region_phrase": "the Westside",
  "intro_label": "Why West LA Businesses Choose Us",
  "intro_h2": "IT built for <em>the Westside's professional corridor</em>",
  "intro_p1": "West Los Angeles is the connective tissue of the Westside — the stretch between Santa Monica and Beverly Hills where Brentwood's financial and legal offices, Westwood's medical corridor, the entertainment and technology companies along Olympic and Pico Boulevards, and the Japanese-American business district of Sawtelle all share a few square miles of some of the most expensive commercial real estate in the country.",
  "intro_p2": "Pro Link Systems has supported Greater Los Angeles businesses since 1999. Our managed IT services cover West LA's 90025, 90064, 90049, and 90024 zip codes — from the medical office buildings near Wilshire and Westwood to the Brentwood offices along San Vicente, the creative and tech spaces on Olympic, and the professional suites along Santa Monica and Pico Boulevards.",
  "intro_p3": "Every West LA client — regardless of size or industry — gets a flat-rate, all-inclusive managed IT plan. That means unlimited support, 24/7 monitoring, enterprise cybersecurity, and compliance assistance for one predictable monthly fee. No per-ticket billing. No annual contracts required.",
  "point1_p": "Remote support resolves most issues within 15 minutes. For hardware and on-site needs, we dispatch technicians over the hill to West LA businesses the same business day.",
  "point2_p": "We support West LA's medical practices, law firms, and financial advisors with the HIPAA, California Bar, SEC/FINRA, and PCI-aligned infrastructure their industries demand.",
  "services_h2": "Complete IT coverage for West Los Angeles businesses",
  "svc_sec": "essential for medical practices and law firms handling protected and privileged data",
  "svc_cloud": "West LA organizations that need reliable collaboration, secure remote access, and scalable infrastructure without the overhead",
  "ind_label": "Who We Serve in West LA",
  "ind_h2": "Built for West Los Angeles's professional and creative community",
  "ind_sub": "From the Westwood medical corridor and Brentwood's legal and financial offices to entertainment, technology, and the Sawtelle business district.",
  "industries": [
   ("🏥", "Medical &amp; Specialty Practices", "The Westwood and Wilshire medical corridor is one of the region's largest. We provide HIPAA-compliant IT, EHR and imaging-system support, and signed BAAs for physician groups, surgical centers, and specialty clinics."),
   ("⚖️", "Law Firms", "Litigation, entertainment, and business law practices in Brentwood and West LA need secure document management, encrypted client communications, and IT that supports California Bar confidentiality guidance."),
   ("💼", "Wealth Management &amp; Family Offices", "Investment advisors, business managers, and family offices handle highly sensitive financial data. Our cybersecurity stack supports SEC, FINRA, and GLBA-aligned practices and protects high-net-worth clients from targeted fraud."),
   ("🎬", "Entertainment &amp; Media", "Production companies, post facilities, and talent-adjacent firms along Olympic and Pico need high-speed storage, secure review workflows, and content security aligned with studio vendor requirements."),
   ("🚀", "Technology &amp; Startups", "Software and digital-media companies on the Westside need SOC 2-ready cloud, identity, and endpoint management that scales with headcount — at a predictable per-user rate."),
   ("🏢", "Professional Services", "Architecture firms, agencies, consultants, and real estate offices across West LA, Sawtelle, and Brentwood that need dependable IT management without the overhead of an internal IT team."),
  ],
  "nearby_label": "Nearby Service Areas", "nearby_h2": "Managed IT beyond West LA",
  "nearby_p": "From our Woodland Hills headquarters, Pro Link Systems has supported businesses across the Westside since 1999. Just outside West Los Angeles? We cover these nearby communities too:",
  "nearby": [("managed-it-services-santa-monica","Santa Monica"),("managed-it-services-beverly-hills","Beverly Hills"),("managed-it-services-century-city","Century City"),("managed-it-services-culver-city","Culver City")],
  "faq_h2": "West Los Angeles IT support — answered",
  "faqs": [
   ("Do you provide managed IT services in West Los Angeles?", "Yes. We serve businesses throughout West LA, Sawtelle, Brentwood, and Westwood (zip codes 90025, 90064, 90049, and 90024). While our office is in Woodland Hills, remote support connects within 15 minutes of your call and on-site technicians are dispatched over the hill the same business day."),
   ("Can you support medical practices in the Westwood medical corridor?", "Absolutely. We specialize in HIPAA-compliant IT for medical and specialty practices throughout Greater Los Angeles. Every healthcare engagement includes a signed Business Associate Agreement (BAA), infrastructure designed around the HIPAA Security Rule, and support for EHR, imaging, and practice-management platforms."),
   ("Do you work with wealth managers and family offices in Brentwood?", "Yes. High-net-worth clients are prime targets for impersonation and wire fraud. We implement advanced email security, enforce multi-factor authentication, harden identity and access, and run security awareness training, alongside the controls that support SEC, FINRA, and GLBA-aligned practices."),
   ("We are a small business in West LA — do you have a minimum size requirement?", "No minimum. Our flat-rate plans work for businesses of any size. Whether you have 5 employees or 150, you get the same per-user rate and the same level of attentive, responsive service. No minimums, no tiered support levels based on headcount."),
   ("How does remote support work for our West LA team?", "Remote support connects within 15 minutes of your call via our live help desk, available 24/7/365. Our engineers resolve the vast majority of issues remotely — software problems, network configuration, Microsoft 365, cloud access, VPN, and more. For hardware or on-site needs, we dispatch a technician to your West Los Angeles location the same business day."),
  ],
 },
]

APEX = "https://prolinksystems.com"
PHONE_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.22 2.18 2 2 0 012.18 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.16 6.16l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>'
CHEV_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'


def j(s):
    """JSON-escape a string that may contain HTML entities (decode first)."""
    return json.dumps(html.unescape(s), ensure_ascii=False)


def faq_schema(c):
    items = ",\n".join(
        '      {\n        "@type": "Question",\n        "name": %s,\n        "acceptedAnswer": { "@type": "Answer", "text": %s }\n      }'
        % (j(q), j(a)) for q, a in c["faqs"])
    return ('  <script type="application/ld+json">\n  {\n    "@context": "https://schema.org",\n'
            '    "@type": "FAQPage",\n    "mainEntity": [\n%s\n    ]\n  }\n  </script>' % items)


def local_business_schema(c):
    return ('  <script type="application/ld+json">\n  {\n    "@context": "https://schema.org",\n'
            '    "@type": "LocalBusiness",\n    "@id": "https://prolinksystems.com/#business",\n'
            '    "name": "Pro Link Systems",\n    "url": "https://prolinksystems.com",\n'
            '    "logo": "https://prolinksystems.com/logo.png",\n'
            '    "description": %s,\n    "telephone": "+18008906133",\n    "email": "info@prolinksystems.com",\n'
            '    "address": {\n      "@type": "PostalAddress",\n      "streetAddress": "21241 Ventura Boulevard",\n'
            '      "addressLocality": "Woodland Hills",\n      "addressRegion": "CA",\n      "postalCode": "91364",\n'
            '      "addressCountry": "US"\n    },\n    "geo": {\n      "@type": "GeoCoordinates",\n'
            '      "latitude": 34.1684,\n      "longitude": -118.5997\n    },\n    "areaServed": [\n'
            '      { "@type": "City", "name": %s },\n      { "@type": "City", "name": "Los Angeles" }\n    ],\n'
            '    "openingHoursSpecification": {\n      "@type": "OpeningHoursSpecification",\n'
            '      "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],\n'
            '      "opens": "09:00",\n      "closes": "18:00"\n    }\n  }\n  </script>'
            % (j(c["schema_desc"]), j(c["city"])))


def breadcrumb_schema(c):
    return ('  <script type="application/ld+json">\n  {\n    "@context": "https://schema.org",\n'
            '    "@type": "BreadcrumbList",\n    "itemListElement": [\n'
            '      { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://prolinksystems.com/" },\n'
            '      { "@type": "ListItem", "position": 2, "name": %s, "item": "%s/%s" }\n    ]\n  }\n  </script>'
            % (j("Managed IT Services " + c["city"]), APEX, c["slug"]))


def speakable_schema(c):
    return ('  <!-- Speakable (T11) -->\n  <script type="application/ld+json">\n  {\n'
            '    "@context": "https://schema.org",\n    "@type": "WebPage",\n'
            '    "@id": "%s/%s#webpage",\n    "url": "%s/%s",\n'
            '    "speakable": {\n      "@type": "SpeakableSpecification",\n      "cssSelector": [\n'
            '        "h1",\n        "h1 + p"\n      ]\n    }\n  }\n  </script>' % (APEX, c["slug"], APEX, c["slug"]))


def footer_areas_block(prefix=""):
    links = "\n".join('      <a href="%s%s">%s</a>' % (prefix, s, n) for s, n in FOOTER_AREAS)
    return '  <div class="footer-areas">\n    <h3>Other Areas We Serve</h3>\n    <div class="footer-areas-links">\n%s\n    </div>\n  </div>' % links


def body(c):
    city = c["city"]
    ind_cards = "\n".join(
        '      <div class="industry-card">\n        <div class="industry-icon">%s</div>\n        <h3>%s</h3>\n        <p>%s</p>\n      </div>'
        % (i, h, p) for i, h, p in c["industries"])
    nearby_links = " &nbsp;&middot;&nbsp;\n".join(
        '      <a href="/%s" style="color:#0b3d6b;">%s</a>' % (s, n) for s, n in c["nearby"])
    faq_items = "\n".join(
        '      <div class="faq-item">\n        <button class="faq-q" aria-expanded="false">\n          %s\n          %s\n        </button>\n        <div class="faq-a">%s</div>\n      </div>'
        % (q, CHEV_SVG, a) for q, a in c["faqs"])
    return f'''
<section class="page-hero" aria-label="{city} managed IT services">
  <div class="local-badge">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
    {c["badge"]}
  </div>
  <h1>Managed IT Services in<br><em>{c["h1_city"]}</em></h1>
  <p>{c["hero_p"]}</p>
  <div class="hero-cta-group">
    <a href="contact" class="btn btn-gold">
      {PHONE_SVG}
      Get a Free IT Assessment
    </a>
    <a href="tel:18008906133" class="btn btn-outline-white">Call 1-800-890-6133</a>
  </div>
</section>

<div class="trust-bar" role="complementary">
  <div class="trust-item">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
    Full-Coverage {city} IT Support
  </div>
  <div class="trust-item">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    24/7/365 Live Help Desk
  </div>
  <div class="trust-item">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
    Serving Greater Los Angeles Since 1999
  </div>
  <div class="trust-item">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    Flat-Rate Plans — No Surprise Bills
  </div>
</div>

<section class="intro-section" aria-labelledby="intro-heading">
  <div class="intro-grid">
    <div class="intro-text">
      <span class="section-label">{c["intro_label"]}</span>
      <h2 id="intro-heading">{c["intro_h2"]}</h2>
      <p>{c["intro_p1"]}</p>
      <p>{c["intro_p2"]}</p>
      <p>{c["intro_p3"]}</p>
    </div>
    <div class="intro-points">
      <div class="intro-point">
        <div class="intro-point-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="intro-point-body">
          <h3>On-Site Support Available</h3>
          <p>{c["point1_p"]}</p>
        </div>
      </div>
      <div class="intro-point">
        <div class="intro-point-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div class="intro-point-body">
          <h3>HIPAA &amp; Compliance-Ready</h3>
          <p>{c["point2_p"]}</p>
        </div>
      </div>
      <div class="intro-point">
        <div class="intro-point-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
        </div>
        <div class="intro-point-body">
          <h3>Predictable Monthly Costs</h3>
          <p>One flat monthly rate per user covers everything — unlimited tickets, monitoring, cybersecurity, and on-site visits. Your IT budget never fluctuates.</p>
        </div>
      </div>
      <div class="intro-point">
        <div class="intro-point-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        </div>
        <div class="intro-point-body">
          <h3>Real Engineers, No Call Centers</h3>
          <p>Every support call is answered by a trained Pro Link engineer — not a scripted responder who's never seen your environment before.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="services-section" aria-labelledby="services-heading">
  <div class="container">
    <div class="centered" style="margin-bottom:48px;">
      <span class="section-label">What We Provide</span>
      <h2 class="section-heading" id="services-heading">{c["services_h2"]}</h2>
      <p class="section-sub">Every service under one flat monthly rate — no à la carte surprises.</p>
    </div>
    <div class="services-grid-4">
      <div class="svc-card">
        <div class="svc-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <h3>Managed IT &amp; Help Desk</h3>
        <p>Proactive monitoring, patch management, and 24/7 live help desk for your {city} team — the full IT department experience at a predictable flat monthly rate.</p>
        <ul>
          <li>Unlimited help desk tickets</li>
          <li>24/7/365 live engineer support</li>
          <li>Proactive monitoring &amp; alerts</li>
          <li>Patch management &amp; updates</li>
        </ul>
      </div>
      <div class="svc-card">
        <div class="svc-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <h3>Cybersecurity</h3>
        <p>Multi-layered security protecting {city} businesses from ransomware, phishing, and data breaches — {c["svc_sec"]}.</p>
        <ul>
          <li>Endpoint detection &amp; response</li>
          <li>Email threat protection</li>
          <li>Security awareness training</li>
          <li>Vulnerability assessments</li>
        </ul>
      </div>
      <div class="svc-card">
        <div class="svc-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <h3>Cloud &amp; Infrastructure</h3>
        <p>Microsoft 365, Azure, and cloud migrations for {c["svc_cloud"]}.</p>
        <ul>
          <li>Microsoft 365 management</li>
          <li>Cloud migrations &amp; setup</li>
          <li>Server &amp; network management</li>
          <li>Secure remote access &amp; VPN</li>
        </ul>
      </div>
      <div class="svc-card">
        <div class="svc-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        </div>
        <h3>Backup &amp; Disaster Recovery</h3>
        <p>Automated backups and tested recovery plans protecting {city} businesses from ransomware, hardware failure, and unexpected disasters — so your data is always recoverable.</p>
        <ul>
          <li>Automated daily backups</li>
          <li>Offsite &amp; cloud backup copies</li>
          <li>Tested recovery procedures</li>
          <li>Business continuity planning</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<div class="stats-strip" role="region" aria-label="Pro Link by the numbers">
  <div class="stat-item">
    <span class="stat-number">27+</span>
    <div class="stat-label">Years serving<br>Greater Los Angeles</div>
  </div>
  <div class="stat-item">
    <span class="stat-number">&lt;15m</span>
    <div class="stat-label">Average response time<br>for remote support</div>
  </div>
  <div class="stat-item">
    <span class="stat-number">Full coverage</span>
    <div class="stat-label">All {city} zip codes<br>{c["zip_short"]}</div>
  </div>
  <div class="stat-item">
    <span class="stat-number">24/7</span>
    <div class="stat-label">Live help desk —<br>always a real engineer</div>
  </div>
</div>

<section class="industries-section" aria-labelledby="industries-heading">
  <div class="container">
    <div class="centered" style="margin-bottom:48px;">
      <span class="section-label">{c["ind_label"]}</span>
      <h2 class="section-heading" id="industries-heading">{c["ind_h2"]}</h2>
      <p class="section-sub">{c["ind_sub"]}</p>
    </div>
    <div class="industries-grid">
{ind_cards}
    </div>
  </div>
</section>

<!-- NEARBY SERVICE AREAS -->
<section aria-label="Nearby service areas" style="padding:56px 24px;background:#f7f9fc;">
  <div class="container" style="max-width:820px;margin:0 auto;text-align:center;">
    <span class="section-label">{c["nearby_label"]}</span>
    <h2 class="section-heading">{c["nearby_h2"]}</h2>
    <p class="section-sub" style="margin-bottom:20px;">{c["nearby_p"]}</p>
    <p style="font-size:1.05rem;line-height:2.1;font-weight:600;">
{nearby_links}
    </p>
    <p style="margin-top:14px;"><a href="/managed-it-services" style="color:#0b3d6b;font-weight:700;">See all Los Angeles managed IT service areas &rarr;</a></p>
  </div>
</section>

<div class="cta-band" role="complementary">
  <span class="section-label" style="display:block;margin-bottom:12px;">Ready to Get Started?</span>
  <h2>Get a free IT assessment for your {city} business</h2>
  <p>No pressure, no commitment — just an honest look at your current IT and how we can make it better.</p>
  <div class="cta-buttons">
    <a href="contact" class="btn btn-gold">
      {PHONE_SVG}
      Schedule a Free Discovery Call
    </a>
    <a href="tel:18008906133" class="btn btn-outline-white">Call 1-800-890-6133</a>
  </div>
</div>

<section class="faq-section" aria-labelledby="faq-heading">
  <div class="container">
    <div class="centered" style="margin-bottom:48px;">
      <span class="section-label">Common Questions</span>
      <h2 class="section-heading" id="faq-heading">{c["faq_h2"]}</h2>
    </div>
    <div class="faq-list">
{faq_items}
    </div>
  </div>
</section>

'''


def build(c, tpl):
    head_end = tpl.index("</head>")
    head = tpl[:head_end]
    # --- replace meta ---
    head = re.sub(r"<title>.*?</title>", "<title>%s</title>" % c["title"], head, count=1)
    head = re.sub(r'<meta name="description" content=".*?">',
                  '<meta name="description" content="%s">' % c["meta"].replace('"', "&quot;"), head, count=1)
    url = f'{APEX}/{c["slug"]}'
    head = re.sub(r'<link rel="canonical" href=".*?">', f'<link rel="canonical" href="{url}">', head, count=1)
    head = re.sub(r'<meta property="og:url" content=".*?">', f'<meta property="og:url" content="{url}">', head, count=1)
    head = re.sub(r'<meta property="og:title" content=".*?">', '<meta property="og:title" content="%s">' % c["title"], head, count=1)
    head = re.sub(r'<meta property="og:description" content=".*?">', '<meta property="og:description" content="%s">' % c["og_desc"], head, count=1)
    head = re.sub(r'<meta name="twitter:title" content=".*?">', '<meta name="twitter:title" content="%s">' % c["title"], head, count=1)
    head = re.sub(r'<meta name="twitter:description" content=".*?">', '<meta name="twitter:description" content="%s">' % c["tw_desc"], head, count=1)
    # --- replace JSON-LD blocks by position: 1 LocalBusiness, 2 Breadcrumb, 3 FAQ, (4 Organization kept), 5 Speakable ---
    blocks = list(re.finditer(r'  <script type="application/ld\+json">.*?</script>', head, flags=re.S))
    assert len(blocks) == 5, f"template has {len(blocks)} JSON-LD blocks, expected 5"
    repl = {0: local_business_schema(c), 1: breadcrumb_schema(c), 2: faq_schema(c), 4: speakable_schema(c)}
    out, pos = [], 0
    for i, m in enumerate(blocks):
        out.append(head[pos:m.start()])
        out.append(repl.get(i, m.group(0)))
        pos = m.end()
    out.append(head[pos:])
    head = "".join(out)
    head = head.replace("  <!-- Speakable (T11) -->\n  <!-- Speakable (T11) -->", "  <!-- Speakable (T11) -->")
    # --- body: keep nav/mobile-menu from template, regenerate content, keep footer+script ---
    rest = tpl[head_end:]
    nav_start = rest.index("<nav ")
    hero_start = rest.index('<section class="page-hero"')
    footer_start = rest.index("<footer ")
    nav = rest[nav_start:hero_start]
    footer = rest[footer_start:]
    footer, n = re.subn(r'  <div class="footer-areas">.*?\n    </div>\n  </div>', footer_areas_block(), footer, count=1, flags=re.S)
    assert n == 1, "footer-areas block not found in template footer"
    return head + "</head>\n<body>\n\n" + nav + body(c).lstrip("\n") + footer


def main():
    force = "--force" in sys.argv
    with open(TEMPLATE, encoding="utf-8") as fh:
        tpl = fh.read()
    for c in CITIES:
        path = os.path.join(HERE, c["slug"] + ".html")
        if os.path.exists(path) and not force:
            print("skip (exists):", c["slug"]); continue
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build(c, tpl))
        print("wrote:", c["slug"] + ".html")


if __name__ == "__main__":
    main()
