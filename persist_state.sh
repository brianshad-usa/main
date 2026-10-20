#!/usr/bin/env bash
# persist_state.sh
# ----------------
# Persist the just-generated social images + editorial ledger/manifests to the
# NON-PROTECTED 'social-state' branch. That branch does two jobs:
#   1. Hosts the card images for the URL-fetch channels (GBP / Instagram /
#      Facebook) at raw.githubusercontent.com/<owner>/<repo>/social-state/social/
#   2. Carries the authoritative dedup ledger (editorial/ledger.json) between runs.
#
# It deliberately NEVER touches protected 'main', so the 'main-protection'
# ruleset cannot block the pipeline. This script is BEST-EFFORT: any failure
# (including a push rejection) prints a ::warning:: and exits 0 so it can never
# fail the run or stop posting. Dedup still survives via the Actions cache even
# if this push is somehow rejected too.
#
# Usage: bash persist_state.sh
set -u
BRANCH="social-state"
REMOTE="origin"

warn() { echo "::warning::persist_state: $*"; }
note() { echo "[persist] $*"; }

git config user.name  "ProLink Social Bot"
git config user.email "actions@users.noreply.github.com"

# Nothing to persist? Then there was no new slot this run (e.g. excellence gate
# skipped the day). Exit clean.
if [ ! -f editorial/ledger.json ] && [ -z "$(ls -A social 2>/dev/null)" ]; then
  note "no state files present; nothing to persist."
  exit 0
fi

WT="$(mktemp -d)"
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; }
trap cleanup EXIT

git fetch --quiet "$REMOTE" "$BRANCH" 2>/dev/null
if git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>&1; then
  note "updating existing $BRANCH branch."
  if ! git worktree add -B "$BRANCH" "$WT" "$REMOTE/$BRANCH" >/dev/null 2>&1; then
    warn "could not create worktree from $REMOTE/$BRANCH; aborting persist (non-fatal)."
    exit 0
  fi
else
  note "$BRANCH does not exist yet; creating it as an orphan."
  if ! git worktree add --detach "$WT" HEAD >/dev/null 2>&1; then
    warn "could not create worktree; aborting persist (non-fatal)."
    exit 0
  fi
  git -C "$WT" checkout --orphan "$BRANCH" >/dev/null 2>&1
  git -C "$WT" rm -rf . >/dev/null 2>&1 || true
fi

# Overlay the fresh state from the (main-based) working tree onto the branch.
mkdir -p "$WT/social" "$WT/editorial/manifests"
cp -a social/. "$WT/social/" 2>/dev/null || true
[ -f editorial/ledger.json ] && cp -a editorial/ledger.json "$WT/editorial/ledger.json"
cp -a editorial/manifests/. "$WT/editorial/manifests/" 2>/dev/null || true

git -C "$WT" add -A social editorial/ledger.json editorial/manifests 2>/dev/null
if git -C "$WT" diff --cached --quiet; then
  note "no changes to persist to $BRANCH."
  exit 0
fi

git -C "$WT" commit --quiet -m "state: editorial content $(date -u +%F)" || {
  warn "commit to $BRANCH failed (non-fatal)."; exit 0; }

# Fast-forward push only (no --force). If the ruleset ever covers this branch
# too, this is where it would be rejected -- which is why dedup also lives in the
# Actions cache. Publishing still proceeds either way.
if git -C "$WT" push "$REMOTE" "HEAD:$BRANCH" 2>&1; then
  note "pushed state to $REMOTE/$BRANCH."
  note "images now served from: https://raw.githubusercontent.com/brianshad-usa/main/$BRANCH/social/"
else
  warn "push to $REMOTE/$BRANCH was rejected or failed. URL-fetch channels (GBP/IG/FB) may 404 this run; LinkedIn (local upload) is unaffected. Dedup is preserved via the Actions cache. If this branch is unexpectedly protected, exclude 'social-state' from the ruleset or add the Actions bot to its bypass."
fi
exit 0
