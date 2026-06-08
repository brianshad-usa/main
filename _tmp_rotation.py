import calendar
from datetime import date

N_TOPICS = 30

def topic_for(d):
    return (d.timetuple().tm_yday // 2) % N_TOPICS

year = 2026
all_runs = []          # (date, index)
per_month = {}
prev_idx = None
back_to_back = 0

for m in range(1, 13):
    days_in_month = calendar.monthrange(year, m)[1]
    for day in range(1, days_in_month + 1):
        if day % 2 == 1:            # cron '*/2' on day-of-month => 1,3,5,...
            d = date(year, m, day)
            idx = topic_for(d)
            all_runs.append((d, idx))
            per_month.setdefault(m, []).append(idx)
            if prev_idx is not None and idx == prev_idx:
                back_to_back += 1
                print("BACK-TO-BACK DUP:", d, idx)
            prev_idx = idx

# 1) No same-month duplicate topic
month_dupes = 0
for m, idxs in per_month.items():
    if len(idxs) != len(set(idxs)):
        month_dupes += 1
        print(f"MONTH {m} has duplicate topics: {idxs}")

# 2) Coverage
covered = sorted({i for _, i in all_runs})
print("Total runs in year:", len(all_runs))
print("Posts per month:", {m: len(v) for m, v in per_month.items()})
print("Distinct topics covered:", len(covered), "of", N_TOPICS)
print("First 8 runs:", [(d.isoformat(), i) for d, i in all_runs[:8]])
print("Back-to-back duplicates:", back_to_back)
print("Months with internal duplicate topic:", month_dupes)

assert len(covered) == N_TOPICS, "not all topics covered in a year"
assert back_to_back == 0, "a topic repeated on consecutive runs"
assert month_dupes == 0, "a topic repeated within the same month"
print("\nROTATION_OK")
