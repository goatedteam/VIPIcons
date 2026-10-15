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

import cv2
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
        tmp_dir = os.path.join(CACHE, "_in")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp = os.path.join(tmp_dir, os.path.basename(cached))
        Image.open(path).save(tmp)
        # cutout.py writes <out-dir>/<input basename>, which is exactly `cached`
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cutout.py"), tmp, "--out-dir", CACHE],
                       check=True, capture_output=True)
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
    """Resize to the export size; sharpen only when enlarging."""
    big = im.resize(size, Image.LANCZOS)
    if size[0] <= im.width:
        return big
    return big.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))


def alpha_from_black(im, gain=1.0, max_alpha=1.0):
    """Light-on-black art (fog, glow) -> RGBA. Alpha comes from brightness and the colour
    is un-premultiplied, so the result composites over any background like the original
    did over black."""
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255
    a = np.clip(rgb.max(axis=2) * gain, 0, 1)
    col = np.where(a[..., None] > 1e-3, np.clip(rgb * gain / np.maximum(a[..., None], 1e-3), 0, 1), 0)
    # near-transparent pixels: un-premultiplying amplifies noise into random colours, so
    # fade them toward their brightness-matched grey (invisible at that alpha anyway)
    w = np.clip(a / 0.15, 0, 1)[..., None]
    col = col * w + col.mean(axis=2, keepdims=True) * (1 - w)
    out = np.dstack([col, a * max_alpha])
    return Image.fromarray((out * 255).round().astype(np.uint8), "RGBA")


def seamless(im, axis="xy", overlap=0.2):
    """Make a texture tile by overlap cross-fade: the last `overlap` of the image is faded
    into the first part and then dropped, so the right edge continues straight into the left
    with no duplicated content. The result is resized back to the input size."""
    size = im.size
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32)
    for ax, name in ((1, "x"), (0, "y")):
        if name not in axis:
            continue
        n = arr.shape[ax]
        o = int(n * overlap)
        t = np.linspace(0, 1, o).reshape((1, o, 1) if ax == 1 else (o, 1, 1))
        head = arr.take(range(o), axis=ax)
        tail = arr.take(range(n - o, n), axis=ax)
        blended = head * t + tail * (1 - t)
        body = arr.take(range(o, n - o), axis=ax)
        arr = np.concatenate([blended, body], axis=ax)
    out = Image.fromarray(arr.round().clip(0, 255).astype(np.uint8), "RGBA")
    return out.resize(size, Image.LANCZOS)


# The plain maps are inputs to tools/hw_zone_shroud.py, which writes the final map files
# (seam-fixed hw26-map-{d,m}.png plus the zone1 / zone12 / zone123 variants).
MAP_BASE = os.path.join(HW, "variants", "round3", "map_zones", "base")


def save(im, rel, quality=(65, 92), dither=1.0):
    dst = (os.path.join(MAP_BASE, os.path.basename(rel)) if rel.startswith("map/hw26-map-")
           else os.path.join(OUT, rel))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rgba = im.convert("RGBA")
    try:
        q = imagequant.quantize_pil_image(rgba, dithering_level=dither, max_colors=256,
                                          min_quality=quality[0], max_quality=quality[1])
        q.save(dst, optimize=True)
        how = "quantized"
    except RuntimeError:  # can't reach the quality floor in 256 colours (e.g. smooth skies): keep truecolour
        (rgba if rgba.getextrema()[3][0] < 255 else rgba.convert("RGB")).save(dst, optimize=True, compress_level=9)
        how = "lossless"
    print(f"{rel:40s} {im.size[0]}x{im.size[1]}  {os.path.getsize(dst) // 1024:5d} KB  {how}", flush=True)


# ---------------------------------------------------------------- assets
def map_png(kind, rel, native=False):
    im = Image.open(src(rel)).convert("RGB")
    box = hw_map_guide.crop_box(kind)
    if im.size != hw_map_guide.GEN[kind]:  # scale the crop box if the model's size differs
        sx, sy = im.width / hw_map_guide.GEN[kind][0], im.height / hw_map_guide.GEN[kind][1]
        box = (round(box[0] * sx), round(box[1] * sy), round(box[2] * sx), round(box[3] * sy))
    if native:  # full-resolution master: same crop, no resize
        return im.crop(box).convert("RGBA")
    return upscale(im.crop(box), hw_map_guide.EXPORT[kind]).convert("RGBA")


