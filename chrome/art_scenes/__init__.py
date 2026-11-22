"""
chrome/art_scenes -- subject-specific illustrations for Insights articles (redesign-2026, iteration 4).

Each article has its own composition built from chrome/art_kit.py. A scene is a function that returns a list of SVG
strings and is registered for a slug:

    from art_scenes import scene
    from art_kit import *

    @scene("2026-09-17-t108-technology-debt-...", alt="A stack of layers with one amber line rising above it")
    def technology_debt(r):            # r = random.Random seeded by the slug (optional use)
        return [...]

STYLE (read this first)
- One idea per scene: a schematic of the article's actual argument, not a decoration and not a generic category motif.
  Choose 2-5 elements with a clear relationship: a flow, a comparison, a boundary, a timeline, an accumulation, a gate.
- White linework on the navy ground. Use the kit's tones: "hi" (key parts), "mid", "lo" (supporting), "faint" (texture).
- EXACTLY one amber idea per scene (a path, a node, a row, a window, a point in time). Everything else is white.
- No text, letters, numbers, logos, faces, emoji, gradients, filters, shadows, images, scripts or external references.
- Canvas 1200 x 675. Keep meaning inside x 120-1080 and y 80-595. Leave air: aim for 25-80 marks, balanced but not
  symmetric by default. Prefer long, quiet lines over clutter; align things to a notional grid.
- Every scene must look intentional at card size (about 360 px wide): strong silhouette, medium strokes (1.6-2.8).
- alt text: a plain sentence that describes what is drawn, e.g. "A ledger of exposures with one row highlighted".
  Keep it under 120 characters. It must be true of the drawing.

Validate + preview: python chrome/art_preview.py <slug> [<slug> ...]   (writes PNG contact sheets to the scratchpad)
"""
import importlib
import pkgutil

SCENES = {}
ALT = {}


def scene(slug, alt):
    def wrap(fn):
        if slug in SCENES:
            raise ValueError("two scenes registered for " + slug)
        SCENES[slug] = fn
        ALT[slug] = alt
        return fn
    return wrap


def load():
    """Import every module in this package so its scenes register. Safe to call more than once."""
    for m in pkgutil.iter_modules(__path__):
        importlib.import_module("art_scenes." + m.name)
    return SCENES


def S(prefix):
    """Resolve a slug from an unambiguous prefix (the registry is the list of articles)."""
    import io
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "editorial", "blog_registry.json")
    with io.open(path, encoding="utf-8") as fh:
        hits = [s for s in json.load(fh)["posts"] if s.startswith(prefix)]
    if len(hits) != 1:
        raise ValueError("prefix %r matches %d articles" % (prefix, len(hits)))
    return hits[0]
