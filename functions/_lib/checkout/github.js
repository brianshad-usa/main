/**
 * Hand-off: open a GitHub issue in a PRIVATE repository (the M365 assessment agent watches
 * brianshad-usa/m365-security-agent for "[order]" issues). Not a route.
 *
 * The token is a fine-grained token limited to that one repository with Issues read/write
 * (plus GitHub's mandatory Metadata read). It cannot run workflows, read code or approve
 * anything; Pro Link's approval and the report release are separate manual steps.
 *
 * Returns { ok, ref, issueNumber, existing } or { ok:false, transient, reason }.
 * transient = worth a retry (GitHub down / rate-limited): the webhook then answers non-200
 * so Authorize.net retries. Anything else is a configuration problem for a human.
 */
const GH = "https://api.github.com";

function headers(token, withBody) {
  const h = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "prolinksystems-checkout",
  };
  if (withBody) h["Content-Type"] = "application/json";
  return h;
}

const transientStatus = (s) => s >= 500 || s === 429;

export async function githubIssueHandoff(env, cfg, order) {
  const token = env[cfg.tokenEnv];
  if (!token) return { ok: false, transient: false, reason: `${cfg.tokenEnv} is not set` };
  let r;

  // 1) Privacy guard: the issue carries the customer's name, email, phone and IP.
  //    Never post it unless the repository is private.
  try {
    r = await fetch(`${GH}/repos/${cfg.repo}`, { headers: headers(token) });
  } catch (e) {
    return { ok: false, transient: true, reason: "GitHub unreachable" };
  }
  if (!r.ok) return { ok: false, transient: transientStatus(r.status), reason: `GitHub repo check returned ${r.status}` };
  const repo = await r.json().catch(() => ({}));
  if (repo.private !== true) {
    return { ok: false, transient: false, reason: `${cfg.repo} is not private; refusing to post customer details` };
  }

  // 2) Already handed off? A previous attempt may have created the issue and then failed
  //    to record it. The newest 50 issues (open and closed) are plenty for that window.
  try {
    r = await fetch(`${GH}/repos/${cfg.repo}/issues?state=all&per_page=50&sort=created&direction=desc`, { headers: headers(token) });
    if (r.ok) {
      const list = await r.json();
      const hit = Array.isArray(list) && list.find((i) => i && !i.pull_request && typeof i.title === "string" &&
        i.title.startsWith(cfg.titlePrefix) && i.title.includes(order.order_id));
      if (hit) return { ok: true, existing: true, issueNumber: hit.number, ref: `${cfg.repo}#${hit.number}` };
    }
  } catch (e) { /* fall through: creating is still right */ }

  // 3) Create it.
  try {
    r = await fetch(`${GH}/repos/${cfg.repo}/issues`, {
      method: "POST",
      headers: headers(token, true),
      body: JSON.stringify({ title: cfg.title(order), body: cfg.body(order) }),
    });
  } catch (e) {
    return { ok: false, transient: true, reason: "GitHub unreachable" };
  }
  if (r.status === 201) {
    const d = await r.json().catch(() => ({}));
    return { ok: true, issueNumber: d.number, ref: `${cfg.repo}#${d.number}` };
  }
  return { ok: false, transient: transientStatus(r.status), reason: `GitHub create-issue returned ${r.status}` };
}
