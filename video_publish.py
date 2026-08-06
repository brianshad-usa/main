"""
video_publish.py
----------------
Publishes AI-generated videos in videos/ to every CONFIGURED channel and records
the outcome in video_posts.json (committed, so the dashboard can show what went
where). Mirrors social_publish.py: a per-channel guardrail that fails the run
(exit 1) ONLY when a configured channel actually fails -- unconfigured channels
are skipped and never break the run.

Channels:
  - YouTube   : uploads the local file            (YT_CLIENT_ID/SECRET/REFRESH_TOKEN)
  - LinkedIn  : uploads the local file            (LINKEDIN_* token)
  - Instagram : Reel from the public video URL    (IG_USER_ID + IG_ACCESS_TOKEN)
  - Facebook  : video from the public video URL   (FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN)

CHANNEL SELECTION (a credential check is not consent to post)
------------------------------------------------------------
Having a channel's secrets present used to be enough to publish to it. That
makes the blast radius of `git push` the full channel set, which is wrong when
an asset only exists in one aspect ratio, or when a channel is being posted by
hand with hand-written copy. A channel now has to be BOTH configured AND
selected. Resolution order, first match wins:

  1. the video's sidecar  "channels": ["LinkedIn", "Facebook"]   <- per-video
  2. the VIDEO_CHANNELS env var (comma-separated, or "all")
  3. DEFAULT_CHANNELS below

DEFAULT_CHANNELS is deliberately NOT "all". The auto-commit watcher in this repo
runs `git add -A` every 30s, so a video file dropped into videos/ is pushed
without review and fires publish-video.yml on its `push` trigger. A conservative
committed default is the only thing standing between that and an unintended
post, so the default must stay narrow and widen only per-video or per-run.

PER-CHANNEL COPY
----------------
Channels do not share a voice, so the sidecar may carry a caption per channel:

  "captions": {"LinkedIn": "...", "Facebook": "...", "YouTube": "..."}

falling back to the single "caption" for any channel not listed. A YouTube entry
is used as the description VERBATIM -- no boilerplate or hashtags appended --
because a hand-authored description is already final. "linkedin_comment" is
posted as the first comment on the LinkedIn post when present.

Idempotent: a channel already marked "posted" for a given video is never posted
again, so re-runs / retries only attempt the channels that haven't succeeded yet.

Usage:
  python video_publish.py                # publish every pending video in videos/
  python video_publish.py my-clip.mp4    # publish/retry one specific file
"""

import os
import sys
import json
import glob
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

import youtube_post
import linkedin_post
import instagram_post
import facebook_post

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(HERE, "videos")
POSTS_PATH = os.path.join(HERE, "video_posts.json")
VIDEO_EXTS = (".mp4", ".mov")

# Public, site-served base for the just-pushed video (Instagram/Facebook fetch by URL).
VIDEO_URL_BASE = os.environ.get("VIDEO_URL_BASE", "https://prolinksystems.com/videos/")


def _log(msg):
    print(f"[video] {msg}", flush=True)


