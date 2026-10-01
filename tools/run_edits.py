#!/usr/bin/env python3
"""Apply art-direction edits to finished icons with Nano Banana Pro.

  python tools/run_edits.py edits.json [bonus ...]

edits.json maps bonus -> {"change": "...", "refs": ["ref names"], "ref_roles": "..."}.
The current final/flat/<bonus>.png is sent first as the image to edit; refs resolve
like run_variants.py (coin, art:<file>, brand:<file>, ...). The edited image
replaces final/flat/<bonus>.png and is cut out to final/<bonus>.png.
"""
import io
import json
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402
from run_variants import ref_path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EDIT_BRIEF = """Edit the FIRST attached image: an approved, finished game icon for Goated, a crypto casino, painted in a hand-painted 2.5D style with bold dark ink outlines and cel shading.

CHANGE: {change}
{roles}
PRESERVE: everything not named in CHANGE, exactly as it is: the design, colours, proportions, pose, camera angle, ink linework style, shading, lighting and composition. Any new element must be painted in the same hand-painted, ink-outlined style and lit from the same top-left key light, so it looks like it was always part of the icon.

CONSTRAINTS: do not add anything that is not asked for. No text, no watermark. Keep the plain, flat, perfectly uniform light-grey (#D0D0D0) background, with no glow halo, light rays or cast shadow spilling onto it."""


def edit(key, spec):
    flat = os.path.join(ROOT, "final", "flat", f"{key}.png")
    refs = [flat] + [ref_path(r) for r in spec.get("refs", [])]
    roles = f"REFERENCE IMAGES: {spec['ref_roles']}\n" if spec.get("ref_roles") else ""
    png = generate(EDIT_BRIEF.format(change=spec["change"], roles=roles), refs, "gemini-3-pro-image", "2K")
    Image.open(io.BytesIO(png)).save(flat, "PNG")
    # BiRefNet leaks memory across calls, so run each cutout in its own process
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cutout.py"), flat,
                    "--out-dir", os.path.join(ROOT, "final"), "--trim"], check=True)


if __name__ == "__main__":
    edits = json.load(open(sys.argv[1]))
    only = set(sys.argv[2:])
    for key, spec in edits.items():
        if only and key not in only:
            continue
        edit(key, spec)
        print("done", key, flush=True)
