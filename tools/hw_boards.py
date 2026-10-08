#!/usr/bin/env python3
"""Review boards for Haunted Trail variants.

  python tools/hw_boards.py halloween/concepts/round1.json

One board per group in halloween/review/<round>/<group>.png. Each cell shows the
variant large, plus an inset at the size it actually shows at on screen (from the
spec), on Goated's dark UI colour, so readability at small sizes can be judged.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
BG, CARD, LIME, MUTED = (15, 14, 21), (29, 27, 41), (215, 255, 0), (150, 148, 165)

# on-screen size per design (spec "shows at"); scenes show a scaled-down whole
SHOWS_AT = {"house_z1": 160, "house_z2": 160, "house_z3": 160, "g3": 128, "candy": 32,
            "lantern": 48, "keeper": 128, "kid": 128, "soldout": 96, "item": 96}
GROUPS = {
    "map-fog-meter": ["map", "fog", "meter"],
    "houses": ["house_z1", "house_z2", "house_z3"],
    "characters": ["g3", "keeper", "kid"],
    "trail-ui": ["candy", "lantern", "soldout"],
    "shop-items-1-4": ["item1", "item2", "item3", "item4"],
    "shop-items-5-8": ["item5", "item6", "item7", "item8"],
}


def cell(path, title, shows_at, w):
    im = Image.open(path).convert("RGB")
    big = im.copy()
    big.thumbnail((w - 24, w - 24 if im.width <= im.height * 1.2 else int((w - 24) / im.width * im.height)))
    h = big.height + 60 + (shows_at + 16 if shows_at else 0)
    c = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(c)
    d.text((12, 10), title, font=ImageFont.truetype(BOLD, 18), fill=LIME)
    c.paste(big, ((w - big.width) // 2, 40))
    if shows_at:
        small = im.copy()
        small.thumbnail((shows_at, shows_at), Image.LANCZOS)
        y = 48 + big.height
        d.text((12, y + 4), f"at {shows_at}px:", font=ImageFont.truetype(REG, 14), fill=MUTED)
        c.paste(small, (110, y))
    return c


def main():
    cfg = json.load(open(sys.argv[1]))
    out_dir = os.path.join(HW, "review", cfg["round"])
    os.makedirs(out_dir, exist_ok=True)
    for group, keys in GROUPS.items():
        keys = [k for k in keys if k in cfg["designs"]]
        if not keys:
            continue
        wide = group == "map-fog-meter"
        w = 640 if wide else 400
        rows = []
        for k in keys:
            d = cfg["designs"][k]
            sa = SHOWS_AT.get(k, SHOWS_AT["item"] if k.startswith("item") else None)
            cells = []
            for vid, v in d["variants"].items():
                p = os.path.join(HW, "variants", cfg["round"], k, f"{vid}.png")
                if os.path.exists(p):
                    cells.append(cell(p, f"{k}  {vid} · {v['name']}", sa, w))
            rows.append(cells)
        gap = 16
        width = max(len(r) for r in rows) * (w + gap) + gap
        height = sum(max(c.height for c in r) + gap for r in rows) + gap
        board = Image.new("RGB", (width, height), BG)
        y = gap
        for r in rows:
            for i, c in enumerate(r):
                board.paste(c, (gap + i * (w + gap), y))
            y += max(c.height for c in r) + gap
        dst = os.path.join(out_dir, f"{group}.png")
        board.save(dst, optimize=True)
        print("wrote", dst, board.size)


if __name__ == "__main__":
    main()