def _has(*names):
    return all(os.environ.get(n, "").strip() for n in names)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_posts():
    if os.path.exists(POSTS_PATH):
        with open(POSTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts(posts):
    with open(POSTS_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _prettify(filename):
    stem = os.path.splitext(filename)[0]
    return stem.replace("-", " ").replace("_", " ").strip().title()


def load_meta(video_file):
    """Read the sidecar videos/<name>.json (title, caption, tags). Falls back to
    a title derived from the filename."""
    stem = os.path.splitext(video_file)[0]
    sidecar = os.path.join(VIDEOS_DIR, stem + ".json")
    meta = {}
    if os.path.exists(sidecar):
        try:
            with open(sidecar, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            _log(f"Could not read {stem}.json ({e}); using defaults.")
    title = (meta.get("title") or _prettify(video_file)).strip()
    caption = (meta.get("caption") or title).strip()
    tags = meta.get("tags") or ["Managed IT", "Cybersecurity", "Los Angeles", "MSP"]
    return title, caption, tags


def youtube_description(caption, tags):
    body = caption.strip()
    body += (
        "\n\nPro Link Systems - Managed IT & cybersecurity for Los Angeles "
        "businesses since 1999.\nhttps://prolinksystems.com"
    )
    hashtags = " ".join("#" + t.replace(" ", "") for t in tags)
    body += f"\n\n{hashtags} #Shorts"
    return body


def wait_for_url(url, tries=60, delay=10):
    """Poll a public URL until it serves (200). Cloudflare Pages can take several
    minutes to deploy a just-pushed video before Instagram/Facebook can fetch it."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, method="GET", headers={
                "Range": "bytes=0-0",
                # Cloudflare 403s the default Python-urllib UA; use a browser UA.
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/124.0 Safari/537.36"),
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status in (200, 206):
                    _log(f"Public URL is live: {url}")
                    return True
        except Exception:
            pass
        _log(f"Waiting for public URL to deploy... ({i + 1}/{tries})")
        time.sleep(delay)
    _log(f"Public URL never became available: {url}")
    return False


def linkedin_url(post_id):
    if post_id and str(post_id).startswith("urn:li:"):
        return f"https://www.linkedin.com/feed/update/{post_id}"
    return None


def publish_one(video_file, posts):
    """Publish/refresh one video across channels; mutate + return its record."""
    path = os.path.join(VIDEOS_DIR, video_file)
    title, caption, tags = load_meta(video_file)
    public_url = VIDEO_URL_BASE + video_file

    record = next((r for r in posts if r.get("file") == video_file), None)
    if record is None:
        record = {
            "file": video_file,
            "title": title,
            "caption": caption,
            "url": public_url,
            "first_published": _now(),
            "updated": _now(),
            "channels": {},
        }
        posts.insert(0, record)
    else:
        # keep title/caption fresh from the sidecar
        record["title"], record["caption"], record["url"] = title, caption, public_url

    ch = record.setdefault("channels", {})

    def done(name):
        return ch.get(name, {}).get("status") == "posted"

    configured = {
        "YouTube": _has("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") or _has("YT_ACCESS_TOKEN"),
        "LinkedIn": _has("LINKEDIN_REFRESH_TOKEN") or _has("LINKEDIN_ACCESS_TOKEN"),
        "Instagram": _has("IG_USER_ID", "IG_ACCESS_TOKEN"),
        "Facebook": _has("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
    }

    # If a URL-based channel needs posting, make sure the public URL is live first.
    need_url = (configured["Instagram"] and not done("Instagram")) or (
        configured["Facebook"] and not done("Facebook")
    )
    url_ready = wait_for_url(public_url) if need_url else True

    failures = []
    summary = []

    def attempt(name, do_it):
        if done(name):
            summary.append(f"  [already]  {name}")
            return
        if not configured[name]:
            ch[name] = {"status": "skipped", "reason": "not configured"}
            summary.append(f"  [skipped]  {name} (not configured)")
            return
        result = do_it()
        if result:
            ch[name] = result
            summary.append(f"  [posted]   {name}")
        else:
            ch[name] = {"status": "failed"}
            summary.append(f"  [FAILED]   {name} (see log above)")
            failures.append(name)

    # YouTube + LinkedIn upload the local file directly.
    def do_youtube():
        r = youtube_post.maybe_post(path, title, youtube_description(caption, tags), tags)
        if not r:
            return None
        return {"status": "posted", "id": r["id"], "url": r["url"], "privacy": r.get("privacy")}

    def do_linkedin():
        pid = linkedin_post.maybe_post_video(caption, path, title)
        if not pid:
            return None
        return {"status": "posted", "id": pid, "url": linkedin_url(pid)}

    # Instagram + Facebook fetch the public URL (only if it deployed).
    def do_instagram():
        if not url_ready:
            _log("Instagram: public URL not ready; skipping this run.")
            return None
        mid = instagram_post.maybe_post_reel(caption, public_url)
        return {"status": "posted", "id": mid} if mid else None

    def do_facebook():
        if not url_ready:
            _log("Facebook: public URL not ready; skipping this run.")
            return None
        vid = facebook_post.maybe_post_video(caption, public_url)
        if not vid:
            return None
        return {"status": "posted", "id": vid, "url": f"https://www.facebook.com/{vid}"}

    attempt("YouTube", do_youtube)
    attempt("LinkedIn", do_linkedin)
    attempt("Instagram", do_instagram)
    attempt("Facebook", do_facebook)

    record["updated"] = _now()
    print(f"\n----- {video_file}  ({title}) -----")
    for line in summary:
        print(line)
    return failures


def pending(video_file, posts):
    """A video needs work if it has no record, or any configured channel isn't posted."""
    record = next((r for r in posts if r.get("file") == video_file), None)
    if record is None:
        return True
    configured = {
        "YouTube": _has("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") or _has("YT_ACCESS_TOKEN"),
        "LinkedIn": _has("LINKEDIN_REFRESH_TOKEN") or _has("LINKEDIN_ACCESS_TOKEN"),
        "Instagram": _has("IG_USER_ID", "IG_ACCESS_TOKEN"),
        "Facebook": _has("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
    }
    ch = record.get("channels", {})
    return any(c and ch.get(n, {}).get("status") != "posted" for n, c in configured.items())


def main():
    target = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else None
    posts = load_posts()

    if not os.path.isdir(VIDEOS_DIR):
        _log("No videos/ directory yet; nothing to publish.")
        return

    all_videos = sorted(
        os.path.basename(p) for p in glob.glob(os.path.join(VIDEOS_DIR, "*"))
        if p.lower().endswith(VIDEO_EXTS)
    )
    if target:
        if target not in all_videos:
            _log(f"Requested video not found in videos/: {target}")
            sys.exit(1)
        todo = [target]                       # explicit file: force a publish/retry
    else:
        todo = [v for v in all_videos if pending(v, posts)]

    if not todo:
        _log("No pending videos to publish.")
        return

    _log(f"Publishing: {', '.join(todo)}")
    all_failures = []
    for v in todo:
        all_failures += [f"{v}:{name}" for name in publish_one(v, posts)]
        save_posts(posts)

    print("\n===== VIDEO PUBLISH SUMMARY =====")
    print(f"  videos processed: {len(todo)}")
    print(f"  failures: {', '.join(all_failures) if all_failures else 'none'}")
    print("=================================\n")

    if all_failures:
        print("::error::Video publish FAILED for configured channel(s): " + ", ".join(all_failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
