"""
sync_photos.py
--------------
Automatic intake for the photographic social style. Brian keeps adding frames to
the Dropbox brand-photo folder; this script pulls any NEW ones into the live
rotation with no manual step:

    scan Dropbox folder
      -> skip anything already ingested   (content-hash ledger + registry check)
      -> skip obvious non-photos          (too small / extreme aspect / near-solid
                                           or logo-slate frames)
      -> copy + optimize into assets/photos/   (progressive JPEG, <=1600px, crisp)
      -> append to assets/variety_assets.json  (photographic; + behind_the_scenes
                                                when people are cheaply detected)
         with robust DEFAULT render hints (center focal, bottom-anchored text so a
         headline rarely lands on a face - the photo card's directional scrim
         handles legibility).

It only ADDS. It never edits or removes the 8 hand-curated photos, never
re-processes a file it has already ingested, and is safe to run on a timer: a
second run against an unchanged folder reports 0 new. New files are left in the
working tree for the "ProLink Auto-Commit Watcher" to commit + push - this script
does NOT touch git.

Run:
    python sync_photos.py            # normal sync
    python sync_photos.py --dry-run  # report what WOULD happen, write nothing
    PHOTO_SRC=... python sync_photos.py   # override the source folder

Fine-tuning: to adjust the crop/focal or text side of a specific photo, edit its
entry in assets/variety_assets.json by hand - this script won't overwrite an
entry that already exists for a given file.
"""

import os
import sys
import json
import hashlib
import datetime
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = r"C:\Users\brian.shad\Dropbox\Prolink\Marketing\2026 Photos"
SRC = os.environ.get("PHOTO_SRC", DEFAULT_SRC)
DEST = os.path.join(HERE, "assets", "photos")
REGISTRY = os.path.join(HERE, "assets", "variety_assets.json")
LEDGER = os.path.join(DEST, ".ingested.json")

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp")
MAX_W = 1600
JPEG_Q = 84

# The 8 hand-curated photos, by their Dropbox SOURCE filename -> the dest name
# already in the registry. On first run this seeds the ledger so the originals are
# recognized as already-ingested and never re-processed or duplicated.
CURATED_SEED = {
    "Screenshot 2026-06-04 090958.png": "server_rack.jpg",
    "Screenshot 2026-06-04 091258.png": "team_brand_polo.jpg",
    "Screenshot 2026-06-04 091426.png": "team_dual_monitor.jpg",
    "Screenshot 2026-06-04 091327.png": "deskside_support.jpg",
    "Screenshot 2026-06-04 091229.png": "tech_workbench.jpg",
    "Screenshot 2026-06-04 091602.png": "lab_consult.jpg",
    "Screenshot 2026-06-04 091828.png": "tech_laptop_notes.jpg",
    "Screenshot 2026-06-04 091457.png": "circuit_macro.jpg",
}


def _log(msg):
    print(f"[photo-sync] {msg}", flush=True)


def _sha1(path, chunk=1 << 20):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _atomic_write(path, data):
    """Write JSON atomically so the watcher never commits a half-written file."""
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Non-photo filters ────────────────────────────────────────────────────
def _classify(im):
    """Return (keep: bool, reason: str, has_people: bool).

    Cheap heuristics on a downscaled copy so brand slides / logo slates / banners
    don't enter the rotation, and so we can cheaply guess whether people appear."""
    w, h = im.size
    if min(w, h) < 600 or w < 900:
        return False, f"too small ({w}x{h})", False
    ar = w / h
    if ar > 2.6 or ar < 0.42:
        return False, f"extreme aspect ratio ({ar:.2f})", False

    small = im.convert("RGB").resize((96, 96))
    px = list(small.getdata())
    n = len(px)
    lum = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px]
    mean = sum(lum) / n
    var = sum((l - mean) ** 2 for l in lum) / n
    std = var ** 0.5
    near_white = sum(1 for r, g, b in px if r > 238 and g > 238 and b > 238) / n
    near_black = sum(1 for r, g, b in px if r < 16 and g < 16 and b < 16) / n

    # Logo slate / near-solid card: mostly white (or one flat tone), little detail.
    if near_white > 0.60:
        return False, f"near-white slate ({near_white:.0%} white)", False
    if std < 16 and (near_white + near_black) > 0.5:
        return False, f"near-solid frame (std {std:.1f})", False

    # Cheap skin-tone fraction -> people present (loose, for behind_the_scenes).
    skin = 0
    for r, g, b in px:
        mx, mn = max(r, g, b), min(r, g, b)
        if (r > 95 and g > 40 and b > 20 and (mx - mn) > 15
                and abs(r - g) > 15 and r > g and r > b):
            skin += 1
    has_people = (skin / n) > 0.04
    return True, "ok", has_people


