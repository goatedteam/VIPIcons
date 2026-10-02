#!/usr/bin/env python3
"""Mystery-chest promo poster (4:5) in Goated's art style.

  python tools/run_poster.py paint [n]          # paint n variants -> poster/raw/lightning_<i>.png
  python tools/run_poster.py logo <raw.png> ... # add the wordmark -> poster/<name>.png

The art is painted by Nano Banana Pro with the bottom band left empty; the GOATED wordmark is
then composited on top, unframed, so it is pixel-exact.
"""
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = [os.path.join(ROOT, "reference", "art", "Chest_mystery_glow.png"),
        os.path.join(ROOT, "reference", "competitor", "mystery_box.webp")]

PROMPT = """Paint a 4:5 portrait social-media promo poster for Goated, a crypto casino: a MYSTERY CHEST reveal.

Using the attached references:
- Reference 1 is the hero: Goated's own painted mystery chest. Reproduce THIS chest faithfully: the same closed chest with the flat-topped lid, red-brown wood planks with ink-drawn grain and a few scratches, chunky light-grey steel corner caps and centre strap with rivets, side ring handles, the brass keyhole plate, the gold strap and trim, and the bright light glowing out of the gap between lid and body. Same art style: hand-painted 2.5D game art, bold dark ink outlines, cel-shaded with soft gradients. Nothing is added to the chest: no logo, no emblem, no symbols.
- Reference 2 gives ONLY the framing: hero object centred slightly above the middle on a wide pedestal that fills the lower third. Do not copy its colours, its cube, its swirls, its question mark or its logo.

SCENE: the chest, front-facing and seen very slightly from above, fills about 45% of the frame width and sits on a wide, dark slate-navy cloth-draped pedestal that runs off both sides of the frame. The chest is charged with energy: the glow leaking from its lid seam and keyhole is neon lime (#D4FF00), and a LIME LIGHTNING STORM erupts from behind it. Behind the chest is a dark, stormy night sky of heavy, churning slate-navy clouds. Jagged, branching bolts of neon-lime lightning crackle outward from behind the chest in every direction and fork across the sky, some bolts reaching to the frame edges; small electric arcs crawl over the steel corner caps and lick at the pedestal. The clouds are lit lime from inside where the bolts pass. A few bright lime and white sparks and embers float in the air. The lightning is painted in the same comic-ink style: crisp bright white-lime cores, lime glow, clean dark outlines on the clouds.

LIGHT: the chest is rim-lit lime from behind and from the seam; its front stays readable with its warm wood and brass colours. Strong lime glow directly behind the chest.

PALETTE (Goated brand only): deep near-black slate navy (#0B0F1A to #1A2233) for sky, clouds and shadows; Goated neon lime (#D4FF00) for lightning, glow and sparks, with darker olive-lime for depth; white only in the hottest lightning cores; the chest keeps its own wood, steel and brass colours. No purple, magenta, pink, blue or cyan lightning anywhere.

The bottom 12% of the frame is calm and dark (the front of the pedestal falling into shadow), with nothing in it, reserved for a logo. No text, letters, numbers or logos anywhere in the image. One chest only."""


def paint(i):
    png = generate(PROMPT, REFS, "gemini-3-pro-image", "2K", aspect="4:5")
    out = os.path.join(ROOT, "poster", "raw", f"lightning_{i}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.open(io.BytesIO(png)).convert("RGB").save(out, "PNG")
    print("wrote", out, flush=True)
    return out


def add_logo(raw, out):
    """GOATED wordmark, unframed, centred near the bottom (where the reference's footer sits)."""
    im = Image.open(raw).convert("RGBA")
    W, H = im.size
    mark = Image.open(os.path.join(ROOT, "reference", "brand", "goated_wordmark.png")).convert("RGBA")
    mark = mark.crop(mark.getbbox())
    mw = round(W * 0.26)
    mark = mark.resize((mw, round(mark.height * mw / mark.width)), Image.LANCZOS)
    im.alpha_composite(mark, ((W - mw) // 2, H - round(H * 0.058) - mark.height))
    im.convert("RGB").save(out, "PNG")
    # Instagram 4:5 export
    w, h = (W, round(W * 5 / 4)) if W * 5 / 4 <= H else (round(H * 4 / 5), H)
    l, t = (W - w) // 2, (H - h) // 2
    im.crop((l, t, l + w, t + h)).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(
        out.replace(".png", "_1080x1350.png"))


if __name__ == "__main__":
    if sys.argv[1] == "paint":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        with ThreadPoolExecutor(n) as ex:
            list(ex.map(paint, range(1, n + 1)))
    else:
        for raw in sys.argv[2:]:
            out = os.path.join(ROOT, "poster", os.path.basename(raw))
            add_logo(raw, out)
            print("wrote", out)
