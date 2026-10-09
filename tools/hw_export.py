#!/usr/bin/env python3
"""Export the approved Haunted Trail images to the spec's file names and sizes.

  python tools/hw_export.py [asset-prefix ...]     e.g.  map/  char/hw26-kid

Sources are the approved variants (see SOURCES). Writes into
halloween/final/halloween-2026/<path> and compresses with libimagequant (the engine
TinyPNG uses). Background removal runs once per source (cached in .cutout_cache).
"""
import math
import os
import subprocess
import sys

import imagequant
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
OUT = os.path.join(HW, "final", "halloween-2026")
CACHE = os.path.join(HW, ".cutout_cache")
sys.path.insert(0, os.path.dirname(__file__))
import hw_map_guide  # noqa: E402

R1, R2 = "variants/round1", "variants/round2"
HOUSES = {"z1": "house_z1/A", "z2": "house_z2/B", "z3": "house_z3/A"}
ITEMS = {1: f"{R2}/item1/logo", 2: f"{R1}/item2/A", 3: f"{R1}/item3/B", 4: f"{R1}/item4/A",
         5: f"{R1}/item5/C", 6: f"{R1}/item6/B", 7: f"{R1}/item7/B", 8: f"{R1}/item8/C"}


def src(rel):
    return os.path.join(HW, rel if rel.endswith(".png") else rel + ".png")


def cutout(rel):
    """RGBA with the flat grey background removed (BiRefNet, one process per image)."""
    path = src(rel)
    cached = os.path.join(CACHE, rel.replace("/", "__") + ("" if rel.endswith(".png") else ".png"))
    if not os.path.exists(cached):
        os.makedirs(CACHE, exist_ok=True)
        tmp = os.path.join(CACHE, "_in_" + os.path.basename(cached))
        Image.open(path).save(tmp)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cutout.py"), tmp, "--out-dir", CACHE],
                       check=True, capture_output=True)
        os.replace(os.path.join(CACHE, os.path.basename(tmp)), cached)
        os.remove(tmp)
    return Image.open(cached).convert("RGBA")


def bbox(im):
    return im.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()


def place(im, size, fit, anchor="center", bottom_pad=0):
    """Trim to content, scale to fit a (w, h) box, and place on a transparent canvas."""
    im = im.crop(bbox(im))
    s = min(fit[0] / im.width, fit[1] / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - im.width) // 2
    y = size[1] - bottom_pad - im.height if anchor == "bottom" else (size[1] - im.height) // 2
    canvas.alpha_composite(im, (x, y))
    return canvas


def upscale(im, size):
    big = im.resize(size, Image.LANCZOS)
    return big.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))


def alpha_from_black(im, gain=1.0, max_alpha=1.0):
    """Light-on-black art (fog, glow) -> RGBA. Alpha comes from brightness and the colour
    is un-premultiplied, so the result composites over any background like the original
    did over black."""
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255
    a = np.clip(rgb.max(axis=2) * gain, 0, 1)
    col = np.where(a[..., None] > 1e-3, np.clip(rgb * gain / np.maximum(a[..., None], 1e-3), 0, 1), 0)
    out = np.dstack([col, a * max_alpha])
    return Image.fromarray((out * 255).round().astype(np.uint8), "RGBA")


def seamless(im, axis="xy"):
    """Make a texture tile: cross-fade it with a half-offset copy of itself. At the edges the
    result is the offset copy, whose edge pixels were neighbours in the middle of the original."""
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32)
    h, w = arr.shape[:2]
    if "x" in axis:
        t = 1 - np.abs(np.linspace(-1, 1, w))[None, :, None]
        arr = arr * t + np.roll(arr, w // 2, axis=1) * (1 - t)
    if "y" in axis:
        t = 1 - np.abs(np.linspace(-1, 1, h))[:, None, None]
        arr = arr * t + np.roll(arr, h // 2, axis=0) * (1 - t)
    return Image.fromarray(arr.round().astype(np.uint8), "RGBA")


def save(im, rel, quality=(65, 92)):
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rgba = im.convert("RGBA")
    try:
        q = imagequant.quantize_pil_image(rgba, dithering_level=1.0, max_colors=256,
                                          min_quality=quality[0], max_quality=quality[1])
        q.save(dst, optimize=True)
        how = "quantized"
    except RuntimeError:  # can't reach the quality floor in 256 colours (e.g. smooth skies): keep truecolour
        (rgba if rgba.getextrema()[3][0] < 255 else rgba.convert("RGB")).save(dst, optimize=True, compress_level=9)
        how = "lossless"
    print(f"{rel:40s} {im.size[0]}x{im.size[1]}  {os.path.getsize(dst) // 1024:5d} KB  {how}", flush=True)


# ---------------------------------------------------------------- assets
def map_png(kind, rel):
    im = Image.open(src(rel)).convert("RGB")
    box = hw_map_guide.crop_box(kind)
    if im.size != hw_map_guide.GEN[kind]:  # scale the crop box if the model's size differs
        sx, sy = im.width / hw_map_guide.GEN[kind][0], im.height / hw_map_guide.GEN[kind][1]
        box = (round(box[0] * sx), round(box[1] * sy), round(box[2] * sx), round(box[3] * sy))
    return upscale(im.crop(box), hw_map_guide.EXPORT[kind]).convert("RGBA")


def fog():
    im = Image.open(src(f"{R2}/fog/1")).convert("RGB")
    w = round(im.height * 2048 / 1200)
    im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height)).resize((2048, 1200), Image.LANCZOS)
    rgba = alpha_from_black(im, gain=1.6, max_alpha=0.85)  # "a bit transparent"
    return seamless(rgba)


