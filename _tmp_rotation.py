import calendar
from datetime import date

N_TOPICS = 30

def topic_for(d):
    posts_before = sum((calendar.monthrange(d.year, m)[1] + 1) // 2 for m in range(1, d.month))
    posts_this = (d.day + 1) // 2
    run_number = posts_before + posts_this
    return (run_number - 1) % N_TOPICS

# Test across two consecutive years to also cover the Dec->Jan boundary.
prev = None
back_to_back = 0
month_dupes = 0
total = 0
covered_2026 = set()

for year in (2026, 2027):
    per_month = {}
    for m in range(1, 13):
        for day in range(1, calendar.monthrange(year, m)[1] + 1):
            if day % 2 == 1:                    # cron '*/2' on day-of-month
                d = date(year, m, day)
                idx = topic_for(d)
                total += 1
                if year == 2026:
                    covered_2026.add(idx)
                per_month.setdefault(m, []).append(idx)
                if prev == idx:
                    back_to_back += 1
                    print("BACK-TO-BACK DUP:", d, idx)
                prev = idx
    for m, idxs in per_month.items():
        if len(idxs) != len(set(idxs)):
            month_dupes += 1
            print(f"{year}-{m:02d} duplicate topics within month:", idxs)

print("Total runs over 2 yrs:", total)
print("Distinct topics covered in 2026:", len(covered_2026), "of", N_TOPICS)
print("Back-to-back duplicates:", back_to_back)
print("Months with internal duplicate topic:", month_dupes)

assert len(covered_2026) == N_TOPICS
assert back_to_back == 0
assert month_dupes == 0
print("\nROTATION_OK")
