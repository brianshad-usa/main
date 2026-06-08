import re, os, calendar
from datetime import date

src = open("generate_blog.py", encoding="utf-8").read()
block = src[src.index("other_topics = ["):src.index("# Topic selection.")]
ns = {}
exec(block, ns)
topics, ai_topics, other_topics = ns["topics"], ns["ai_topics"], ns["other_topics"]
N = len(topics)

print(f"other={len(other_topics)} ai={len(ai_topics)} total={N}")
assert N == 95
assert len(topics) == len(set(topics)), "duplicate topic"
assert set(ai_topics) <= set(topics) and set(other_topics) <= set(topics)
assert all(t in ai_topics or t in other_topics for t in topics)

# AI positions within the list + gaps
ai_pos = [i for i, t in enumerate(topics) if t in set(ai_topics)]
gaps = [ai_pos[i+1] - ai_pos[i] for i in range(len(ai_pos)-1)]
print("AI list positions:", ai_pos)
print("Gaps between AI topics:", gaps, "| max gap:", max(gaps))
assert len(ai_pos) == 10
assert max(gaps) <= 11, "AI topics too clustered"

# Rotation across 2 years with the real run-ordinal formula
def topic_for(d):
    pb = sum((calendar.monthrange(d.year, m)[1] + 1) // 2 for m in range(1, d.month))
    return (pb + (d.day + 1)//2 - 1) % N

prev=None; b2b=0; mdupes=0; covered=set()
ai_set = set(ai_topics)
ai_run_days = []  # day-of-year (continuous) for runs that hit an AI topic
run_calendar = []
for year in (2026, 2027):
    per_month = {}
    for m in range(1, 13):
        for day in range(1, calendar.monthrange(year, m)[1]+1):
            if day % 2 == 1:
                idx = topic_for(date(year, m, day))
                if year == 2026: covered.add(idx)
                per_month.setdefault(m, []).append(idx)
                if prev == idx: b2b += 1
                prev = idx
                run_calendar.append((date(year, m, day), topics[idx] in ai_set))
    for m, idxs in per_month.items():
        if len(idxs) != len(set(idxs)): mdupes += 1
assert b2b == 0 and mdupes == 0 and len(covered) == N
print(f"Rotation: covered {len(covered)}/{N}, back-to-back={b2b}, month-dupes={mdupes}")

# AI cadence in the actual publish stream (gap in days between AI posts)
ai_dates = [d for d, is_ai in run_calendar if is_ai]
day_gaps = [(ai_dates[i+1]-ai_dates[i]).days for i in range(len(ai_dates)-1)]
ai_2026 = [d for d in ai_dates if d.year == 2026]
print(f"AI posts in 2026: {len(ai_2026)} | gap between AI posts: ~{min(day_gaps)}-{max(day_gaps)} days")
print("First 6 AI post dates:", [d.isoformat() for d in ai_dates[:6]])
assert max(day_gaps) <= 24, "AI gap too large"
print("\nALL_AI_OK")
