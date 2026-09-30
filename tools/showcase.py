#!/usr/bin/env python3
"""Render the final icons as a 3x3 sheet of VIP modal cards, plus a before/after sheet.

  python tools/showcase.py [--current-dir DIR]

Reads final/<bonus>.png and writes review/final_cards.png (and, with
--current-dir, review/final_before_after.png). Also writes 512px copies of
each transparent icon to final/512/.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

from mock_cards import BOLD, CURRENT, H, ROOT, W, X, card

TITLES = {k: b["title"] for k, b in json.load(open(os.path.join(ROOT, "tools", "concepts.json")))["bonuses"].items()}
ORDER = ["monthly", "weekly", "rakeback", "daily", "vip", "lossback", "reload", "levelup", "tierup"]
BG, GAP = (15, 14, 21), 20 * X


def final_icon(key):
    return Image.open(os.path.join(ROOT, "final", f"{key}.png")).convert("RGBA")


def grid(cells, cols):
    rows = (len(cells) + cols - 1) // cols
    out = Image.new("RGB", (cols * (W + GAP) + GAP, rows * (H + GAP) + GAP), BG)
    for i, im in enumerate(cells):
        out.paste(im, (GAP + (i % cols) * (W + GAP), GAP + (i // cols) * (H + GAP)), im)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current-dir")
    a = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "review"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "final", "512"), exist_ok=True)

    cards = [card(TITLES[k], final_icon(k), "Expires in 4 hours") for k in ORDER]
    grid(cards, 3).save(os.path.join(ROOT, "review", "final_cards.png"), optimize=True)

    for k in ORDER:
        small = final_icon(k).resize((512, 512), Image.LANCZOS)
        small.save(os.path.join(ROOT, "final", "512", f"{k}.png"), optimize=True)

    if a.current_dir:
        head = 30 * X
        out = Image.new("RGB", (2 * (W + GAP) + GAP, len(ORDER) * (H + GAP) + GAP + head), BG)
        d = ImageDraw.Draw(out)
        f = ImageFont.truetype(BOLD, 14 * X)
        d.text((GAP, GAP), "BEFORE", font=f, fill=(170, 170, 185))
        d.text((2 * GAP + W, GAP), "AFTER", font=f, fill=(215, 255, 0))
        for i, (k, new) in enumerate(zip(ORDER, cards)):
            old = Image.open(os.path.join(a.current_dir, CURRENT[k])).convert("RGBA").resize((W, H), Image.LANCZOS)
            y = head + GAP + i * (H + GAP)
            out.paste(old, (GAP, y), old)
            out.paste(new, (2 * GAP + W, y), new)
        out.save(os.path.join(ROOT, "review", "final_before_after.png"), optimize=True)
    print("wrote review/final_cards.png, final/512/*")


if __name__ == "__main__":
    main()