def _slug_from(src_name, digest):
    stem = os.path.splitext(os.path.basename(src_name))[0]
    stem = "".join(c.lower() if c.isalnum() else "_" for c in stem).strip("_")
    stem = "_".join(p for p in stem.split("_") if p)[:32] or "photo"
    return f"auto_{stem}_{digest[:8]}.jpg"


def _optimize_to(src_path, dest_path):
    im = Image.open(src_path).convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.save(dest_path, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    return im.size


DEFAULT_HINT = {"focal": [0.5, 0.5], "text": "bottom"}


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.isdir(SRC):
        _log(f"source folder not found: {SRC} - nothing to do.")
        return 0
    os.makedirs(DEST, exist_ok=True)

    ledger = _load_json(LEDGER, {"version": 1, "ingested": {}})
    ingested = ledger.setdefault("ingested", {})  # sha1 -> {dest, src, added, seed?}

    registry = _load_json(REGISTRY, {})
    registry.setdefault("photographic", [])
    registry.setdefault("behind_the_scenes", [])
    registry.setdefault("reel_clip", [])
    registered_paths = {e.get("path") for e in registry["photographic"]
                        if isinstance(e, dict)}

    # 1) Seed the ledger with the curated originals so they're never re-ingested.
    seeded = 0
    for src_name, dest_name in CURATED_SEED.items():
        p = os.path.join(SRC, src_name)
        if not os.path.exists(p):
            continue
        digest = _sha1(p)
        if digest not in ingested:
            ingested[digest] = {"dest": f"assets/photos/{dest_name}",
                                "src": src_name, "added": None, "seed": True}
            seeded += 1
    if seeded:
        _log(f"seeded {seeded} curated original(s) into the ingest ledger")

    # 2) Scan the source folder for NEW images.
    files = sorted(f for f in os.listdir(SRC)
                   if f.lower().endswith(EXTS) and os.path.isfile(os.path.join(SRC, f)))
    new_count = skipped = 0
    for fname in files:
        src_path = os.path.join(SRC, fname)
        digest = _sha1(src_path)
        if digest in ingested:
            continue  # already handled (dedupe by content hash; rename-proof)
        try:
            im = Image.open(src_path)
            im.load()
        except Exception as e:
            _log(f"skip {fname}: unreadable ({e})")
            skipped += 1
            continue
        keep, reason, has_people = _classify(im)
        if not keep:
            _log(f"skip {fname}: {reason}")
            ingested[digest] = {"dest": None, "src": fname,
                                "added": datetime.date.today().isoformat(),
                                "skipped": reason}
            skipped += 1
            continue

        dest_name = _slug_from(fname, digest)
        rel = f"assets/photos/{dest_name}"
        # collision guard (different content, same slug) -> extend the hash
        if rel in registered_paths or os.path.exists(os.path.join(DEST, dest_name)):
            dest_name = f"auto_{digest[:12]}.jpg"
            rel = f"assets/photos/{dest_name}"

        entry = {"path": rel,
                 "shows": f"Pro Link Systems 2026 brand shoot ({os.path.splitext(fname)[0]})",
                 "focal": list(DEFAULT_HINT["focal"]), "text": DEFAULT_HINT["text"],
                 "people": bool(has_people), "auto": True}

        if dry:
            _log(f"NEW (dry-run): {fname} -> {rel}"
                 f"{'  +people' if has_people else ''}")
            new_count += 1
            continue

        size = _optimize_to(src_path, os.path.join(DEST, dest_name))
        registry["photographic"].append(entry)
        registered_paths.add(rel)
        if has_people:
            registry["behind_the_scenes"].append(dict(entry))
        ingested[digest] = {"dest": rel, "src": fname,
                            "added": datetime.date.today().isoformat(),
                            "people": bool(has_people)}
        new_count += 1
        _log(f"ingested {fname} -> {rel} ({size[0]}x{size[1]}, "
             f"{'people' if has_people else 'no-people'})")

    # 3) Persist (atomic). Only write when something changed.
    if not dry and (new_count or seeded):
        registry["updated"] = datetime.date.today().isoformat()
        _atomic_write(REGISTRY, registry)
        _atomic_write(LEDGER, ledger)

    _log(f"done: {new_count} new, {skipped} skipped, "
         f"{len(registry['photographic'])} total photographic"
         f"{' (dry-run, nothing written)' if dry else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
