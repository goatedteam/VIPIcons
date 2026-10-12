#!/usr/bin/env python3
"""Cut the round4_motion sheets (Nano Banana 2) into individual RGBA sprites.

  python tools/hw_motion_assets.py

Solid painted pieces (bats, cauldron, smoke, potion) are cut out with BiRefNet; glowing
pieces on black (sparkles, light burst, fog wisps) get alpha from brightness. Sheets are
split into separate sprites by connected components. Output:
halloween/variants/round4_motion/sprites/<sheet>_<n>.png
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "halloween", "variants", "round4_motion")
OUT = os.path.join(R, "sprites")
sys.path.insert(0, os.path.dirname(__file__))
from hw_export import alpha_from_black  # noqa: E402


def birefnet(path):
    tmp = os.path.join(OUT, "_cut")
    os.makedirs(tmp, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cutout.py"), path, "--out-dir", tmp],
                   check=True, capture_output=True)
    return Image.open(os.path.join(tmp, os.path.basename(path))).convert("RGBA")


def split(im, min_area, pad=6, merge=9, order="lr"):
    """Separate sprites by connected components of the (dilated) alpha."""
    a = np.asarray(im)[..., 3]
    m = cv2.dilate((a > 20).astype(np.uint8), np.ones((merge, merge), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    boxes = [tuple(stats[i][:4]) for i in range(1, n) if stats[i][4] >= min_area]
    if order == "rows":
        boxes.sort(key=lambda b: (round((b[1] + b[3] / 2) / (im.height / 2.5)), b[0]))
    else:
        boxes.sort(key=lambda b: b[0])
    out = []
    for x, y, w, h in boxes:
        x0, y0 = max(0, x - pad), max(0, y - pad)
        out.append(im.crop((x0, y0, min(im.width, x + w + pad), min(im.height, y + h + pad))))
    return out


def save(sprites, name):
    for i, s in enumerate(sprites, 1):
        s.save(os.path.join(OUT, f"{name}_{i}.png"))
    print(f"{name}: {len(sprites)} sprites", [s.size for s in sprites])


def main():
    os.makedirs(OUT, exist_ok=True)
    src = lambda k: os.path.join(R, k, "1.png")
    save(split(birefnet(src("bats")), 4000), "bat")
    save(split(birefnet(src("cauldron")), 20000), "cauldron")
    save(split(birefnet(src("smoke")), 8000), "smoke")
    save(split(birefnet(src("splash")), 600, order="rows"), "potion")
    save(split(alpha_from_black(Image.open(src("sparkles")), gain=1.3), 400, order="rows"), "sparkle")
    burst = Image.open(src("burst")).convert("RGB")
    w, h = burst.size  # keep only the central burst; the sheet has clutter around the edges
    core = burst.crop((int(w * 0.27), int(h * 0.27), int(w * 0.73), int(h * 0.73)))
    rgba = alpha_from_black(core, gain=1.25)
    cw, ch = rgba.size
    yy, xx = np.mgrid[0:ch, 0:cw]
    fade = np.clip((1 - np.hypot((xx - cw / 2) / (cw / 2), (yy - ch / 2) / (ch / 2))) / 0.25, 0, 1)
    arr = np.asarray(rgba).copy()
    arr[..., 3] = (arr[..., 3] * fade).astype(np.uint8)
    Image.fromarray(arr).save(os.path.join(OUT, "burst_1.png"))
    print("burst: 1 sprite", rgba.size)
    alpha_from_black(Image.open(src("wisps")), gain=1.15).save(os.path.join(OUT, "wisps_sheet.png"))
    print("wisps: sheet")


if __name__ == "__main__":
    main()
