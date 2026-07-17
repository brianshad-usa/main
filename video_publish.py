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


def wait_for_url(url, tries=30, delay=8):
    """Poll a public URL until it serves (200). Cloudflare needs a moment to
    deploy a just-pushed video before Instagram/Facebook can fetch it."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-0"})
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
    attempt("YouTube", lambda: (
        (lambda r: {"status": "posted", "id": r["id"], "url": r["url"], "privacy": r.get("privacy")})(_r)
        if (_r := youtube_post.maybe_post(path, title, youtube_description(caption, tags), tags)) else None
    ))
    attempt("LinkedIn", lambda: (
        (lambda pid: {"status": "posted", "id": pid, "url": linkedin_url(pid)})(_p)
        if (_p := linkedin_post.maybe_post_video(caption, path, title)) else None
    ))

    # Instagram + Facebook fetch the public URL (only if it deployed).
    def ig():
        if not url_ready:
            _log("Instagram: public URL not ready; skipping this run.")
            return None
        mid = instagram_post.maybe_post_reel(caption, public_url)
        return {"status": "posted", "id": mid} if mid else None

    def fb():
        if not url_ready:
            _log("Facebook: public URL not ready; skipping this run.")
            return None
        vid = facebook_post.maybe_post_video(caption, public_url)
        return {"status": "posted", "id": vid, "url": f"https://www.facebook.com/{vid}" if vid else None} if vid else None

    attempt("Instagram", ig)
    attempt("Facebook", fb)

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
