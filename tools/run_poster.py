#!/usr/bin/env python3
"""Add the Goated logo pill to a painted mystery-chest poster.

  python tools/run_poster.py poster/raw/<name>.png [...]

The poster art itself is painted by Nano Banana Pro (prompt in docs/06-mystery-chest-poster.md)
with the bottom band left empty. This composites the footer pill (lime Goated glyph +
GOATED.COM) on top so the logo is pixel-exact. Writes poster/<name>.png.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIME = (212, 255, 0)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def add_pill(raw, out):
    """Outlined pill with the lime Goated glyph + GOATED.COM, laid out like the reference's footer."""
    im = Image.open(raw).convert("RGBA")
    W, H = im.size
    s = W / 960  # layout measured on the 960x1200 reference
    ph, pw = round(50 * s), round(270 * s)
    x0, y0 = (W - pw) // 2, H - round(94 * s)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), radius=ph // 2,
                        fill=(11, 15, 26, 150), outline=(255, 255, 255, 255), width=max(2, round(3 * s)))
    logo = Image.open(os.path.join(ROOT, "reference", "brand", "goated_logo.png")).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    lh = round(ph * 0.6)
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    glyph = Image.new("RGBA", logo.size, LIME + (255,))
    glyph.putalpha(logo.getchannel("A"))
    font = ImageFont.truetype(FONT, round(ph * 0.46))
    text = "GOATED.COM"
    tb = d.textbbox((0, 0), text, font=font)
    gap = round(ph * 0.22)
    gx = (W - (glyph.width + gap + tb[2] - tb[0])) // 2
    layer.alpha_composite(glyph, (gx, y0 + (ph - lh) // 2))
    d.text((gx + glyph.width + gap - tb[0], y0 + (ph - (tb[3] - tb[1])) // 2 - tb[1]),
           text, font=font, fill=(255, 255, 255, 255))
    im.alpha_composite(layer)
    im.convert("RGB").save(out, "PNG")


if __name__ == "__main__":
    for raw in sys.argv[1:]:
        out = os.path.join(ROOT, "poster", os.path.basename(raw))
        add_pill(raw, out)
        print("wrote", out)
