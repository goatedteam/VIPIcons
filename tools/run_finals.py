#!/usr/bin/env python3
"""Step 4: generate final icons from the selected variants.

  python tools/run_finals.py selections.json [bonus ...]

selections.json maps bonus -> {"pick": "A"|"B"|"C", "notes": "optional tweaks"}.
For each bonus, the chosen variant is passed as the primary reference, together
with the Goated style references, and re-rendered at 2K. Writes:
  final/flat/<bonus>.png   2K on a flat #D0D0D0 background
  final/<bonus>.png        transparent cutout, trimmed to a padded square
"""
import io
import json
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "tools", "concepts.json")))

FINAL_BRIEF = """The FIRST attached image is the approved concept sketch for this icon. Re-render it as the final, production-quality asset.

PRESERVE from the concept: the subject, its design, colours, silhouette, composition and camera angle.
IMPROVE: cleaner and more confident ink linework, richer cel-shaded modelling, crisper specular highlights, more refined painterly texture, and consistent Goated ram-horn glyphs on every coin, chip or seal. The glyph must match the one on the coin reference exactly.
Keep every secondary effect (sparks, stars, motion streaks, steam, light rays) touching or overlapping the main object rather than floating free, so the asset can be cut out cleanly.

The remaining attached images are Goated's official art, supplied as the style reference: {style}

SUBJECT (for context): {subject}
{notes}
COMPOSITION: centred, filling about 80% of a square canvas with even padding, nothing cropped.
BACKGROUND: plain, flat, solid light grey (#D0D0D0), perfectly uniform. No gradient, no floor, no cast shadow on the background, no vignette, and no glow halo on the background.
No text, letters or numbers; no UI, no frame, no watermark."""

STYLE = ("hand-painted stylized 2.5D premium mobile-game asset, bold dark ink outlines with varied weight, "
         "cel-shaded value blocks with soft gradient blending, chunky proportions, warm top-left key light.")


def final(key, pick, notes):
    c = CFG["bonuses"][key][pick]
    refs = [os.path.join(ROOT, "variants", key, f"{pick}.png")]
    refs += [os.path.join(ROOT, "reference", "style", r + ".png") for r in c["refs"]]
    prompt = FINAL_BRIEF.format(style=STYLE, subject=c["subject"],
                                notes=f"ART DIRECTION NOTES (apply these): {notes}\n" if notes else "")
    png = generate(prompt, refs, "gemini-3-pro-image", "2K")
    flat = os.path.join(ROOT, "final", "flat", f"{key}.png")
    os.makedirs(os.path.dirname(flat), exist_ok=True)
    Image.open(io.BytesIO(png)).save(flat, "PNG")
    # BiRefNet leaks memory across calls, so run each cutout in its own process
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cutout.py"), flat,
                    "--out-dir", os.path.join(ROOT, "final"), "--trim"], check=True)


if __name__ == "__main__":
    sel = json.load(open(sys.argv[1]))
    only = set(sys.argv[2:])
    for key, s in sel.items():
        if only and key not in only:
            continue
        final(key, s["pick"], s.get("notes", ""))
        print("done", key, flush=True)
