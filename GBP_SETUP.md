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
