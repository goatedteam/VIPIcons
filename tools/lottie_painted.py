#!/usr/bin/env python3
"""Build the Haunted Trail Lotties from painted art (round 2 of the motion work).

  python tools/lottie_painted.py [name ...]   names: door pulse g3 pop brew rain drift lift bats

Every visible element is a painted sprite in the Goated style, embedded as a PNG asset:
Nano Banana 2 sheets cut by tools/hw_motion_assets.py, the approved candy for the candy
pieces, G3's own painted cutout as a puppet, and the approved shroud for the fog. Only
pure light (glows, the zone-tinted bloom) stays vector, on layers named "tint" where the
zone colour applies. Output: halloween/final/halloween-2026/motion/.
"""
import math
import os
import random
import sys

import cv2
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import lottie_kit as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
SPR = os.path.join(HW, "variants", "round4_motion", "sprites")
CACHE = os.path.join(HW, ".cutout_cache")
OUT = os.path.join(HW, "final", "halloween-2026", "motion")


def sprite(name):
    return Image.open(os.path.join(SPR, name + ".png")).convert("RGBA")


def trim(im):
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(bb) if bb else im


CANDY = None


def candy_img():
    """The approved candy (hw26-candy source cutout), trimmed."""
    global CANDY
    if CANDY is None:
        CANDY = trim(Image.open(os.path.join(CACHE, "variants__round2__candy__orange_logo.png")).convert("RGBA"))
    return CANDY


class Painter:
    """Comp wrapper that places embedded sprites by their centre at a display width."""

    def __init__(self, comp):
        self.c = comp
        self.assets = {}

    def asset(self, ref, im, max_side=None):
        if ref not in self.assets:
            self.assets[ref] = self.c.add_image(ref, im, max_side)
        return self.assets[ref]

    def put(self, nm, ref, width, p, r=0, o=100, s=None, parent=None, ip=0, op=None, anchor=None, **kw):
        w, h = self.assets[ref]
        base = width / w * 100
        if s is None:
            sc = (base, base)
        elif isinstance(s, list):  # keyframed multiplier in percent
            sc = [(kf[0], [base * kf[1][0] / 100, base * kf[1][1] / 100]) + tuple(kf[2:]) for kf in s]
        else:
            sc = (base * s[0] / 100, base * s[1] / 100)
        ks = K.transform(a=anchor or (w / 2, h / 2), p=p, s=sc, r=r, o=o)
        return self.c.image_layer(nm, ref, ks=ks, parent=parent, ip=ip, op=op if op is not None else self.c.frames, **kw)


def soft_disc(d, color, alpha=1.0, core=0.0):
    return [K.group([K.ellipse([d, d]),
                     K.radial([(0, color, alpha), (max(core, 0.01), color, alpha), (1, color, 0)], end=(d / 2, 0))])]


def halo_ring(d, color="#ffffff", alpha=0.8, width=0.18):
    """Soft glowing ring: radial gradient peaking near the edge."""
    a = 1 - width
    return [K.group([K.ellipse([d, d]),
                     K.radial([(0, color, 0), (a - 0.12, color, 0), (a, color, alpha), (min(1, a + 0.1), color, alpha * 0.35),
                               (1, color, 0)], end=(d / 2, 0))])]


def wrap_life(n, t0, life, fn, step=2):
    """Keyframes for an element that repeats every `life` frames starting at t0, inside an n-frame
    loop. fn(u) -> value for life fraction u in [0, 1); values at u=0 and u->1 should be equal
    (e.g. invisible), so the jump at the wrap is hidden."""
    pts = sorted({0.0, float(n)} | {float(t) for t in np.arange(0, n + 0.01, step)} |
                 {float((t0 + k * life) % n) for k in range(int(n / life) + 1)} |
                 {float((t0 + k * life - 0.01) % n) for k in range(1, int(n / life) + 2)})
    out = []
    for t in pts:
        if t < 0 or t > n:
            continue
        u = ((t - t0) % life) / life
        if abs(t - n) < 1e-6:
            u = ((0 - t0) % life) / life
        out.append((round(t, 2), fn(u), "linear"))
    return out


