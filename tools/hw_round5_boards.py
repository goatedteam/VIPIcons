#!/usr/bin/env python3
"""Review boards for round 5: the Zone 4 haunted house options and the zone icons.

  python tools/hw_round5_boards.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
CUT = os.path.join(HW, "variants", "round5", "cut")
F = os.path.join(HW, "final", "halloween-2026")
OUT = os.path.join(HW, "review", "round5")
BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
BG, CARD, LIME, MUTED = (15, 14, 21), (29, 27, 41), (215, 255, 0), (150, 148, 165)


def fit(im, box, anchor="bottom"):
    im = im.copy()
    im.thumbnail(box, Image.LANCZOS)
    c = Image.new("RGBA", box, (0, 0, 0, 0))
    y = box[1] - im.height if anchor == "bottom" else (box[1] - im.height) // 2
    c.alpha_composite(im, ((box[0] - im.width) // 2, y))
    return c


def houses():
    names = {"A": "A · Haunted mansion", "B": "B · Castle-manor", "C": "C · Living house (face)"}
    W, H = 1500, 1640
    S = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(S)
    d.text((24, 18), "Zone 4 · The Haunted House: 3 options × 2 states", font=ImageFont.truetype(BOLD, 30), fill=LIME)
    for j, v in enumerate("ABC"):
        x = 24 + j * 488
        d.text((x, 70), names[v], font=ImageFont.truetype(BOLD, 22), fill=(236, 232, 244))
        for i, (st, lab) in enumerate((("house_z4", "lit · unlocked"), ("house_z4_dark", "dark · locked"))):
            y = 110 + i * 500
            ImageDraw.Draw(S).rounded_rectangle((x, y, x + 464, y + 470), 14, fill=CARD)
            S.alpha_composite(fit(Image.open(os.path.join(CUT, st, f"{v}.png")).convert("RGBA"), (430, 420)), (x + 17, y + 12))
            d.text((x + 14, y + 440), lab, font=ImageFont.truetype(REG, 17), fill=MUTED)
    # on the trail at map size (shows at 160 px): Z1, Z2, Z3 open, then each Z4 option
    y = 1130
    d.text((24, y), "At map size (160 px) next to the existing houses", font=ImageFont.truetype(BOLD, 22), fill=(236, 232, 244))
    strip = Image.new("RGBA", (W - 48, 450), (34, 30, 48, 255))
    row = [Image.open(os.path.join(F, f"map/hw26-house-{z}-open.png")).convert("RGBA").resize((160, 160), Image.LANCZOS)
           for z in ("z1", "z2", "z3")]
    for v in "ABC":
        # Z4 gets a 200 px box so it reads a size up from the other three, as the finale
        row.append(fit(Image.open(os.path.join(CUT, "house_z4", f"{v}.png")).convert("RGBA"), (200, 200)))
    labs = ["Z1", "Z2", "Z3", "Z4 A", "Z4 B", "Z4 C"]
    x = 30
    for im, lab in zip(row, labs):
        strip.alpha_composite(im, (x, 250 - im.height))
        ImageDraw.Draw(strip).text((x + im.width // 2 - 20, 270), lab, font=ImageFont.truetype(BOLD, 18), fill=MUTED)
        x += im.width + 50
    S.alpha_composite(strip, (24, y + 40))
    S = S.crop((0, 0, W, y + 40 + 330))
    S.convert("RGB").save(os.path.join(OUT, "house_z4.png"), optimize=True)


def icons():
    sets = [("Pumpkin Fields", [("icon_pumpkin", "A", "Your example, at 2K")]),
            ("Hollow Woods", [("icon_woods", "A", "A · Mushroom cluster"), ("icon_woods", "B", "B · Tree stump with face"),
                              ("icon_woods", "C", "C · Owl with lantern")]),
            ("The Graveyard", [("icon_grave", "A", "A · Tombstone and ghost"), ("icon_grave", "B", "B · Skull candle"),
                               ("icon_grave", "C", "C · Gate lantern")])]
    W = 24 + 4 * 360
    S = Image.new("RGBA", (W, 3 * 500 + 80), BG)
    d = ImageDraw.Draw(S)
    d.text((24, 18), "Zone icons · 2048 px masters, transparent", font=ImageFont.truetype(BOLD, 30), fill=LIME)
    for r, (zone, items) in enumerate(sets):
        y = 70 + r * 500
        d.text((24, y), zone, font=ImageFont.truetype(BOLD, 22), fill=(236, 232, 244))
        if r == 0:  # the user's example for comparison
            ex = Image.open(os.path.join(HW, "reference", "zone_icon_pumpkin_example.png")).convert("RGBA")
            items = [("_ex", ex, "Your example (128 px)")] + items
        for j, it in enumerate(items):
            x = 24 + j * 360
            ImageDraw.Draw(S).rounded_rectangle((x, y + 36, x + 340, y + 480), 14, fill=CARD)
            im = it[1] if it[0] == "_ex" else Image.open(os.path.join(CUT, it[0], f"{it[1]}.png")).convert("RGBA")
            S.alpha_composite(fit(im, (300, 300), "center"), (x + 20, y + 50))
            small = fit(im, (48, 48), "center")
            S.alpha_composite(small, (x + 20, y + 370))
            S.alpha_composite(fit(im, (96, 96), "center"), (x + 80, y + 346))
            d.text((x + 190, y + 380), "48 · 96 px", font=ImageFont.truetype(REG, 15), fill=MUTED)
            d.text((x + 16, y + 452), it[2], font=ImageFont.truetype(REG, 17), fill=MUTED)
    S.convert("RGB").save(os.path.join(OUT, "zone_icons.png"), optimize=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    houses()
    icons()
    print("wrote", OUT)
