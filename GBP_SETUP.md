# Auto-posting weekly updates to Google Business Profile

Every Tuesday at 10 AM LA time GitHub Actions generates a post with Claude
and publishes it to your GBP listing automatically, cycling through 8 themes:

| Week % 8 | Theme |
|---|---|
| 0 | Cybersecurity Alert |
| 1 | Managed IT Value (break-fix vs MSP) |
| 2 | Cloud & Microsoft 365 |
| 3 | Local Los Angeles Focus |
| 4 | Compliance Corner (HIPAA / cyber insurance) |
| 5 | 24/7 Help Desk |
| 6 | Backup & Disaster Recovery |
| 7 | Free IT Assessment Offer |

You only need to do **Steps 1–5 once**. After that it runs itself indefinitely
(Google refresh tokens don't expire as long as the app is used at least once
every 6 months — which the weekly cron ensures automatically).

---

## Step 1 — Create a Google Cloud project

1. Go to **https://console.cloud.google.com/** and create a new project
   (e.g. "ProLink GBP Bot").
2. In the left menu go to **APIs & Services → Library**.
3. Search for **"My Business Business Information API"** and enable it.
4. Also enable **"My Business Account Management API"**.
   *(Both are needed to read account/location IDs and post updates.)*

## Step 2 — Create OAuth credentials

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** user type → fill in App name ("ProLink GBP Bot"),
   support email, and your email as developer contact. Save.
3. On the **Scopes** step add: `https://www.googleapis.com/auth/business.manage`
4. On the **Test users** step add your Google account email. Save.
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
6. Application type: **Desktop app**. Name it anything. Click **Create**.
7. Copy your **Client ID** and **Client Secret** — you'll need them next.

## Step 3 — Generate your tokens (run once on your computer)

In the repo's `main` folder, run:

**Windows PowerShell:**
```powershell
$env:GBP_CLIENT_ID="paste-client-id"
$env:GBP_CLIENT_SECRET="paste-client-secret"
python gbp_auth.py
```

A browser opens → sign in as the Google account that manages the GBP listing
→ click **Allow** → the terminal prints your **GBP_REFRESH_TOKEN**.

## Step 4 — Find your Account ID and Location ID

You need these two IDs once to configure the secrets.

**Option A — from the GBP website:**
1. Go to **https://business.google.com/**
2. Open your listing. Look at the URL:
   `business.google.com/dashboard/l/LOCATION_ID/...`
   That number is your **Location ID**.
3. For the Account ID, open your browser DevTools (F12) → Network tab → reload
   the page → filter for `accounts` → find a request to
   `mybusiness.googleapis.com/v4/accounts`. The response contains
   `"name": "accounts/ACCOUNT_ID"`.

**Option B — run the discovery helper** (after Step 3 tokens are set):
```powershell
$env:GBP_CLIENT_ID="xxxx"
$env:GBP_CLIENT_SECRET="yyyy"
$env:GBP_REFRESH_TOKEN="zzzz"
python - <<'EOF'
import os, json, urllib.request, urllib.parse
import gbp_post
token = gbp_post._resolve_access_token()
req = urllib.request.Request(
    "https://mybusiness.googleapis.com/v4/accounts",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
for acct in data.get("accounts", []):
    print("Account:", acct["name"])
    loc_url = f"https://mybusiness.googleapis.com/v4/{acct['name']}/locations"
    req2 = urllib.request.Request(loc_url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req2) as r2:
        locs = json.loads(r2.read())
    for loc in locs.get("locations", []):
        print("  Location:", loc["name"], "|", loc.get("title",""))
EOF
```

The output looks like:
```
Account: accounts/123456789
  Location: accounts/123456789/locations/987654321 | Pro Link Systems
```

Your **GBP_ACCOUNT_ID** = `123456789`
Your **GBP_LOCATION_ID** = `987654321`

## Step 5 — Add GitHub secrets

In the repo on GitHub: **Settings → Secrets and variables → Actions → New
repository secret**. Add each of these:

| Secret name | Value |
|---|---|
| `GBP_CLIENT_ID` | from Step 2 |
| `GBP_CLIENT_SECRET` | from Step 2 |
| `GBP_REFRESH_TOKEN` | from Step 3 |
| `GBP_ACCOUNT_ID` | from Step 4 |
| `GBP_LOCATION_ID` | from Step 4 |
| `GBP_ACCESS_TOKEN` | from Step 3 (optional fallback) |

`ANTHROPIC_API_KEY` is already set from the blog automation.

That's it — you're live. Every Tuesday at 10 AM LA time a post goes up.

---

## Test it now (without waiting for Tuesday)

1. GitHub → **Actions** → **Weekly GBP Post** → **Run workflow**.
2. Optional: enter a `theme_index` (0–7) to test a specific theme.
3. Watch the run log for `[gbp] Published GBP post: accounts/…`.
4. Check your GBP listing — the post appears within a minute.

> Each manual run creates a real live GBP post. Delete it from GBP afterward
> if you're just testing.

---

## Run a specific theme manually from your computer

```powershell
# Set credentials
$env:GBP_CLIENT_ID="xxxx"
$env:GBP_CLIENT_SECRET="yyyy"
$env:GBP_REFRESH_TOKEN="zzzz"
$env:GBP_ACCOUNT_ID="123456789"
$env:GBP_LOCATION_ID="987654321"
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Theme index 0-7 (or omit for this week's auto theme)
python generate_gbp_post.py 7
```

