#!/usr/bin/env python3
"""motion/hw26-g3-walk.json: G3 walk cycle traced from the approved map sprite.

Frame 0 matches map/hw26-g3.png. Parts (in the sprite's 256px layout): cloak flap
(sways from the shoulder), candy bag (swings from the hand), front arm, two boots
(alternating stance/swing under the dress hem), head+body (bobs). 30 fps, 18 frames.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import lottie_kit as K  # noqa: E402
import lottie_trace as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
OUT = os.path.join(HW, "final", "halloween-2026", "motion", "hw26-g3-walk.json")
SRC = os.path.join(HW, ".cutout_cache", "variants__round2__g3__1.png")
S = 4  # trace at 4x the 256 layout
N = 18

# part polygons in 256-layout coords (from the gridded sprite)
BAG = [(108, 146), (122, 145), (131, 151), (130, 162), (123, 168), (125, 190), (119, 207), (100, 211),
       (79, 209), (73, 195), (75, 176), (85, 161), (96, 157), (106, 151)]
CLOAK = [(96, 62), (122, 70), (124, 90), (112, 103), (104, 122), (104, 140), (100, 150), (86, 158),
         (75, 176), (73, 200), (78, 211), (70, 216), (56, 198), (58, 178), (66, 156), (76, 130), (86, 104), (92, 82)]
ARM = [(160, 121), (179, 120), (188, 133), (188, 160), (176, 162), (165, 151), (159, 137)]
BOOT_X = {"back": (84, 132), "front": (148, 204)}
FACE = [(146, 32), (166, 30), (172, 44), (170, 64), (160, 68), (148, 60)]
PIVOT = {"bag": (117, 149), "cloak": (118, 76), "arm": (167, 123)}


def sprite_4x():
    """Hi-res cutout placed exactly like tools/hw_export.py g3(), rendered at 4x."""
    im = Image.open(SRC).convert("RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    im = im.crop(bb)
    s = min(236 / im.width, 244 / im.height)
    w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
    x0, y0 = (256 - w) // 2, 256 - 6 - h
    big = im.resize((w * S, h * S), Image.LANCZOS)
    canvas = Image.new("RGBA", (256 * S, 256 * S), (0, 0, 0, 0))
    canvas.alpha_composite(big, (x0 * S, y0 * S))
    return np.asarray(canvas)


def main():
    rgba = sprite_4x()
    labels, pal, opaque = T.quantise(rgba, k=14, alpha_min=150)
    ink = 0  # darkest cluster is the outline colour
    H = rgba.shape[0]
    bag = T.poly_mask(labels.shape, [BAG], S)
    cloak = T.poly_mask(labels.shape, [CLOAK], S) & ~bag
    arm = T.poly_mask(labels.shape, [ARM], S)
    # hem line per column: lowest lime-ish pixel (bright, green-yellow), boots start just below it
    rgb = rgba[..., :3].astype(int)
    is_lime = (rgb[..., 1] > 170) & (rgb[..., 0] > 140) & (rgb[..., 2] < 90) & opaque
    boots = {}
    yy = np.arange(H)[:, None]
    for name, (xa, xb) in BOOT_X.items():
        m = np.zeros(labels.shape, bool)
        for x in range(xa * S, xb * S):
            col = np.where(is_lime[:, x])[0]
            top = (col.max() + 3 * S) if len(col) else 229 * S
            m[top:, x] = True
        boots[name] = m & opaque & (yy < 252 * S)
    body = opaque & ~bag & ~cloak & ~arm & ~boots["back"] & ~boots["front"]
    deep = "#2e2742"
    # finer tracing for the face only (hands and candy cost too many bytes for 128px)
    # skin pixels near the face, grown a little: follows the face edge instead of a box
    rgbf = rgba[..., :3].astype(int)
    skin = (rgbf[..., 0] > 150) & (rgbf[..., 0] > rgbf[..., 1] + 25) & (rgbf[..., 1] > rgbf[..., 2] + 5) & opaque
    detail = (cv2.dilate((skin & T.poly_mask(labels.shape, [FACE], S)).astype(np.uint8),
                         np.ones((7, 7), np.uint8)) > 0)

    c = K.Comp("hw26-g3-walk", 256, 256, N)

    def part_layer(nm, mask, pivot, ks_anim, parent=None, backfill=None, layer_extra=None):
        items = T.trace_part(labels, pal, mask, S, ink, offset=(0, 0), backfill=backfill, detail=detail)
        ks = K.transform(p=pivot, a=pivot, **ks_anim)
        return c.shape(nm, items, ks=ks, parent=parent)

    # body null carries the bob; everything except boots + shadow hangs off it
    bob = [(0, [128, 128], "sine"), (4.5, [128, 125.5], "sine"), (9, [128, 128], "sine"),
           (13.5, [128, 125.5], "sine"), (18, [128, 128])]
    body_null = c.null("body", ks=K.transform(p=bob, a=(128, 128)))
    swing = lambda amp, ph: [(t, amp * np.sin(2 * np.pi * (t / N + ph)), "linear") for t in np.arange(0, N + 0.01, 1.5)]
    # stacking: first added = top
    part_layer("front_arm", arm, PIVOT["arm"], {"r": swing(-4, 0)}, parent=body_null)
    part_layer("candy_bag", bag, PIVOT["bag"], {"r": swing(6, 0.08)}, parent=body_null)
    c.shape("head_body", T.trace_part(labels, pal, body, S, ink, detail=detail,
                                      backfill=((bag | arm) & opaque, deep)), parent=body_null)
    cloak_bf = cv2.dilate(cloak.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
    cloak_bf = cloak_bf & (body | bag) & T.poly_mask(labels.shape, [[(x + 6, y) for x, y in CLOAK]], S)
    part_layer("cloak", cloak, PIVOT["cloak"],
               {"r": swing(2.5, 0.25), "s": [(t, [100 + 2 * np.sin(2 * np.pi * (t / N + 0.25)), 100], "linear")
                                             for t in np.arange(0, N + 0.01, 1.5)]},
               parent=body_null, backfill=(cloak_bf, deep))

    # boots: stance (slides back on the ground) then swing (lifts and comes forward)
    stride = 48

    def boot_kfs(x0, swing_first):
        a, b = (x0, x0 + stride) if swing_first else (x0, x0 - stride)
        if swing_first:  # back boot: swing forward f0-9, stance back f9-18
            return [(0, [a, 0], "inout"), (4.5, [(a + b) / 2, -6], "inout"), (9, [b, 0], "linear"), (18, [a, 0])]
        return [(0, [a, 0], "linear"), (9, [b, 0], "inout"), (13.5, [(a + b) / 2, -6], "inout"), (18, [a, 0])]

    for name, swing_first in (("front", False), ("back", True)):
        m = boots[name]
        items = T.trace_part(labels, pal, m, S, ink)
        # shaft filler above the boot, hidden under the hem unless the boot moves
        ys, xs = np.where(m)
        bx0, bx1, by0 = xs.min() / S, xs.max() / S, ys.min() / S
        shaft = K.group([K.rect([max(6, (bx1 - bx0) * 0.45), 16], p=((bx0 + bx1) / 2 - 4, by0 - 6), r=3),
                         K.fill("#1b1720")], nm="shaft")
        items.append(shaft)
        pos = [(kf[0], kf[1], kf[2]) if len(kf) > 2 else (kf[0], kf[1]) for kf in boot_kfs(0, swing_first)]
        c.shape(f"boot_{name}", items, ks=K.transform(p=pos, a=(0, 0)))

    # soft ground shadow
    sh_scale = [(0, [100, 100], "sine"), (4.5, [92, 92], "sine"), (9, [100, 100], "sine"), (13.5, [92, 92], "sine"),
                (18, [100, 100])]
    c.shape("shadow", [K.group([K.ellipse([104, 14]),
                                K.radial([(0, "#000000", 0.42), (1, "#000000", 0)], start=(0, 0), end=(52, 0))],
                               nm="shadow")],
            ks=K.transform(p=(140, 249), s=sh_scale))
    size = c.save(OUT)
    print("wrote", OUT, size // 1024, "KB")


if __name__ == "__main__":
    main()
