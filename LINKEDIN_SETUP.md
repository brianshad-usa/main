# Auto-posting blog articles to the company LinkedIn Page

Each month the GitHub Action that generates a new blog post will also publish
it to the Pro Link Systems LinkedIn **Company Page** automatically. This file
is the one-time setup. Budget ~30 minutes, plus possible wait time for LinkedIn
to approve the API product.

You only need to do **Steps 1–6 once**. After that it runs itself for ~12 months
until the refresh token expires, at which point you re-run one script (Step 4).

---

## What was already built (no action needed)

- `generate_blog.py` now also asks Claude for a LinkedIn caption and, after the
  post is live, calls the poster.
- `linkedin_post.py` handles token refresh + publishing. **If anything LinkedIn
  is missing or broken, the blog still publishes — the LinkedIn step just skips.**
- `linkedin_auth.py` is the one-time token helper you run in Step 4.
- `.github/workflows/generate-blog.yml` passes the LinkedIn secrets to the run.

---

## Step 1 — Create the LinkedIn app

1. Go to **https://www.linkedin.com/developers/apps** and click **Create app**.
2. Fill in:
   - **App name:** `Pro Link Systems Blog Bot` (anything works)
   - **LinkedIn Page:** select your **Pro Link Systems** company page. *(This is
     what ties the app to the page you'll post to — it must be your real page.)*
   - **App logo:** upload the logo.
   - Accept the legal terms and **Create app**.
3. On the app's **Settings** tab, find **Verify** next to your Page and click it.
   It generates a link; open that link as a **Page admin** and confirm. The app
   now shows "Verified."

## Step 2 — Request the Community Management API

1. Open the app's **Products** tab.
2. Find **Community Management API** and click **Request access**.
3. Complete the short form. For a Page you administer, access is often granted
   right away; occasionally LinkedIn reviews it over a few business days. You'll
   get an email and the product will show as **Added** when ready.
   - *(The "Share on LinkedIn" / "Sign In with LinkedIn" products are NOT enough —
     they only post as a person. You specifically need Community Management API to
     post as the Company Page.)*

## Step 3 — Configure Auth + grab your keys

1. Open the app's **Auth** tab.
2. Under **OAuth 2.0 settings → Authorized redirect URLs**, add exactly:
   ```
   http://localhost:8000/callback
   ```
   Save.
3. Copy your **Client ID** and **Primary Client Secret** (you'll need them next).
4. Confirm that under **OAuth 2.0 scopes** you now see
   `w_organization_social` and `r_organization_social`. If they're missing,
   Step 2 hasn't finished approving yet — wait for it.

## Step 4 — Generate your tokens (run the helper once)

On your own computer, from the repo's `main` folder:

**Windows PowerShell**
```powershell
$env:LINKEDIN_CLIENT_ID="paste-client-id"
$env:LINKEDIN_CLIENT_SECRET="paste-client-secret"
python linkedin_auth.py
```

A browser opens → approve the permissions → the terminal prints your
**LINKEDIN_ACCESS_TOKEN** and **LINKEDIN_REFRESH_TOKEN**. Keep that window open
for the next step.

## Step 5 — Company Page (Organization) ID — ALREADY DONE

Your Organization ID is **`3574099`** (from your admin URL
`linkedin.com/company/3574099/admin/`). It's already baked into `linkedin_post.py`
as the default, so **you don't need to add a secret for it.** (If the page ever
changes, set a `LINKEDIN_ORG_ID` secret to override.)

## Step 6 — Add the GitHub secrets

In the repo on GitHub: **Settings → Secrets and variables → Actions → New
repository secret**. Add each of these:

| Secret name | Value |
|---|---|
| `LINKEDIN_CLIENT_ID` | from Step 3 |
| `LINKEDIN_CLIENT_SECRET` | from Step 3 |
| `LINKEDIN_REFRESH_TOKEN` | from Step 4 |
| `LINKEDIN_ACCESS_TOKEN` | from Step 4 (fallback; optional but recommended) |
| `LINKEDIN_ORG_ID` | the number from Step 5 |

*(`ANTHROPIC_API_KEY` is already set from the blog automation.)*

That's it — you're live.

---

## Test it now (don't wait a month)

1. GitHub → **Actions** → **Generate Blog Post** → **Run workflow**. You can put a
   `topic_index` (e.g. `5`) to control which topic, or leave it blank.
2. Watch the run log. In the "Generate and publish blog post" step you'll see
   `[linkedin] Refreshing access token...` and `[linkedin] Published to LinkedIn.
   Post id: ...` on success.
3. Check the company page — the post appears with a link-preview card.

> Heads up: each manual run also creates a real blog post and a real LinkedIn
> post. Use it sparingly for testing, or delete the test post/article afterward.

---

## Yearly maintenance

The **refresh token lasts ~365 days**. About once a year the LinkedIn step will
start logging an auth error (the blog keeps publishing fine). When that happens,
just re-run **Step 4** and update the `LINKEDIN_REFRESH_TOKEN` (and
`LINKEDIN_ACCESS_TOKEN`) secrets with the new values. Two minutes, once a year.

If a run log ever prints `NOTE: LinkedIn returned a NEW refresh token`, copy that
value into the `LINKEDIN_REFRESH_TOKEN` secret to keep the clock from resetting
early.

---

## Troubleshooting

| Symptom in the Action log | Fix |
|---|---|
| `Skipping LinkedIn post (LINKEDIN_ORG_ID not configured)` | Add the `LINKEDIN_ORG_ID` secret (Step 5–6). |
| `LinkedIn API 401` / `Refresh failed` | Token expired or revoked — re-run Step 4, update the secrets. |
| `LinkedIn API 403` `ACCESS_DENIED` | App isn't approved for Community Management API yet, or you're not a Page admin (Steps 1–2). |
| `LinkedIn API 426` / version error | Bump the LinkedIn version: add a `LINKEDIN_API_VERSION` secret like `202507`. |
| Post text shows stray `\` characters | A reserved character slipped through; tell me and I'll adjust the escaper. |

The golden rule: **a LinkedIn failure never stops the blog from publishing.**
You'll see a `[linkedin] WARNING:` line and the rest of the run succeeds.
