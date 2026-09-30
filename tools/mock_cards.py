#!/usr/bin/env python3
"""Render icons inside a replica of Goated's VIP bonus modal card.

  python tools/mock_cards.py --cut-dir DIR --out-dir DIR [--current-dir DIR] [--config FILE]

For every bonus in the concepts file, writes <out-dir>/<bonus>.png: a row of cards
(current live icon, if given, then each variant) at 2x scale.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X = 2  # render scale
W, H = 332 * X, 352 * X
CARD_BG, BORDER, BTN, MUTED = (29, 27, 41), (68, 64, 84), (215, 255, 0), (150, 148, 165)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# Current live card files, in the order they appear in Current_Bonus_Images.zip
CURRENT = {
    "monthly": "Group 24518127.png", "weekly": "Group 24518128.png", "rakeback": "Group 24518129.png",
    "daily": "Group 24518130.png", "vip": "Group 24518131.png", "lossback": "Group 24518132.png",
    "reload": "Group 24518133.png", "levelup": "Group 24518134.png", "tierup": "Group 24518135.png",
}


def concepts(cfg, key):
    """{variant id: concept} for round 1 (A/B/C) and later rounds (variants map)."""
    b = cfg["bonuses"][key]
    return b["variants"] if cfg.get("round") else {v: b[v] for v in "ABC"}


def card(title, icon, caption):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=16 * X, fill=CARD_BG, outline=BORDER, width=X)
    f = ImageFont.truetype(FONT, 19 * X)
    d.text((W // 2, 45 * X), title, font=f, fill="white", anchor="mm")
    box = 170 * X
    ic = icon.copy()
    ic.thumbnail((box, box), Image.LANCZOS)
    c.alpha_composite(ic, ((W - ic.width) // 2, 72 * X + (box - ic.height) // 2))
    d.text((W // 2, 262 * X), caption, font=ImageFont.truetype(FONT, 11 * X), fill=MUTED, anchor="mm")
    d.rounded_rectangle([16 * X, 288 * X, W - 16 * X, 334 * X], radius=8 * X, fill=BTN)
    d.text((W // 2, 311 * X), "Claim", font=ImageFont.truetype(FONT, 15 * X), fill=(20, 20, 20), anchor="mm")
    return c


def board(cfg, key, cut_dir, current_dir):
    b = cfg["bonuses"][key]
    cells = []
    if current_dir:
        cur = Image.open(os.path.join(current_dir, CURRENT[key])).convert("RGBA").resize((W, H), Image.LANCZOS)
        cells.append(("CURRENT", cur))
    for v, c in concepts(cfg, key).items():
        p = os.path.join(cut_dir, key, f"{v}.png")
        if os.path.exists(p):
            cells.append((f"{v} · {c['name']}", card(b["title"], Image.open(p).convert("RGBA"), "Expires in 4 hours")))
    gap, head = 24 * X, 34 * X
    out = Image.new("RGB", (len(cells) * (W + gap) + gap, H + head + gap), (15, 14, 21))
    d = ImageDraw.Draw(out)
    lf = ImageFont.truetype(BOLD, 13 * X)
    for i, (label, im) in enumerate(cells):
        x = gap + i * (W + gap)
        d.text((x + 4, gap // 2 + 4), label, font=lf, fill=(215, 255, 0) if label != "CURRENT" else (170, 170, 185))
        out.paste(im, (x, head + gap // 2), im)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--current-dir")
    ap.add_argument("--config", default=os.path.join(ROOT, "tools", "concepts.json"))
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    os.makedirs(a.out_dir, exist_ok=True)
    for key in cfg["bonuses"]:
        dst = os.path.join(a.out_dir, f"{key}.png")
        board(cfg, key, a.cut_dir, a.current_dir).save(dst, optimize=True)
        print("wrote", dst)