# ------------------------------------------------------------------ 1. door opens
def door_open():
    n = 42
    c = K.Comp("hw26-door-open", 320, 320, n)
    P = Painter(c)
    rnd = random.Random(13)
    P.asset("candy", candy_img(), 160)
    for i in (1, 2, 3, 4, 7):
        P.asset(f"spark{i}", sprite(f"sparkle_{i}"), 96)
    P.asset("burst", sprite("burst_1"), 360)
    c.marker(10, "swap_to_done")  # the flash covers the doorway here: swap the house PNG open -> done
    door = c.null("door", ks=K.transform(p=(168, 204)))
    size = c.null("door_size", ks=K.transform(s=(100, 100)), parent=door)
    fade = [(0, 100), (34, 100, "in"), (41, 0)]
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * 0.42
        dist = rnd.uniform(50, 84)
        t0 = 10 + i
        P.put(f"spark{i}", f"spark{(1, 2, 3, 4, 7)[i % 5]}", rnd.uniform(26, 40),
              p=[(t0, [0, -10], "out"), (t0 + 13, [math.cos(a) * dist, -10 + math.sin(a) * dist])],
              s=[(t0, [0, 0], "out"), (t0 + 4, [115, 115], "inout"), (t0 + 14, [0, 0])],
              r=[(t0, 0, "linear"), (t0 + 14, 70)], parent=door, ip=t0)
    for i in range(8):
        dx = (i - 3.5) * rnd.uniform(14, 19) + rnd.uniform(-6, 6)
        peak, land = -rnd.uniform(48, 80), rnd.uniform(50, 74)
        t0 = 9 + (i % 4) * 2 + (i // 4)
        P.put(f"candy{i}", "candy", rnd.uniform(24, 30),
              p=[(t0, [0, 8], "out"), (t0 + 9, [dx * 0.75, peak], "in"), (t0 + 20, [dx * 1.25, land])],
              s=[(t0, [15, 15], "back"), (t0 + 5, [100, 100])],
              r=[(t0, rnd.uniform(-30, 30), "linear"), (t0 + 20, rnd.uniform(-240, 240))], o=fade, parent=door, ip=t0)
    # painted light bursting out of the doorway (scaled to each house's door by door_size)
    P.put("door_burst", "burst", 150, p=(0, -6), parent=size,
          s=[(1, [25, 25], "out"), (9, [100, 100], "inout"), (13, [92, 92], "in"), (30, [110, 110])],
          o=[(1, 0, "out"), (6, 100), (13, 100, "in"), (30, 0)])
    c.shape("tint", [K.group(soft_disc(210, "#ffffff", 0.85, 0.12), nm="bloom", s=[(2, [20, 20], "out"), (16, [100, 100])]),
                     K.group(halo_ring(170, "#ffffff", 0.9), nm="ring", s=[(8, [35, 35], "out"), (28, [175, 175])],
                             o=[(8, 100), (28, 0)])],
            ks=K.transform(o=[(2, 0, "out"), (10, 90), (30, 80, "in"), (41, 0)]), parent=door)
    return c


# ------------------------------------------------------------------ 2. house pulse
def house_pulse():
    n = 48
    c = K.Comp("hw26-house-pulse", 400, 400, n)
    P = Painter(c)
    P.asset("mote_w", sprite("sparkle_5"), 64)
    P.asset("mote_g", sprite("sparkle_6"), 64)
    P.asset("star", sprite("sparkle_4"), 64)
    rnd = random.Random(8)
    for i in range(9):  # embers drifting up around the house, twinkling
        x0, y0 = rnd.uniform(110, 290), rnd.uniform(200, 300)
        rise = rnd.uniform(70, 120)
        life = rnd.choice([24, 48])
        t0 = rnd.uniform(0, life)
        sway = rnd.uniform(-14, 14)
        ref = ("mote_w", "mote_g", "star")[i % 3]
        size = rnd.uniform(10, 18) if ref != "star" else rnd.uniform(16, 24)
        P.put(f"mote{i}", ref, size,
              p=wrap_life(n, t0, life, lambda u, x0=x0, y0=y0, rise=rise, sway=sway:
                          [x0 + sway * math.sin(u * math.pi * 2), y0 - rise * u]),
              o=wrap_life(n, t0, life, lambda u: 100 * math.sin(math.pi * u) ** 1.5))
    glow = K.group(soft_disc(330, "#ffffff", 0.75, 0.2), nm="glow",
                   s=[(t, [v, v], "linear") for t, v in [(t, 98 + 8 * math.sin(2 * math.pi * t / n - math.pi / 2)) for t in range(0, n + 1, 4)]],
                   o=[(t, v, "linear") for t, v in [(t, 81 + 19 * math.sin(2 * math.pi * t / n - math.pi / 2)) for t in range(0, n + 1, 4)]])
    ring = K.group(halo_ring(230, "#ffffff", 0.85), nm="ring", s=[(0, [60, 60], "out"), (n, [165, 165])],
                   o=[(0, 0, "out"), (8, 80, "in"), (n, 0)])
    c.shape("tint", [ring, glow], ks=K.transform(p=(200, 200)))
    return c


# ------------------------------------------------------------------ 3. G3 walk (painted puppet)
def g3_walk():
    import lottie_g3_walk as G
    n, S = 18, 3  # parts are cut at 3x the 256 layout (the source cutout is ~3.2x), so she stays crisp
    src = Image.open(os.path.join(CACHE, "variants__round2__g3__1.png")).convert("RGBA")
    bb = src.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    src = src.crop(bb)
    s = min(236 / src.width, 244 / src.height)
    w, h = max(1, round(src.width * s)), max(1, round(src.height * s))
    x0, y0 = (256 - w) // 2, 256 - 6 - h
    canvas = Image.new("RGBA", (256 * S, 256 * S), (0, 0, 0, 0))
    canvas.alpha_composite(src.resize((w * S, h * S), Image.LANCZOS), (x0 * S, y0 * S))
    rgba = np.asarray(canvas).copy()
    a = rgba[..., 3]
    opaque = a > 8
    pm = lambda poly: np.asarray(_poly(rgba.shape, poly, S)) > 0
    bag, arm = pm(G.BAG) & opaque, pm(G.ARM) & opaque
    cloak = pm(G.CLOAK) & opaque & ~bag
    rgb = rgba[..., :3].astype(int)
    lime = (rgb[..., 1] > 170) & (rgb[..., 0] > 140) & (rgb[..., 2] < 90) & (a > 150)
    boots = {}
    for name, (xa, xb) in G.BOOT_X.items():
        m = np.zeros(a.shape, bool)
        for x in range(xa * S, xb * S):
            col = np.where(lime[:, x])[0]
            top = (col.max() + 3 * S) if len(col) else 229 * S
            m[top:, x] = True
        boots[name] = m & opaque & (np.arange(a.shape[0])[:, None] < 250 * S)
    body = opaque & ~bag & ~arm & ~cloak & ~boots["back"] & ~boots["front"]

    def layer_img(mask, fill_holes=None, extend=None):
        """RGBA of one part; optional inpainted backfill so moving parts don't open gaps."""
        img = rgba.copy()
        keep = mask.copy()
        if fill_holes is not None:
            hole = fill_holes & ~mask
            rgb_ = cv2.inpaint(np.ascontiguousarray(img[..., :3]), (hole | ~(mask | hole)).astype(np.uint8) * 0 + hole.astype(np.uint8) * 255,
                               9, cv2.INPAINT_TELEA)
            img[..., :3] = np.where(hole[..., None], rgb_, img[..., :3])
            img[..., 3] = np.where(hole, 255, img[..., 3])
            keep = keep | hole
        if extend is not None:
            img[..., :3] = np.where(extend[..., None], np.array([29, 24, 34]), img[..., :3])
            img[..., 3] = np.where(extend, 255, img[..., 3])
            keep = keep | extend
        img[..., 3] = np.where(keep, img[..., 3], 0)
        im = Image.fromarray(img.astype(np.uint8), "RGBA")
        bb = im.getchannel("A").getbbox()
        return im.crop(bb), bb

    c = K.Comp("hw26-g3-walk", 256, 256, n)
    P = Painter(c)

    def part(nm, img_bb, pivot, parent=None, **anim):
        im, bb = img_bb
        P.asset(nm, im)
        anchor = (pivot[0] * S - bb[0], pivot[1] * S - bb[1])
        return P.put(nm, nm, im.width / S, p=anim.pop("p", pivot), anchor=anchor, parent=parent, **anim)

    swing = lambda amp, ph: [(t, amp * math.sin(2 * math.pi * (t / n + ph)), "linear") for t in np.arange(0, n + 0.01, 1.5)]
    bob = [(0, [128, 128], "sine"), (4.5, [128, 125.5], "sine"), (9, [128, 128], "sine"), (13.5, [128, 125.5], "sine"), (18, [128, 128])]
    body_null = c.null("body", ks=K.transform(p=bob, a=(128, 128)))
    grow = lambda m, k: cv2.dilate(m.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    part("front_arm", layer_img(arm), G.PIVOT["arm"], parent=body_null, r=swing(-4, 0))
    part("candy_bag", layer_img(bag), G.PIVOT["bag"], parent=body_null, r=swing(6, 0.08))
    part("head_body", layer_img(body, fill_holes=(bag | arm) & grow(body, 31)), (128, 128), parent=body_null)
    cloak_bf = grow(cloak, 61) & (body | bag) & pm([(x + 6, y) for x, y in G.CLOAK])
    part("cloak", layer_img(cloak, fill_holes=cloak_bf | (bag & grow(cloak, 31))), G.PIVOT["cloak"], parent=body_null,
         r=swing(2.5, 0.25), s=[(t, [100 + 2 * math.sin(2 * math.pi * (t / n + 0.25)), 100], "linear") for t in np.arange(0, n + 0.01, 1.5)])
    stride = 48
    for name, swing_first in (("front", False), ("back", True)):
        m = boots[name]
        ys, xs = np.where(m)
        shaft = np.zeros_like(m)
        top = ys.min()
        cx0, cx1 = int(np.percentile(xs, 15)), int(np.percentile(xs, 70))
        shaft[max(0, top - 14 * S):top + 2, cx0:cx1] = True
        if swing_first:
            pos = [(0, [128, 128], "inout"), (4.5, [128 + stride / 2, 122], "inout"), (9, [128 + stride, 128], "linear"), (18, [128, 128])]
        else:
            pos = [(0, [128, 128], "linear"), (9, [128 - stride, 128], "inout"), (13.5, [128 - stride / 2, 122], "inout"), (18, [128, 128])]
        part(f"boot_{name}", layer_img(m, extend=shaft & ~m), (128, 128), p=pos)
    sh = [(0, [100, 100], "sine"), (4.5, [92, 92], "sine"), (9, [100, 100], "sine"), (13.5, [92, 92], "sine"), (18, [100, 100])]
    c.shape("shadow", [K.group([K.ellipse([104, 14]), K.radial([(0, "#000000", 0.42), (1, "#000000", 0)], end=(52, 0))])],
            ks=K.transform(p=(140, 249), s=sh))
    return c


def _poly(shape, poly, scale):
    from PIL import ImageDraw
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([(x * scale, y * scale) for x, y in poly], fill=255)
    return m


# ------------------------------------------------------------------ 4. candy pop
def pop():
    n = 14
    c = K.Comp("hw26-pop", 192, 192, n)
    P = Painter(c)
    for i in (1, 2, 3, 4, 7):
        P.asset(f"spark{i}", sprite(f"sparkle_{i}"), 96)
    P.asset("orb", sprite("sparkle_5"), 160)
    c.null("icon_scale_ref", ks=K.transform(p=(96, 96), s=[(0, [100, 100], "out"), (4, [145, 145], "inout"),
                                                           (9, [92, 92], "inout"), (13, [100, 100])]))
    rnd = random.Random(5)
    for i in range(10):
        a = i * math.pi / 5 + 0.2
        dist = rnd.uniform(58, 84)
        P.put(f"star{i}", f"spark{(2, 4, 3, 7, 1)[i % 5]}", rnd.uniform(22, 36),
              p=[(0, [96 + math.cos(a) * 22, 96 + math.sin(a) * 22], "out"), (12, [96 + math.cos(a) * dist, 96 + math.sin(a) * dist])],
              s=[(0, [0, 0], "out"), (4, [115, 115], "in"), (13, [0, 0])], r=[(0, 0, "linear"), (13, 60)])
    P.put("big_star", "spark4", 150, p=(96, 96), s=[(0, [20, 20], "out"), (5, [100, 100], "in"), (11, [40, 40])],
          r=[(0, 0, "linear"), (11, 45)], o=[(0, 100), (6, 100, "in"), (11, 0)])
    P.put("flash", "orb", 120, p=(96, 96), s=[(0, [30, 30], "out"), (5, [110, 110])], o=[(0, 90, "in"), (9, 0)])
    c.shape("glow", soft_disc(176, "#d4ff00", 0.45, 0.0),
            ks=K.transform(p=(96, 96), s=[(0, [40, 40], "out"), (8, [100, 100])], o=[(0, 0, "out"), (3, 100), (13, 0)]))
    return c


# ------------------------------------------------------------------ 5. cauldron brew
def brew():
    n = 45
    c = K.Comp("hw26-brew", 400, 400, n)
    P = Painter(c)
    rnd = random.Random(21)
    pot = trim(sprite("cauldron_1"))
    P.asset("cauldron", pot, 640)
    pw, ph = P.assets["cauldron"]
    disp_w = 300
    k = disp_w / pw
    top_left = (200 - disp_w / 2, 380 - ph * k)  # feet near the bottom of the canvas
    # find the brew surface (bright green) in the sprite -> comp coordinates
    arr = np.asarray(pot.resize((pw, ph)))
    green = (arr[..., 1] > 170) & (arr[..., 0] < 170) & (arr[..., 3] > 200)
    ys, xs = np.where(green)
    lx0, lx1, ly0, ly1 = np.percentile(xs, 2), np.percentile(xs, 98), np.percentile(ys, 2), np.percentile(ys, 98)
    lcx, lcy = top_left[0] + (lx0 + lx1) / 2 * k, top_left[1] + (ly0 + ly1) / 2 * k
    lrx, lry = (lx1 - lx0) / 2 * k, (ly1 - ly0) / 2 * k
    for i in (2, 4, 7):
        P.asset(f"spark{i}", sprite(f"sparkle_{i}"), 96)
    for i in (1, 2, 3):
        P.asset(f"smoke{i}", sprite(f"smoke_{i}"), 300)
    for i in (1, 2, 4):
        P.asset(f"drop{i}", sprite(f"potion_{i}"), 96)
    P.asset("bubble", sprite("potion_5"), 96)

    for i in range(6):  # sparkles around the risen item
        a = i * math.pi / 3 + 0.4
        t0 = 22 + i
        P.put(f"spark{i}", f"spark{(2, 4, 7)[i % 3]}", rnd.uniform(26, 38),
              p=[(t0, [200 + math.cos(a) * 40, 120 + math.sin(a) * 40], "out"), (t0 + 14, [200 + math.cos(a) * 95, 120 + math.sin(a) * 85])],
              s=[(t0, [0, 0], "out"), (t0 + 5, [110, 110], "in"), (t0 + 15, [0, 0])], r=[(t0, 0, "linear"), (t0 + 15, 90)], ip=t0)
    for i in range(7):  # painted green smoke puff
        a = -math.pi / 2 + (i - 3) * 0.42
        d = rnd.uniform(60, 110)
        t0 = 9 + i % 3
        P.put(f"smoke{i}", f"smoke{1 + i % 3}", rnd.uniform(85, 115),
              p=[(t0, [lcx + (i - 3) * 12, lcy - 10], "out"), (t0 + 18, [lcx + math.cos(a) * d * 1.25, lcy - 30 + math.sin(a) * d])],
              s=[(t0, [25, 25], "out"), (t0 + 18, [120, 120])], r=[(t0, rnd.uniform(-10, 10), "linear"), (t0 + 18, rnd.uniform(-25, 25))],
              o=[(t0, 0, "out"), (t0 + 3, 85), (t0 + 9, 60, "in"), (t0 + 18, 0)], ip=t0)
    for i in range(6):  # splash drops
        dx = (i - 2.5) * 26
        t0 = 8 + i % 2
        P.put(f"drop{i}", f"drop{(1, 2, 4)[i % 3]}", rnd.uniform(14, 22),
              p=[(t0, [lcx + dx * 0.4, lcy - 4], "out"), (t0 + 7, [lcx + dx, lcy - 72], "in"), (t0 + 15, [lcx + dx * 1.35, lcy + 6])],
              r=[(t0, 0, "linear"), (t0 + 15, (i - 2.5) * 40)], o=[(t0, 100), (t0 + 13, 100, "in"), (t0 + 15, 0)], ip=t0, op=t0 + 16)
    # item rises out of the brew: precomp masked to the area above the surface line plus the surface itself
    sub = K.sub_comp(n, 400, 400)
    sub.add_image_asset("item", 192, 192, "item.png")
    sub.image_layer("item", "item", ks=K.transform(
        a=(96, 96), p=[(0, [200, lcy + 120]), (14, [200, lcy + 120], "back"), (28, [200, 118], "sine"), (37, [200, 126], "sine"), (45, [200, 120])],
        s=[(14, [55, 55], "back"), (28, [100, 100])], o=[(0, 0), (13, 0), (14, 100)]))
    c.d["assets"] += sub.d["assets"]
    c.add_precomp("item_rise", sub.d["layers"])
    c.precomp_layer("item_rise", "item_rise", 400, 400, ks=K.transform(),
                    hasMask=True, masksProperties=[K.mask([(0, 0), (400, 0), (400, lcy), (0, lcy)]),
                                     K.mask(K.ellipse_pts(lcx, lcy, lrx, lry))])
    for i in range(8):  # bubbles popping on the surface
        bx = lcx + rnd.uniform(-lrx * 0.7, lrx * 0.7)
        by = lcy + rnd.uniform(-lry * 0.4, lry * 0.4)
        t0 = rnd.choice([0, 3, 6, 9, 18, 26, 33, 38])
        P.put(f"bubble{i}", "bubble", rnd.uniform(12, 22), p=(bx, by),
              s=[(t0, [0, 0], "out"), (t0 + 5, [100, 100], "in"), (t0 + 7, [135, 135])], o=[(t0, 100), (t0 + 6, 100), (t0 + 7, 0)],
              ip=t0, op=t0 + 8)
    P.put("cauldron", "cauldron", disp_w, p=(200, top_left[1] + ph * k / 2),
          r=[(0, 0, "out"), (4, -2.5, "inout"), (8, 2, "inout"), (12, -1, "inout"), (16, 0)])
    c.shape("glow", soft_disc(320, "#3dff8a", 0.5, 0.05),
            ks=K.transform(p=(lcx, lcy - 10), s=[(0, [70, 70], "out"), (12, [115, 115], "inout"), (45, [95, 95])],
                           o=[(0, 50), (12, 100, "inout"), (45, 70)]))
    return c


# ------------------------------------------------------------------ 6. candy rain
def candy_rain():
    n, W = 90, 1080
    c = K.Comp("hw26-candy-rain", W, W, n)
    P = Painter(c)
    P.asset("candy", candy_img(), 256)
    for i in (2, 3, 4):
        P.asset(f"spark{i}", sprite(f"sparkle_{i}"), 96)
    rnd = random.Random(40)
    for i in range(40):
        dur = rnd.randint(44, 62)
        t0 = rnd.randint(0, n - dur - 1)
        x0 = rnd.uniform(40, W - 40)
        rot0, spin = rnd.uniform(0, 360), rnd.choice([-1, 1]) * rnd.uniform(180, 540)
        P.put(f"candy{i}", "candy", rnd.uniform(100, 170), ip=t0, op=t0 + dur + 1,
              p=[(t0, [x0, -90], "in"), (t0 + dur, [x0 + rnd.uniform(-90, 90), W + 90])],
              r=[(t0, rot0, "linear"), (t0 + dur, rot0 + spin)])
    for i in range(14):
        t0 = rnd.randint(0, n - 30)
        x = rnd.uniform(40, W - 40)
        P.put(f"sparkle{i}", f"spark{(2, 3, 4)[i % 3]}", rnd.uniform(34, 56), ip=t0, op=t0 + 29,
              p=[(t0, [x, rnd.uniform(60, 500)], "linear"), (t0 + 28, [x, rnd.uniform(560, 1000)])],
              s=[(t0, [0, 0], "out"), (t0 + 6, [100, 100], "inout"), (t0 + 14, [45, 45], "inout"), (t0 + 22, [100, 100], "in"), (t0 + 28, [0, 0])],
              r=[(t0, 0, "linear"), (t0 + 28, 90)])
    return c


# ------------------------------------------------------------------ 7. fog drift (tileable)
def _seamless(arr, axis, overlap=0.22):
    n = arr.shape[axis]
    o = int(n * overlap)
    t = np.linspace(0, 1, o).reshape((1, o, 1) if axis == 1 else (o, 1, 1))
    head, tail = arr.take(range(o), axis=axis), arr.take(range(n - o, n), axis=axis)
    return np.concatenate([head * t + tail * (1 - t), arr.take(range(o, n - o), axis=axis)], axis=axis)


def wisp_tile(size=1200):
    """Painted wisps sheet -> a size x size RGBA tile that repeats seamlessly both ways."""
    im = sprite("wisps_sheet")
    arr = np.asarray(im, np.float32)
    arr = _seamless(_seamless(arr, 1), 0)
    tile = Image.fromarray(arr.round().clip(0, 255).astype(np.uint8), "RGBA").resize((size, size // 2), Image.LANCZOS)
    full = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    full.paste(tile, (0, 0))
    full.paste(tile, (0, size // 2))  # same band twice: it is seamless top-to-bottom, so the stack is too
    return full


def fog_drift():
    n, W = 240, 1200
    c = K.Comp("hw26-fog-drift", W, W, n)
    P = Painter(c)
    tile = wisp_tile(W)
    # soft texture: stored at half resolution and scaled up (no visible loss, a quarter of the bytes)
    P.asset("wisps", tile, W // 2)
    P.asset("wisps_flip", ImageOps.flip(ImageOps.mirror(tile)), W // 2)
    for nm, ref, direction, opacity, dy in (("wisps_back", "wisps_flip", -1, 28, 300), ("wisps_front", "wisps", 1, 55, 0)):
        for k in (-1, 0, 1):  # three copies one tile apart, so the canvas is always covered while moving one tile
            for j in (-1, 0, 1):
                x = W / 2 + k * W
                y = W / 2 + j * W + dy
                P.put(f"{nm}_{k}_{j}", ref, W, o=opacity,
                      p=[(0, [x, y], "linear"), (n, [x + direction * W, y])])
    return c


# ------------------------------------------------------------------ 8. fog lift (approved shroud, in pieces)
def fog_lift():
    import hw_zone_shroud as Z
    n, W = 54, 1200
    c = K.Comp("hw26-fog-lift", W, W, n)
    P = Painter(c)
    rgb = Z.shroud_rgb((W, W), 26)
    base = Image.fromarray((rgb * 255).round().clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    rnd = random.Random(11)
    seeds = []
    step = 200
    for gy in range(6):
        for gx in range(6):
            seeds.append((gx * step + step / 2 + rnd.uniform(-55, 55), gy * step + step / 2 + rnd.uniform(-55, 55)))
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    d = np.stack([np.hypot(xx - x, yy - y) for x, y in seeds])
    noise = Z.smooth_noise(W, W, 99, scales=((10, 0.6), (26, 0.4))) * 60
    owner = np.argmin(d + noise[None] * 0, axis=0)
    ctr = (W / 2, W / 2)
    base_arr = np.asarray(base)
    layers = []
    for i, (sx, sy) in enumerate(seeds):
        cell = (owner == i).astype(np.uint8)
        # distance outside the cell, broken up by noise: alpha 1 inside, soft cloud edge 60-110 px beyond
        dist = cv2.distanceTransform(1 - cell, cv2.DIST_L2, 5)
        alpha = np.clip(1 - (dist - 30 + noise * 0.8) / 70, 0, 1)
        if alpha.max() == 0:
            continue
        arr = base_arr.copy()
        arr[..., 3] = (alpha * 255).astype(np.uint8)
        im = Image.fromarray(arr, "RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 4 else 0).getbbox()
        piece = im.crop(bb)
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        layers.append((math.dist((sx, sy), ctr), i, piece, cx, cy, sx, sy))
    for dd, i, piece, cx, cy, sx, sy in sorted(layers, key=lambda t: t[0]):  # centre pieces listed first (on top)
        ref = f"piece{i}"
        P.asset(ref, piece.resize((max(1, piece.width // 2), max(1, piece.height // 2)), Image.LANCZOS))
        ang = math.atan2(sy - ctr[1], sx - ctr[0]) if dd > 1 else rnd.uniform(0, 2 * math.pi)
        t0 = 3 + dd / 850 * 14
        travel = 560 + rnd.uniform(0, 160)
        P.put(ref, ref, piece.width, p=[(0, [cx, cy]), (t0, [cx, cy], "in"), (n, [cx + math.cos(ang) * travel, cy + math.sin(ang) * travel])],
              s=[(t0, [100, 100], "in"), (n, [135, 135])], o=[(t0 + 10, 100, "in"), (n - 2, 0)])
    P.asset("base", base, W // 2)
    P.put("base", "base", W, p=(W / 2, W / 2), o=[(0, 100), (4, 100, "in"), (14, 0)])
    return c


# ------------------------------------------------------------------ 9. bats
def bats():
    n, W, H = 180, 1920, 600
    c = K.Comp("hw26-bats", W, H, n)
    poses = [trim(sprite(f"bat_{i}")) for i in (1, 2, 3)]
    # register the three poses on the eyes (bright pink-red pixels) so the body doesn't jump
    eyes = []
    for im in poses:
        a = np.asarray(im).astype(int)
        m = (a[..., 0] > 180) & (a[..., 1] < 110) & (a[..., 2] > 60) & (a[..., 3] > 200)
        ys, xs = np.where(m)
        eyes.append((xs.mean(), ys.mean()) if len(xs) else (im.width / 2, im.height / 2))
    sub = K.sub_comp(n, 400, 300)
    sp = Painter(sub)
    target = 150  # display width of the spread-wing pose inside the precomp
    k = target / poses[1].width
    cycle = [(0, 0), (3, 1), (6, 2), (9, 1)]  # (frame offset, pose) within a 12-frame flap
    for pi, im in enumerate(poses):
        ref = f"bat{pi}"
        sp.asset(ref, im, 400)
        aw, ah = sp.assets[ref]
        f = aw / im.width
        ex, ey = eyes[pi]
        ops = []
        for start in range(0, n, 12):
            for off, pose in cycle:
                ops.append((start + off, 100 if pose == pi else 0, "hold"))
        ops.append((n, ops[0][1]))
        sp.put(ref, ref, im.width * k, p=(200, 150), anchor=(ex * f, ey * f), o=ops)
    c.d["assets"] += sub.d["assets"]
    c.add_precomp("bat", sub.d["layers"])
    L = W + 400
    rnd = random.Random(3)
    for i, (y, sc, ph) in enumerate([(110, 0.95, 0.0), (240, 0.6, 0.35), (70, 0.45, 0.62), (330, 0.75, 0.82)]):
        x0 = -200 + ph * L
        period = 60 if i % 2 else 90
        amp = rnd.uniform(14, 26)
        phase = rnd.random()
        times = list(range(0, n + 1, 6))
        for kk in (0, -1):
            xs = x0 + kk * L
            pos = [(t, [xs + L * t / n, y + amp * math.sin(2 * math.pi * (t / period + phase))], "linear") for t in times]
            c.precomp_layer(f"bat{i}_{kk}", "bat", 400, 300, st=-(i * 5) if kk == 0 else -(i * 5),
                            ks=K.transform(a=(200, 150), p=pos, s=(sc * 100, sc * 100),
                                           r=[(t, 5 * math.sin(4 * math.pi * t / n + i), "linear") for t in times]))
    return c


BUILDERS = {"door": ("hw26-door-open.json", door_open), "pulse": ("hw26-house-pulse.json", house_pulse),
            "g3": ("hw26-g3-walk.json", g3_walk), "pop": ("hw26-pop.json", pop), "brew": ("hw26-brew.json", brew),
            "rain": ("hw26-candy-rain.json", candy_rain), "drift": ("hw26-fog-drift.json", fog_drift),
            "lift": ("hw26-fog-lift.json", fog_lift), "bats": ("hw26-bats.json", bats)}

if __name__ == "__main__":
    for nm in sys.argv[1:] or list(BUILDERS):
        fn, build = BUILDERS[nm]
        size = build().save(os.path.join(OUT, fn))
        print(f"{fn:26s} {size / 1024:8.1f} KB", flush=True)
