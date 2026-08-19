"""
editorial_engine.py
-------------------
Topic intelligence for the social pipeline: selects WHAT to publish next.

Replaces the fixed 8-theme day-of-year rotation with ranked selection from
social_backlog.json (258 qualified ideas), moderated by the published ledger:

  * composite score       - weighted editorial scoring from the backlog
  * recency decay         - an idea published in the last 26 weeks is blocked;
                            its theme is dampened for 3 cycles, its format for 2
  * seasonal windows      - seasonal ideas surge inside their months and are
                            excluded outside them
  * timeliness mix        - keeps a deliberate balance of evergreen / timely
                            instead of letting one fashionable subject (esp. AI)
                            consume the calendar
  * anti-repetition       - hard block on same idea, same theme twice running,
                            or a third AI-themed post inside any rolling five

The ledger (editorial/ledger.json) is append-only and committed by the
workflow, so selection state survives between CI runs the same way
used_topics.json does for the blog bot.

Deterministic given (backlog, ledger, date) - no randomness, so a re-run of a
failed workflow picks the same topic instead of silently switching subjects.

Usage:
    python editorial_engine.py            # print today's selection (no writes)
    python editorial_engine.py --explain  # show the full ranked shortlist
"""

import os
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKLOG_PATH = os.path.join(HERE, "social_backlog.json")
LEDGER_PATH = os.path.join(HERE, "editorial", "ledger.json")

# AI-adjacent themes share a fatigue pool so "balance the mix" has teeth.
AI_THEMES = {"ai_governance", "ai_threats"}

# How many recent posts to consider for theme/format fatigue.
FATIGUE_WINDOW = 5
IDEA_COOLDOWN_DAYS = 182          # same idea: hard block ~26 weeks
THEME_REPEAT_PENALTY = 2.5        # last post's theme
THEME_RECENT_PENALTY = 1.2        # theme appeared in the fatigue window
FORMAT_RECENT_PENALTY = 0.8       # format appeared in the last 2 posts
SEASONAL_BOOST = 1.5
TIMELY_SHARE_TARGET = 0.4         # aim: ~40% timely, 60% evergreen


def _load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def load_backlog():
    return _load(BACKLOG_PATH, {"ideas": [], "scoring": {"weights": {}}})


def load_ledger():
    return _load(LEDGER_PATH, {"posts": []})


def save_ledger(ledger):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")


def composite(idea, weights):
    s = idea.get("s", {})
    total, wsum = 0.0, 0.0
    for k, w in weights.items():
        total += w * float(s.get(k, 5))
        wsum += w
    return round(total / wsum, 3) if wsum else 0.0


def record_publication(idea, excellence=None, channels=None, today=None, variety=None):
    """Append a published (or generated-for-publish) item to the ledger.

    variety (optional): the visual-style/format directive from social_variety,
    persisted so the next run can avoid repeating the same look per channel.
    """
    ledger = load_ledger()
    entry = {
        "date": (today or datetime.date.today()).isoformat(),
        "idea_id": idea["id"],
        "theme": idea["theme"],
        "format": idea["format"],
        "title": idea["title"],
        "excellence": excellence,
        "channels": channels or [],
    }
    if variety:
        entry["variety"] = variety
    ledger["posts"].append(entry)
    save_ledger(ledger)


def select(today=None, explain=False):
    """Rank the backlog against the ledger; return (idea, shortlist)."""
    today = today or datetime.date.today()
    backlog = load_backlog()
    weights = backlog.get("scoring", {}).get("weights", {})
    ledger = load_ledger()
    posts = ledger.get("posts", [])
    recent = posts[-FATIGUE_WINDOW:]
    recent_themes = [p["theme"] for p in recent]
    recent_formats = [p["format"] for p in recent[-2:]]
    last_theme = recent_themes[-1] if recent_themes else None
    recent_ai = sum(1 for t in recent_themes if t in AI_THEMES)
    timely_recent = sum(1 for p in recent if p.get("timeliness") == "timely")

    published_dates = {}
    for p in posts:
        published_dates[p["idea_id"]] = p["date"]

    shortlist = []
    for idea in backlog.get("ideas", []):
        why = []

        # Hard blocks -----------------------------------------------------
        last = published_dates.get(idea["id"])
        if last:
            age = (today - datetime.date.fromisoformat(last)).days
            if age < IDEA_COOLDOWN_DAYS:
                continue
        months = idea.get("seasonal_months")
        if months and today.month not in months:
            continue
        if idea["theme"] == last_theme and last_theme is not None:
            continue  # never the same theme twice running
        if idea["theme"] in AI_THEMES and recent_ai >= 2:
            continue  # a third AI post in five would let AI eat the calendar

        # Soft scoring ----------------------------------------------------
        score = composite(idea, weights)
        why.append(f"composite {score}")

        if idea["theme"] in recent_themes:
            score -= THEME_RECENT_PENALTY
            why.append(f"theme fatigue -{THEME_RECENT_PENALTY}")
        if idea["format"] in recent_formats:
            score -= FORMAT_RECENT_PENALTY
            why.append(f"format fatigue -{FORMAT_RECENT_PENALTY}")
        if months and today.month in months:
            score += SEASONAL_BOOST
            why.append(f"in season +{SEASONAL_BOOST}")

        timely = idea.get("timeliness") == "timely"
        timely_share = timely_recent / max(len(recent), 1)
        if timely and timely_share < TIMELY_SHARE_TARGET:
            score += 0.6
            why.append("timely mix boost +0.6")
        elif timely and timely_share > TIMELY_SHARE_TARGET:
            score -= 0.4
            why.append("timely mix damp -0.4")

        shortlist.append((round(score, 3), idea, why))

    shortlist.sort(key=lambda t: (-t[0], t[1]["id"]))
    if not shortlist:
        raise SystemExit("editorial_engine: nothing selectable - backlog exhausted or over-filtered.")

    if explain:
        for score, idea, why in shortlist[:12]:
            print(f"{score:6.2f}  {idea['id']}  [{idea['theme']}/{idea['format']}]  "
                  f"{idea['title']}   ({'; '.join(why)})")

    return shortlist[0][1], shortlist


if __name__ == "__main__":
    import sys
    idea, ranked = select(explain="--explain" in sys.argv)
    print(json.dumps(idea, indent=2, ensure_ascii=False))
