"""
generate_gbp_post.py
--------------------
Generates and publishes the weekly Pro Link Systems Google Business Profile post.
Uses Claude to write content on a rotating 8-week theme cycle, then calls
gbp_post.py to publish it.

Run via GitHub Actions on a weekly schedule (see gbp-weekly.yml).
Can also be run manually:
  python generate_gbp_post.py           # auto-rotate by week of year
  python generate_gbp_post.py 3         # force theme index 0-7

Required environment variable:
  ANTHROPIC_API_KEY

Required for actual posting (set as GitHub secrets):
  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN
  GBP_ACCOUNT_ID, GBP_LOCATION_ID
"""

import anthropic
import os
import sys
from datetime import datetime, timezone, timedelta

import gbp_post


# ---------------------------------------------------------------------------
# 8-week rotating theme schedule
# Each entry drives the Claude prompt + the GBP call-to-action.
# ---------------------------------------------------------------------------
THEMES = [
    {
        "key":      "cybersecurity_alert",
        "label":    "Cybersecurity Alert",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/cybersecurity-services",
        "prompt": """\
Write a Google Business Profile post for a managed IT and cybersecurity company \
in Woodland Hills, CA that has served Los Angeles businesses since 1999.

Theme: Cybersecurity Alert
Goal: raise awareness of a current or evergreen cyber threat targeting small and \
mid-size businesses and position the company as the expert that can help.

Guidelines:
- Open with a striking stat, question, or short warning headline
- Name the specific threat (phishing, ransomware, BEC, MFA fatigue, etc.) \
and explain the real-world risk in 1–2 sentences
- Briefly state what businesses should do right now
- End with: "Book a free 30-min security assessment — no obligation."
- Total length: 300–500 characters (hard cap 1 450 chars to leave room)
- Add 2–3 hashtags at the very end (choose: \
#CybersecurityLA #ITSecurityLA #RansomwareProtection #PhishingProtection \
#ManagedITLA #DataSecurity)
- Plain text only — no markdown, no bullet symbols, no emojis""",
    },
    {
        "key":      "managed_it_value",
        "label":    "Managed IT Value",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/managed-it-services-los-angeles",
        "prompt": """\
Write a Google Business Profile post for a managed IT company in Woodland Hills, CA \
that has served Los Angeles businesses since 1999.

Theme: Why Managed IT beats break-fix
Goal: speak directly to a business owner frustrated with reactive, expensive IT \
and show why a flat-rate MSP model is smarter.

Guidelines:
- Open with a relatable pain point (unexpected IT bill, downtime, slow response)
- Compare reactive "break-fix" costs vs proactive managed IT in 1 concrete way \
(cost, downtime minutes, staff hours, etc.)
- Mention 24/7 monitoring, live engineers (not a ticket queue), and LA-area coverage
- End with a soft CTA: "See what flat-rate IT looks like for your team."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#ManagedITLA #ITSupportLA #LosAngelesBusiness #WoodlandHillsIT
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "cloud_microsoft365",
        "label":    "Cloud & Microsoft 365",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/cloud-services",
        "prompt": """\
Write a Google Business Profile post for a managed IT company in Woodland Hills, CA \
that has served Los Angeles businesses since 1999.

Theme: Cloud & Microsoft 365
Goal: help LA business owners understand a specific cloud or M365 benefit they \
may not be using yet.

Guidelines:
- Focus on ONE concrete benefit: Teams Phone replacing desk phones, SharePoint \
replacing file servers, Autopilot for zero-touch device setup, Co-Pilot for \
productivity — pick whichever feels freshest
- Explain the business outcome (cost, speed, flexibility) in 1–2 sentences
- Mention the company handles the migration, licensing, and ongoing management
- End with: "Ask us about moving your team to the cloud — we handle everything."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#Microsoft365 #CloudServicesLA #ManagedITLA #RemoteWorkLA
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "local_la_focus",
        "label":    "Los Angeles Local Focus",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/managed-it-services-los-angeles",
        "prompt": """\
Write a Google Business Profile post for a managed IT company headquartered in \
Woodland Hills, CA, serving businesses across the greater Los Angeles area since 1999.

Theme: Local LA focus
Goal: reinforce local expertise and community presence for LA-area business owners \
searching for a nearby IT partner.

Guidelines:
- Reference 2–3 specific LA neighborhoods or industries the company serves \
(e.g. Century City financial firms, Burbank entertainment companies, \
Pasadena healthcare, San Fernando Valley manufacturers)
- Mention something specific about LA IT challenges: traffic meaning slow on-site \
response from distant vendors, earthquake/power-outage DR planning, \
diverse compliance needs (HIPAA, entertainment, defense)
- Position the company as the local expert with boots-on-the-ground presence
- End with: "Local IT support — we're in your backyard."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#WoodlandHillsBusiness #LosAngelesIT #SFValleyBusiness #LAManagedIT
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "compliance_corner",
        "label":    "Compliance Corner",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/cybersecurity-services",
        "prompt": """\
Write a Google Business Profile post for a managed IT and cybersecurity company \
in Woodland Hills, CA that has served Los Angeles businesses since 1999.

Theme: IT Compliance
Goal: make a compliance requirement feel relevant and urgent to a non-technical \
LA business owner.

Guidelines:
- Pick ONE regulation or requirement common in LA: \
cyber insurance minimum controls, HIPAA for healthcare, CMMC for defense contractors, \
CCPA/CPRA for California businesses, or SEC cybersecurity disclosure rules
- Explain in plain English what it requires and the real consequence of ignoring it \
(denied insurance claim, audit fine, contract loss)
- Position the company as the guide that makes compliance straightforward
- End with: "We make compliance simple — let's talk."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#CyberInsurance #HIPAACompliance #CMCCCompliance #ITComplianceLA #CybersecurityLA
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "help_desk_support",
        "label":    "24/7 Help Desk",
        "cta_type": "CALL",
        "cta_url":  None,
        "prompt": """\
Write a Google Business Profile post for a managed IT company in Woodland Hills, CA \
that has served Los Angeles businesses since 1999.

Theme: 24/7 live help desk and fast response
Goal: differentiate from offshore ticket-queue IT support by highlighting \
live, US-based engineers available around the clock.

Guidelines:
- Open with the frustration of waiting on hold or submitting a ticket for a \
simple IT problem
- Contrast that with talking to a live engineer within minutes, 24/7
- Mention average response time or the "no ticket queue" approach
- Speak to LA businesses specifically: time zones matter, executives and staff \
can't wait
- End with: "Call us now — a real engineer picks up."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#ITHelpDesk #TechSupportLA #ManagedITLA #24x7Support
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "disaster_recovery",
        "label":    "Backup & Disaster Recovery",
        "cta_type": "LEARN_MORE",
        "cta_url":  "https://prolinksystems.com/backup-disaster-recovery",
        "prompt": """\
Write a Google Business Profile post for a managed IT company in Woodland Hills, CA \
that has served Los Angeles businesses since 1999.

Theme: Backup & Disaster Recovery
Goal: make a business owner viscerally understand the risk of inadequate backup \
and how easy it is to fix with the right partner.

Guidelines:
- Lead with a real-world consequence: the average cost of downtime, a ransomware \
recovery scenario, or an LA earthquake/power event angle
- Briefly explain what a proper BDR solution covers \
(offsite cloud backup, fast restore, tested recovery)
- Mention the company tests backups, not just runs them
- End with: "When was your last backup test? Let's check."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#DisasterRecovery #DataBackupLA #BusinessContinuity #ManagedITLA
- Plain text only — no markdown, no bullets, no emojis""",
    },
    {
        "key":      "free_assessment",
        "label":    "Free IT Assessment Offer",
        "cta_type": "BOOK_APPOINTMENT",
        "cta_url":  "https://prolinksystems.com/contact",
        "prompt": """\
Write a Google Business Profile post for a managed IT company in Woodland Hills, CA \
that has served Los Angeles businesses since 1999.

Theme: Free IT Assessment offer (direct CTA post)
Goal: convert a reader into a booked discovery call with a no-pressure, \
high-value offer.

Guidelines:
- Lead with the offer: a free 30-minute IT assessment or discovery call
- Name 2–3 specific things they'll walk away with: \
a clear picture of security gaps, a cost comparison vs their current setup, \
a plain-English IT roadmap
- Emphasize no sales pressure, no obligation, no jargon
- Include the phone number: 1-800-890-6133
- End with: "Book your free assessment — spots fill fast."
- Total length: 300–500 characters
- Add 2–3 hashtags: \
#FreeITAssessment #ManagedITLA #LosAngelesBusiness #WoodlandHillsIT
- Plain text only — no markdown, no bullets, no emojis""",
    },
]


def pick_theme(index=None):
    """Return the theme for this week. index overrides auto-rotation."""
    if index is not None:
        return THEMES[int(index) % len(THEMES)]
    # Rotate by ISO week number so the same week always picks the same theme
    week = datetime.now(timezone.utc).isocalendar()[1]
    return THEMES[week % len(THEMES)]


def generate_post_text(theme):
    """Call Claude to generate the post text for the given theme."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[{"role": "user", "content": theme["prompt"]}],
    )
    return message.content[0].text.strip()


def main():
    theme_index = None
    if len(sys.argv) > 1:
        try:
            theme_index = int(sys.argv[1])
        except ValueError:
            print(f"Invalid theme index '{sys.argv[1]}'. Using auto-rotation.")

    theme = pick_theme(theme_index)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[gbp] Date: {today}")
    print(f"[gbp] Theme: {theme['label']} (key: {theme['key']})")

    print("[gbp] Generating post content with Claude...")
    try:
        post_text = generate_post_text(theme)
    except Exception as e:
        print(f"[gbp] ERROR: Could not generate post text: {e}")
        sys.exit(1)

    print(f"\n[gbp] --- GENERATED POST ({len(post_text)} chars) ---")
    print(post_text)
    print("[gbp] ---\n")

    result = gbp_post.maybe_post(
        summary=post_text,
        cta_type=theme["cta_type"],
        cta_url=theme.get("cta_url"),
    )

    if result:
        print(f"[gbp] Weekly GBP post published successfully: {result}")
    else:
        print("[gbp] Post was not published (see warnings above).")


if __name__ == "__main__":
    main()