def meter_track():
    im = cutout(f"{R2}/meter/track")
    im = im.crop(bbox(im))
    h = 48
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    cap = h * 2  # keep the carved end caps undistorted, stretch only the middle
    left, right = im.crop((0, 0, cap, h)), im.crop((im.width - cap, 0, im.width, h))
    mid = im.crop((cap, 0, im.width - cap, h)).resize((1200 - 2 * cap, h), Image.LANCZOS)
    out = Image.new("RGBA", (1200, h), (0, 0, 0, 0))
    for part, x in ((left, 0), (mid, cap), (right, 1200 - cap)):
        out.alpha_composite(part, (x, 0))
    return out


def meter_fill():
    im = Image.open(src(f"{R2}/meter/fill")).convert("RGB")
    rgba = alpha_from_black(im, gain=1.4)
    b = bbox(rgba)
    band = rgba.crop((im.width // 8, b[1], im.width - im.width // 8, b[3]))
    return seamless(band.resize((1200, 48), Image.LANCZOS), axis="x")


def house_glow():
    size, out = 400, Image.new("RGBA", (400, 400), (255, 255, 255, 0))
    a = Image.new("L", (size, size))
    a.putdata([int(255 * max(0.0, 1 - (math.hypot(x - 199.5, y - 199.5) / 200)) ** 1.8)
               for y in range(size) for x in range(size)])
    out.putalpha(a)
    return out


def g3():
    im = place(cutout(f"{R2}/g3/1"), (256, 256), (236, 244), anchor="bottom", bottom_pad=6)
    shadow = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((80, 238, 176, 254), fill=(20, 10, 30, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    shadow.alpha_composite(im)
    return shadow


def character(rel):
    """full (800x1200), bust (600x600), avatar (128x128) from one cutout."""
    im = cutout(rel)
    im = im.crop(bbox(im))
    full = place(im, (800, 1200), (760, 1170), anchor="bottom", bottom_pad=10)
    fb = bbox(full)
    # bust: square from just above the top of the figure, ~45% of figure height
    side = int((fb[3] - fb[1]) * 0.45)
    cx = (fb[0] + fb[2]) // 2
    bust_box = (cx - side // 2, fb[1] - 10, cx + side // 2, fb[1] - 10 + side)
    bust = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    bust.alpha_composite(full.crop(bust_box))
    bust = bust.resize((600, 600), Image.LANCZOS)
    av_side = int(side * 0.62)
    av = bust.crop(((600 - av_side * 600 // side) // 2, 0, (600 + av_side * 600 // side) // 2, av_side * 600 // side))
    return full, bust, av.resize((128, 128), Image.LANCZOS)


def build():
    yield "map/hw26-map-d.png", lambda: map_png("d", f"{R2}/map/E2")
    yield "map/hw26-map-m.png", lambda: map_png("m", f"{R2}/map/F1")
    yield "map/hw26-fog.png", fog
    for z, h in HOUSES.items():
        for state, rel in (("dark", f"{R2}/house_{z}/dark"), ("open", f"{R1}/{h}"), ("done", f"{R2}/house_{z}/done")):
            yield f"map/hw26-house-{z}-{state}.png", (
                lambda rel=rel: place(cutout(rel), (320, 320), (300, 306), anchor="bottom", bottom_pad=4))
    yield "map/hw26-house-glow.png", house_glow
    yield "map/hw26-g3.png", g3
    yield "currency/hw26-candy.png", lambda: place(cutout(f"{R2}/candy/orange_logo"), (192, 192), (180, 180))
    yield "meter/hw26-meter-track.png", meter_track
    yield "meter/hw26-meter-fill.png", meter_fill
    yield "meter/hw26-lantern-on.png", lambda: place(cutout(f"{R1}/lantern/A"), (96, 96), (88, 90))
    yield "meter/hw26-lantern-off.png", lambda: place(cutout(f"{R2}/lantern/off"), (96, 96), (88, 90))
    for name, rel in (("keeper", f"{R1}/keeper/B"), ("kid", f"{R1}/kid/A")):
        parts = {}
        for part in ("full", "bust", "avatar"):
            def fn(part=part, rel=rel, parts=parts):
                if not parts:
                    parts.update(zip(("full", "bust", "avatar"), character(rel)))
                return parts[part]
            yield f"char/hw26-{name}-{part}.png", fn
    for n, rel in ITEMS.items():
        yield f"shop/hw26-item-{n}.png", lambda rel=rel: place(cutout(rel), (192, 192), (172, 172))
    yield "shop/hw26-sold-out.png", lambda: place(cutout(f"{R1}/soldout/A"), (192, 192), (176, 176))


if __name__ == "__main__":
    only = sys.argv[1:]
    for rel, fn in build():
        if only and not any(rel.startswith(o) for o in only):
            continue
        save(fn(), rel, quality=(0, 95) if rel.startswith("map/hw26-map") else (65, 92))