def fog():
    im = Image.open(src(f"{R2}/fog/1")).convert("RGB")
    w = round(im.height * 2048 / 1200)
    im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height)).resize((2048, 1200), Image.LANCZOS)
    # tile while still on black (blending straight-alpha colour amplifies noise), then cut alpha
    return alpha_from_black(seamless(im).convert("RGB"), gain=1.6, max_alpha=0.85)  # "a bit transparent"


def meter_track(W=1200, h=48, rel=f"{R2}/meter/track_4k"):
    im = cutout(rel)
    im = im.crop(bbox(im))
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    cap = h * 2  # keep the carved end caps undistorted, stretch only the middle
    left, right = im.crop((0, 0, cap, h)), im.crop((im.width - cap, 0, im.width, h))
    mid = im.crop((cap, 0, im.width - cap, h)).resize((W - 2 * cap, h), Image.LANCZOS)
    out = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    for part, x in ((left, 0), (mid, cap), (right, W - cap)):
        out.alpha_composite(part, (x, 0))
    return out


def meter_fill(W=1200, h=48, rel=f"{R2}/meter/fill_4k"):
    """Cut the glowing band, scale it to height h keeping its proportions (so the swirls
    aren't squashed), make it seamless left-right and repeat it to width W."""
    im = Image.open(src(rel)).convert("RGB")
    b = bbox(alpha_from_black(im, gain=1.4))
    # middle half of the band's height: the core of the mist, wide enough that one repeat
    # spans about the whole bar, so no pattern shows
    h0 = b[3] - b[1]
    band = im.crop((im.width // 16, b[1] + h0 // 4, im.width - im.width // 16, b[3] - h0 // 4))
    band = band.resize((round(band.width * h / band.height), h), Image.LANCZOS)
    # even out brightness along the bar (the painting has periodic hot spots) but keep the swirls:
    # divide each pixel by its row's heavily blurred brightness, times the row's mean
    arr = np.asarray(band, np.float32)
    lum = arr.mean(axis=2)
    k = max(3, band.width // 6) | 1
    pad = np.pad(lum, ((0, 0), (k, k)), mode="wrap")
    blur = cv2.blur(pad, (k, 1))[:, k:-k]
    gain = (lum.mean(axis=1, keepdims=True) + 1) / (blur + 1)
    arr = np.clip(arr * gain[..., None], 0, 255)
    band = seamless(Image.fromarray(arr.astype(np.uint8), "RGB"), axis="x").convert("RGB")
    strip = Image.new("RGB", (W, h))
    for x in range(0, W, band.width):
        strip.paste(band, (x, 0))
    return alpha_from_black(strip, gain=1.4)


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


# Per-character framing, as fractions of the full figure's bounding box:
# bust = (top, height) of the square bust crop; avatar = (cx, cy, size) inside the bust.
FRAMING = {"keeper": {"bust": (0.0, 0.46), "avatar": (0.5, 0.36, 0.62)},
           "kid": {"bust": (0.0, 0.62), "avatar": (0.5, 0.56, 0.62)}}


def character(rel, name):
    """full (800x1200), bust (600x600), avatar (128x128) from one cutout."""
    im = cutout(rel)
    im = im.crop(bbox(im))
    full = place(im, (800, 1200), (760, 1170), anchor="bottom", bottom_pad=10)
    fb = bbox(full)
    fh = fb[3] - fb[1]
    top, frac = FRAMING[name]["bust"]
    side = int(fh * frac)
    cx = (fb[0] + fb[2]) // 2
    y0 = fb[1] + int(fh * top) - 10
    bust = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    bust.alpha_composite(full.crop((cx - side // 2, y0, cx + side // 2, y0 + side)))
    bust = bust.resize((600, 600), Image.LANCZOS)
    ax, ay, asz = FRAMING[name]["avatar"]
    a = int(600 * asz)
    l, t = int(600 * ax - a / 2), int(600 * ay - a / 2)
    av = Image.new("RGBA", (a, a), (0, 0, 0, 0))
    av.alpha_composite(bust.crop((max(l, 0), max(t, 0), min(l + a, 600), min(t + a, 600))), (max(-l, 0), max(-t, 0)))
    return full, bust, av.resize((128, 128), Image.LANCZOS)


def scene(rel, size, focus_y=0.5):
    """Opaque banner: crop the generated scene to the export aspect (full width, vertical
    position set by focus_y) and upscale."""
    im = Image.open(src(rel)).convert("RGB")
    ew, eh = size
    if im.width / im.height > ew / eh:
        w = round(im.height * ew / eh)
        im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height))
    else:
        h = round(im.width * eh / ew)
        top = round((im.height - h) * focus_y)
        im = im.crop((0, top, im.width, top + h))
    return upscale(im, size)


def build():
    yield "map/hw26-map-d.png", lambda: map_png("d", f"{R2}/map/E2_4k")
    yield "map/hw26-map-m.png", lambda: map_png("m", f"{R2}/map/F1_4k")
    yield "masters/hw26-map-d@native.png", lambda: map_png("d", f"{R2}/map/E2_4k", native=True)
    yield "masters/hw26-map-m@native.png", lambda: map_png("m", f"{R2}/map/F1_4k", native=True)
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
    yield "masters/hw26-meter-track@4x.png", lambda: meter_track(2400, 96)
    yield "masters/hw26-meter-fill@4x.png", lambda: meter_fill(2400, 96)
    yield "meter/hw26-lantern-on.png", lambda: place(cutout(f"{R1}/lantern/A"), (96, 96), (88, 90))
    yield "meter/hw26-lantern-off.png", lambda: place(cutout(f"{R2}/lantern/off"), (96, 96), (88, 90))
    for name, rel in (("keeper", f"{R1}/keeper/B"), ("kid", f"{R1}/kid/A")):
        parts = {}
        for part in ("full", "bust", "avatar"):
            def fn(part=part, rel=rel, parts=parts, name=name):
                if not parts:
                    parts.update(zip(("full", "bust", "avatar"), character(rel, name)))
                return parts[part]
            yield f"char/hw26-{name}-{part}.png", fn
    for n, rel in ITEMS.items():
        yield f"shop/hw26-item-{n}.png", lambda rel=rel: place(cutout(rel), (192, 192), (172, 172))
    yield "modal/hw26-new-zone.png", lambda: scene(f"{R2}/popup/B", (1040, 560), focus_y=0.45)
    yield "shop/hw26-shop.png", lambda: scene(f"{R2}/shop/A", (1600, 600), focus_y=0.5)
    # Round 6 board-style trail map (labelled, and clean for live labels); no fog
    for name, v in (("hw26-trailmap", "A_nofog"), ("hw26-trailmap-clean", "A_clean")):
        rel = f"variants/round6/map_board_fix/{v}"
        yield f"trailmap/{name}.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA").resize((2752, 1536), Image.LANCZOS)
        yield f"masters/{name}@native.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA")
    # Round 7: each approved house in its own 16:9 zone scene (no fog)
    for z in ("z1", "z2", "z3", "z4"):
        rel = f"variants/round7/house_scene/{z}"
        yield f"scene/hw26-house-{z}-scene.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA").resize((2752, 1536), Image.LANCZOS)
        yield f"masters/hw26-house-{z}-scene@native.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA")
    # Round 8: four more houses per zone (Hollow Woods, Graveyard), each bigger and creepier
    for zone in ("woods", "grave"):
        for i in "1234":
            rel = f"variants/round8/{zone}/{i}"
            yield f"scene/hw26-{zone}-house-{i}-scene.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA").resize((2752, 1536), Image.LANCZOS)
            yield f"masters/hw26-{zone}-house-{i}-scene@native.png", lambda rel=rel: Image.open(src(rel)).convert("RGBA")
    yield "shop/hw26-sold-out.png", lambda: place(cutout(f"{R1}/soldout/A"), (192, 192), (176, 176))


if __name__ == "__main__":
    only = sys.argv[1:]
    for rel, fn in build():
        if only and not any(rel.startswith(o) for o in only):
            continue
        q = (0, 95) if rel.startswith(("map/hw26-map", "masters/hw26-map", "trailmap/", "masters/hw26-trailmap", "scene/", "masters/hw26-house-z", "masters/hw26-woods-", "masters/hw26-grave-", "modal/", "shop/hw26-shop")) else (65, 92)
        # dithering shows as grain on soft semi-transparent textures
        save(fn(), rel, quality=q, dither=0.0 if rel in ("map/hw26-fog.png", "meter/hw26-meter-fill.png") else 1.0)