---

## Troubleshooting

| Error in Action log | Fix |
|---|---|
| `Skipping GBP post (no GBP_REFRESH_TOKEN/ACCESS_TOKEN)` | Tokens not set — finish Steps 3 + 5. |
| `GBP API 401` | Refresh token revoked or expired — re-run Step 3, update the secret. |
| `GBP API 403` | The Google account used in Step 3 isn't a manager of the GBP listing. |
| `GBP API 404` | Wrong Account ID or Location ID — re-check Step 4. |
| `No access_token in Google response` | Client ID / Secret mismatch — re-check Step 2. |
| Post doesn't appear on GBP | GBP can take up to 10 minutes to surface new posts. |

**The golden rule:** a GBP failure never stops any other automation.
The script logs a `[gbp] WARNING:` line and exits cleanly.

---

## Enabling GBP on the DAILY social pipeline (current path)

The GBP channel is already fully wired into the **Social Posts (Daily)**
workflow (`social-3x-week.yml` → `content_studio.py` → `social_publish.py`).
`content_studio.py` already writes a GBP-specific caption (`channels.gbp`,
300–700 chars) plus `cta_type` / `cta_url`, and `social_publish.py` already
calls `gbp_post.maybe_post(...)`. The workflow already passes every `GBP_*`
secret into the publish step. **No code change is needed to turn it on** — the
channel prints `[skipped] GBP (not configured)` only because the secrets below
are not yet set in `brianshad-usa/main`. Add them and GBP posts automatically
on the existing daily schedule (17:00 UTC / 10 AM LA). No separate cron.

> Cadence note: Google recommends not over-posting. Daily is fine for a single
> location, but if the profile ever looks spammy, gate GBP to e.g. 3×/week by
> adding a weekday check in `social_publish.py` rather than a new workflow.

### Reuse the war-room GBP token (fastest path — no new OAuth)

The war room (`brianshad-usa/prolink-warroom`) already has a working
`GBP_REFRESH_TOKEN` with the `business.manage` scope, minted by
`cmo/seo-intel/mint_gbp_token.py` against the **Google Ads OAuth client in
Cloud project 6748977141**. That same token creates local posts — reuse it.

**Critical:** a refresh token only works with the **same OAuth client** that
minted it. So `GBP_CLIENT_ID` / `GBP_CLIENT_SECRET` here must be that Ads
OAuth client's id/secret (project 6748977141) — **not** a new "Desktop app"
client. Copy all three from the war room together.

### Secrets to add to `brianshad-usa/main`

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value / where to get it |
|---|---|
| `GBP_REFRESH_TOKEN` | copy the war room's `GBP_REFRESH_TOKEN` verbatim |
| `GBP_CLIENT_ID` | the Ads OAuth client ID from project 6748977141 (same client that minted the token) |
| `GBP_CLIENT_SECRET` | that client's secret |
| `GBP_ACCOUNT_ID` | numeric account id — the number after `accounts/` (get it with `gbp_discover.py`, below) |
| `GBP_LOCATION_ID` | the Pro Link Systems location id = **7712242499324845523** (the number after `locations/`) |

`GBP_LOCATION_ID` is ProLink's Business ID (Woodland Hills). If a call returns
404, the account id is likely the issue, not the location — run discovery.

**Find `GBP_ACCOUNT_ID`** (run once locally, with the three token secrets set
in your shell):
```powershell
$env:GBP_CLIENT_ID="..."; $env:GBP_CLIENT_SECRET="..."; $env:GBP_REFRESH_TOKEN="..."
python gbp_discover.py
```
It prints `Account: accounts/NNNN` (that `NNNN` is `GBP_ACCOUNT_ID`) and each
`Location: accounts/NNNN/locations/MMMM`.

### Verify BEFORE going live (no post is created)

```powershell
$env:GBP_CLIENT_ID="..."; $env:GBP_CLIENT_SECRET="..."; $env:GBP_REFRESH_TOKEN="..."
$env:GBP_ACCOUNT_ID="..."; $env:GBP_LOCATION_ID="7712242499324845523"
python gbp_post.py --check
```
`--check` does a read-only `GET` on the location's `localPosts`. It never
writes to the profile. Read the result:

* `[check] OK ...` → token valid, project allowlisted, IDs correct — **ready**.
* `[check] FAIL: GBP API 403 ...` → **the biggest risk**: Cloud project
  6748977141 is not allowlisted for local posts (quota 0). Even though the war
  room reads GBP data fine, each of Google's Business Profile APIs is enabled
  and quota-gated **separately**. Enable the **"Google My Business API"**
  (legacy v4, which hosts `localPosts`) in project 6748977141, and if quota is
  still 0, submit the **Business Profile API access request form**
  (support.google.com/business/contact/api_default). Approval is manual and
  takes days to ~2 weeks — there is no way around it.
* `401` → client id/secret don't match the client that minted the token.
* `404` → wrong `GBP_ACCOUNT_ID` — re-run `gbp_discover.py`.

Once `--check` prints OK, the daily workflow will post to GBP on its next run
with zero further changes.
