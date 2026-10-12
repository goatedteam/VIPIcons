#!/usr/bin/env python3
"""Build the Haunted Trail Lottie files (all except the G3 walk, see lottie_g3_walk.py).

  python tools/lottie_hw26.py [name ...]     names: door pulse pop brew rain drift lift bats

Spec: Bodymovin JSON, 30 fps, vector only, transparent, under 100 KB; layers that take
the zone colour are white and named "tint". Output: halloween/final/halloween-2026/motion/.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lottie_kit as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "halloween", "final", "halloween-2026", "motion")

INK = "#1a0f2e"
PURPLE, PURPLE_D, PURPLE_L = "#7b3fc4", "#4a2380", "#b48cf0"
LIME, LIME_D = "#d4ff00", "#8fb800"
WARM, WARM_D = "#ffe7ae", "#ffc861"


# ------------------------------------------------------------------ shared drawings
def candy(r=16):
    """Wrapped sweet centred on (0, 0): purple ball, lime twists, ink outline, shine."""
    t = r * 1.15
    twist_l = K.path([(-r * 0.6, 0), (-r - t, -r * 0.75), (-r - t * 0.75, 0), (-r - t, r * 0.75)])
    twist_r = K.path([(r * 0.6, 0), (r + t, -r * 0.75), (r + t * 0.75, 0), (r + t, r * 0.75)])
    return [
        K.group([K.ellipse([r * 0.7, r * 0.42], p=(-r * 0.32, -r * 0.42)), K.fill("#ffffff", o=70)], nm="shine"),
        K.group([K.ellipse([r * 1.5, r * 1.5], p=(r * 0.14, r * 0.14)), K.fill(PURPLE_D)], nm="shade"),
        K.group([K.ellipse([r * 2, r * 2]), K.fill(PURPLE), K.stroke(INK, max(1.5, r * 0.14))], nm="ball"),
        K.group([twist_l, twist_r, K.fill(LIME), K.stroke(INK, max(1.5, r * 0.12))], nm="twists"),
    ]


def sparkle(size, color="#ffffff"):
    return [K.group([K.star(4, size, size * 0.28, roundness=0), K.fill(color)], nm="spark")]


def soft_disc(d, color, alpha=1.0, core=0.0):
    """Circle with a radial alpha falloff (opaque out to `core`, then fading)."""
    return [K.group([K.ellipse([d, d]),
                     K.radial([(0, color, alpha), (max(core, 0.01), color, alpha), (1, color, 0)],
                              start=(0, 0), end=(d / 2, 0))], nm="disc")]


def loop_osc(frames, period, lo, hi, phase=0.0, n_per=8):
    """Sampled sine keyframes for a seamless loop (period must divide frames)."""
    kfs = []
    steps = int(frames / period * n_per)
    for i in range(steps + 1):
        t = frames * i / steps
        v = lo + (hi - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * (t / period + phase)))
        kfs.append((t, v, "linear"))
    return kfs


def vec_osc(frames, period, base, amp, phase=0.0, n_per=8):
    """[x, y] keyframes oscillating around base by amp=(ax, ay)."""
    out = []
    steps = int(frames / period * n_per)
    for i in range(steps + 1):
        t = frames * i / steps
        s = math.sin(2 * math.pi * (t / period + phase))
        out.append((t, [base[0] + amp[0] * s, base[1] + amp[1] * s], "linear"))
    return out


# ------------------------------------------------------------------ 1. door opens
# The door anchor defaults to the Zone 1 house; code patches the "door" layer position
# and the "door_size" layer scale per zone (values in hw26-motion-notes.md).
DOOR_W, DOOR_H = 36, 70


def door_open():
    n = 42
    c = K.Comp("hw26-door-open", 320, 320, n)
    rnd = random.Random(13)
    fade_out = [(0, 100), (34, 100, "in"), (41, 0)]
    door = c.null("door", ks=K.transform(p=(168, 204)))
    size = c.null("door_size", ks=K.transform(s=(100, 100)), parent=door)
    # sparkles (top)
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * 0.42
        dist = rnd.uniform(48, 80)
        t0 = 11 + i
        c.shape(f"spark{i}", sparkle(rnd.uniform(5, 8), LIME if i % 2 else "#ffffff"), parent=door,
                ks=K.transform(p=[(t0, [0, -10], "out"), (t0 + 12, [math.cos(a) * dist, -10 + math.sin(a) * dist])],
                               s=[(t0, [0, 0], "out"), (t0 + 4, [120, 120], "inout"), (t0 + 14, [0, 0])],
                               r=[(t0, 0, "linear"), (t0 + 14, 120)]))
    # candy burst
    for i in range(8):
        dx = (i - 3.5) * rnd.uniform(14, 19) + rnd.uniform(-6, 6)
        peak = -rnd.uniform(46, 78)
        land = rnd.uniform(52, 76)
        t0 = 10 + (i % 4) * 2 + (i // 4)
        c.shape(f"candy{i}", candy(rnd.uniform(6.5, 8.5)), parent=door,
                ks=K.transform(p=[(t0, [0, 8], "out"), (t0 + 9, [dx * 0.75, peak], "in"), (t0 + 20, [dx * 1.25, land])],
                               s=[(t0, [10, 10], "back"), (t0 + 5, [100, 100])],
                               r=[(t0, rnd.uniform(-30, 30), "linear"), (t0 + 20, rnd.uniform(-260, 260))],
                               o=fade_out))
    # light filling the doorway as the door swings open (scales out from the hinge)
    hw, hh = DOOR_W / 2, DOOR_H / 2
    arch = K.path([(-hw, hh), (-hw, -hh + hw), (-hw * 0.71, -hh + hw * 0.29), (0, -hh), (hw * 0.71, -hh + hw * 0.29),
                   (hw, -hh + hw), (hw, hh)])
    c.shape("door_light", [K.group([arch, K.fill(WARM)], nm="opening", a=(-hw, 0), p=(-hw, 0),
                                   s=[(2, [0, 100], "out"), (12, [100, 100])])],
            ks=K.transform(o=fade_out), parent=size)
    c.shape("door_spill", [K.group([K.path([(-hw, hh), (hw, hh), (hw * 2.6, hh + 34), (-hw * 2.6, hh + 34)]),
                                    K.radial([(0, WARM_D, 0.8), (1, WARM_D, 0)], start=(0, hh), end=(0, hh + 40))])],
            ks=K.transform(o=[(4, 0, "out"), (14, 100), (34, 100, "in"), (41, 0)]), parent=size)
    # zone-coloured bloom behind everything
    c.shape("tint", [K.group(soft_disc(200, "#ffffff", 0.85, 0.15), nm="bloom",
                             s=[(2, [20, 20], "out"), (16, [100, 100])]),
                     K.group([K.ellipse([120, 120]), K.stroke("#ffffff", 5)], nm="ring",
                             s=[(8, [30, 30], "out"), (26, [170, 170])], o=[(8, 90), (26, 0)])],
            ks=K.transform(o=[(2, 0, "out"), (10, 90), (30, 80, "in"), (41, 0)]), parent=door)
    return c


# ------------------------------------------------------------------ 2. house pulse
def house_pulse():
    n = 48
    c = K.Comp("hw26-house-pulse", 400, 400, n)
    glow = K.group(soft_disc(330, "#ffffff", 0.75, 0.2), nm="glow",
                   s=[(t, [v, v], e) for t, v, e in loop_osc(n, n, 90, 106, phase=-0.25)],
                   o=[(t, v, e) for t, v, e in loop_osc(n, n, 62, 100, phase=-0.25)])
    ring = K.group([K.ellipse([200, 200]), K.stroke("#ffffff", 5)], nm="ring",
                   s=[(0, [70, 70], "out"), (n, [175, 175])],
                   o=[(0, 0, "out"), (8, 70, "in"), (n, 0)])
    c.shape("tint", [ring, glow], ks=K.transform(p=(200, 200)))
    return c


# ------------------------------------------------------------------ 3. candy pop
def pop():
    n = 14  # 0.47 s at 30 fps (spec 0.45 s)
    c = K.Comp("hw26-pop", 192, 192, n)
    # reference curve for the candy icon's own scale (applied by code): 1 -> 1.45 -> 0.92 -> 1
    c.null("icon_scale_ref", ks=K.transform(p=(96, 96), s=[(0, [100, 100], "out"), (4, [145, 145], "inout"),
                                                           (9, [92, 92], "inout"), (13, [100, 100])]))
    rnd = random.Random(5)
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        dist = rnd.uniform(62, 80)
        c.shape(f"star{i}", sparkle(rnd.uniform(6, 9), LIME if i % 2 else "#ffffff"),
                ks=K.transform(p=[(0, [96 + math.cos(a) * 20, 96 + math.sin(a) * 20], "out"),
                                  (12, [96 + math.cos(a) * dist, 96 + math.sin(a) * dist])],
                               s=[(0, [0, 0], "out"), (4, [110, 110], "in"), (13, [0, 0])],
                               r=[(0, 0, "linear"), (13, 90)]))
    rays = []
    for i in range(12):
        a = math.degrees(i * math.pi / 6)
        rays.append(K.group([K.rect([5, 26], p=(0, -46), r=2.5), K.fill(PURPLE_L if i % 2 else "#ffffff")],
                            nm=f"ray{i}", r=a, s=[(0, [100, 0], "out"), (5, [100, 100], "in"), (11, [100, 0])],
                            p=[(0, [0, 0], "out"), (11, [0, 0])]))
    c.shape("rays", rays, ks=K.transform(p=(96, 96), s=[(0, [60, 60], "out"), (11, [125, 125])],
                                         o=[(0, 100), (8, 100, "in"), (12, 0)]))
    c.shape("flash", [K.group(soft_disc(150, "#ffffff", 0.9, 0.1), nm="flash")],
            ks=K.transform(p=(96, 96), s=[(0, [30, 30], "out"), (6, [110, 110])], o=[(0, 90, "in"), (10, 0)]))
    c.shape("glow", [K.group(soft_disc(176, LIME, 0.45, 0.0), nm="glow")],
            ks=K.transform(p=(96, 96), s=[(0, [40, 40], "out"), (8, [100, 100])], o=[(0, 0, "out"), (3, 100), (13, 0)]))
    return c


# ------------------------------------------------------------------ 4. cauldron brew
def _cauldron_body(cx, cy, rx, ry):
    """Front of the pot: lower half of the rim ellipse, then the belly."""
    pts = []
    for i in range(0, 19):  # rim lower arc, left -> right
        a = math.pi - math.pi * i / 18
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    belly_w, belly_h = rx * 1.22, rx * 1.05
    for i in range(1, 24):  # belly, right -> left through the bottom
        a = -math.pi * 0.08 + (math.pi * 1.16) * i / 24
        pts.append((cx + belly_w * math.cos(a), cy + 18 + belly_h * 0.78 * math.sin(a)))
    return pts


def brew():
    n = 45
    c = K.Comp("hw26-brew", 400, 400, n)
    rnd = random.Random(21)
    cx, rim_y, rx, ry = 200, 212, 112, 26
    # sparkles around the risen item
    for i in range(6):
        a = i * math.pi / 3 + 0.4
        t0 = 22 + i
        c.shape(f"spark{i}", sparkle(rnd.uniform(6, 9), LIME if i % 2 else "#ffffff"),
                ks=K.transform(p=[(t0, [cx + math.cos(a) * 40, 120 + math.sin(a) * 40], "out"),
                                  (t0 + 14, [cx + math.cos(a) * 95, 120 + math.sin(a) * 85])],
                               s=[(t0, [0, 0], "out"), (t0 + 5, [110, 110], "in"), (t0 + 15, [0, 0])],
                               r=[(t0, 0, "linear"), (t0 + 15, 140)]))
    # green smoke puff
    for i in range(8):
        a = -math.pi / 2 + (i - 3.5) * 0.38
        d = rnd.uniform(70, 120)
        size = rnd.uniform(90, 140)
        t0 = 11 + i % 3
        c.shape(f"smoke{i}", soft_disc(size, rnd.choice(["#7dffb0", "#a6ffcb", "#4be38c"]), 0.85, 0.35),
                ks=K.transform(p=[(t0, [cx + (i - 3.5) * 10, rim_y - 6], "out"),
                                  (t0 + 22, [cx + math.cos(a) * d, rim_y - 30 + math.sin(a) * d])],
                               s=[(t0, [25, 25], "out"), (t0 + 22, [125, 125])],
                               o=[(t0, 0, "out"), (t0 + 4, 85), (t0 + 12, 70, "in"), (t0 + 24, 0)]))
    # splash drops
    for i in range(6):
        dx = (i - 2.5) * 26
        t0 = 9 + i % 2
        c.shape(f"drop{i}", [K.group([K.ellipse([11, 14]), K.fill("#3dff8a"), K.stroke("#0a5a33", 2)], nm="drop")],
                ks=K.transform(p=[(t0, [cx + dx * 0.4, rim_y - 4], "out"), (t0 + 7, [cx + dx, rim_y - 70], "in"),
                                  (t0 + 15, [cx + dx * 1.35, rim_y + 8])],
                               s=[(t0, [40, 40]), (t0 + 6, [100, 100]), (t0 + 15, [60, 60])],
                               o=[(t0, 100), (t0 + 13, 100, "in"), (t0 + 15, 0)]))
    # rim, front lip (over the item)
    front = [(cx + (rx + 10) * math.cos(a), rim_y + (ry + 6) * math.sin(a)) for a in [i * math.pi / 16 for i in range(17)]]
    front += [(cx + (rx - 4) * math.cos(a), rim_y + (ry - 4) * math.sin(a)) for a in [math.pi - i * math.pi / 16 for i in range(17)]]
    c.shape("rim_front", [K.group([K.path(front), K.fill("#4a4359"), K.stroke(INK, 3)], nm="lip")])
    body = _cauldron_body(cx, rim_y, rx + 6, ry)
    bottom = max(y for _, y in body)
    feet = [K.group([K.rect([30, 30], p=(cx + dx, bottom - 6), r=8), K.fill("#2a2434"), K.stroke(INK, 3)], nm=f"foot{dx}")
            for dx in (-78, 0, 78)]
    # soft highlight inside the belly, and a green under-glow on the iron
    c.shape("pot", [K.group([K.ellipse([46, 84]), K.fill("#6b6284", o=40)], nm="sheen", p=(cx - 78, rim_y + 74), r=24),
                    K.group([K.ellipse([2 * rx, 70], p=(cx, rim_y + 30)),
                             K.radial([(0, "#3dff8a", 0.28), (1, "#3dff8a", 0)], start=(0, 0), end=(rx, 0))],
                            nm="glow_on_iron", p=(0, 0)),
                    K.group([K.path(body), K.fill("#3a3349"), K.stroke(INK, 4)], nm="belly")] + feet,
            ks=K.transform(p=[(0, [0, 0], "out"), (5, [0, 3], "inout"), (9, [0, -4], "out"), (14, [0, 0])]))
    # the bought item: code swaps this image asset (item.png, 192x192) for the item PNG
    c.add_image_asset("item", 192, 192, "item.png")
    c.image_layer("item", "item", ks=K.transform(
        a=(96, 96),
        p=[(0, [cx, rim_y + 90]), (14, [cx, rim_y + 90], "back"), (28, [cx, 118], "sine"), (37, [cx, 126], "sine"),
           (45, [cx, 120])],
        s=[(14, [55, 55], "back"), (28, [100, 100])],
        o=[(0, 0), (13, 0), (14, 100)]))
    # liquid surface + bubbles
    bubbles = []
    for i in range(9):
        bx = cx + rnd.uniform(-rx * 0.75, rx * 0.75)
        by = rim_y + rnd.uniform(-ry * 0.45, ry * 0.45)
        t0 = rnd.choice([0, 2, 4, 6, 8, 18, 24, 30, 36])
        d = rnd.uniform(10, 20)
        bubbles.append(K.group([K.ellipse([d, d * 0.8]), K.fill("#7dffb0"), K.stroke("#0a7a45", 2)], nm=f"b{i}", p=(bx, by),
                               s=[(t0, [0, 0], "out"), (t0 + 5, [100, 100], "in"), (t0 + 8, [130, 0])]))
    surface = [K.group([K.ellipse([2 * rx - 14, 2 * ry - 10], p=(cx - 8, rim_y - 3)), K.fill("#3dff8a", o=80)], nm="hi"),
               K.group([K.ellipse([2 * rx - 4, 2 * ry - 4], p=(cx, rim_y)), K.fill("#12b862")], nm="liquid")]
    c.shape("brew", bubbles + surface,
            ks=K.transform(a=(cx, rim_y), p=(cx, rim_y), s=[(0, [100, 100], "out"), (6, [100, 125], "inout"),
                                                           (10, [104, 90], "inout"), (16, [100, 100])]))
    c.shape("rim_back", [K.group([K.ellipse([2 * rx + 20, 2 * ry + 12], p=(cx, rim_y)), K.fill("#4a4359"),
                                  K.stroke(INK, 3)], nm="rim")])
    c.shape("glow", soft_disc(300, "#3dff8a", 0.55, 0.05),
            ks=K.transform(p=(cx, rim_y - 20), s=[(0, [70, 70], "out"), (12, [115, 115], "inout"), (45, [95, 95])],
                           o=[(0, 50), (12, 100, "inout"), (45, 70)]))
    c.shape("shadow", [K.group([K.ellipse([250, 34]), K.radial([(0, "#000000", 0.45), (1, "#000000", 0)],
                                                                end=(125, 0))], nm="shadow")],
            ks=K.transform(p=(cx, max(y for _, y in body) + 14)))
    return c


# ------------------------------------------------------------------ 5. candy rain
def candy_rain():
    n = 90
    W = 1080
    c = K.Comp("hw26-candy-rain", W, W, n)
    sub = K.sub_comp(n, 120, 120)
    sub.shape("candy", candy(26), ks=K.transform(p=(60, 60)))
    c.add_precomp("candy", sub.d["layers"])
    rnd = random.Random(40)
    for i in range(40):
        dur = rnd.randint(44, 62)
        t0 = rnd.randint(0, n - dur - 1)
        x0 = rnd.uniform(40, W - 40)
        drift = rnd.uniform(-90, 90)
        sc = rnd.uniform(55, 115)
        rot0 = rnd.uniform(0, 360)
        spin = rnd.choice([-1, 1]) * rnd.uniform(180, 540)
        c.precomp_layer(f"candy{i}", "candy", 120, 120, ip=t0, op=t0 + dur + 1, ks=K.transform(
            a=(60, 60), s=(sc, sc),
            p=[(t0, [x0, -90], "in"), (t0 + dur, [x0 + drift, W + 90])],
            r=[(t0, rot0, "linear"), (t0 + dur, rot0 + spin)]))
    for i in range(14):
        t0 = rnd.randint(0, n - 30)
        x = rnd.uniform(40, W - 40)
        c.shape(f"sparkle{i}", sparkle(rnd.uniform(7, 12), LIME if i % 2 else "#ffffff"), ip=t0, op=t0 + 29,
                ks=K.transform(p=[(t0, [x, rnd.uniform(60, 500)], "linear"), (t0 + 28, [x, rnd.uniform(560, 1000)])],
                               s=[(t0, [0, 0], "out"), (t0 + 6, [100, 100], "inout"), (t0 + 14, [40, 40], "inout"),
                                  (t0 + 22, [100, 100], "in"), (t0 + 28, [0, 0])],
                               r=[(t0, 0, "linear"), (t0 + 28, 180)]))
    return c


# ------------------------------------------------------------------ 6. fog drift (tileable loop)
def fog_drift():
    n = 240
    W = 1200
    c = K.Comp("hw26-fog-drift", W, W, n)
    rnd = random.Random(7)
    P = 600  # horizontal period: the pattern repeats every 600 px, so it tiles at 1200
    for i in range(10):
        w, h = rnd.uniform(420, 640), rnd.uniform(100, 190)
        y = rnd.uniform(h / 2 + 40, W - h / 2 - 40)
        x = rnd.uniform(0, P)
        direction = 1 if i % 3 else -1
        alpha = rnd.uniform(0.32, 0.5)
        col = rnd.choice(["#f1edff", "#e2dbfa", "#d2caee"])
        bob = vec_osc(n, n / 2 if i % 2 else n, (0, 0), (0, rnd.uniform(8, 18)), phase=rnd.random())
        # radial gradients are circular, so the wisp is drawn round and squashed by the group scale
        wisp = [K.group([K.ellipse([w, w]), K.radial([(0, col, alpha), (0.35, col, alpha * 0.8), (1, col, 0)],
                                                     end=(w / 2, 0))], nm="wisp", s=(100, h / w * 100), p=bob)]
        for k in (-1, 0, 1, 2):  # copies one period apart so the canvas is always covered
            x0 = x + k * P
            c.shape(f"wisp{i}_{k}", wisp, ks=K.transform(p=[(0, [x0, y], "linear"), (n, [x0 + direction * P, y])]))
    return c


# ------------------------------------------------------------------ 7. fog lift
def fog_lift():
    n = 54
    W = 1200
    c = K.Comp("hw26-fog-lift", W, W, n)
    rnd = random.Random(11)
    ctr = (W / 2, W / 2)
    puffs = []
    step = 210
    for gy in range(-1, 7):
        for gx in range(-1, 7):
            x = gx * step + step / 2 + rnd.uniform(-60, 60)
            y = gy * step + step / 2 + rnd.uniform(-60, 60)
            puffs.append((x, y))
    puffs.sort(key=lambda p: -math.dist(p, ctr))  # far ones drawn first (lowest)... listed top-first below
    for i, (x, y) in enumerate(reversed(puffs)):
        d = math.dist((x, y), ctr)
        ang = math.atan2(y - ctr[1], x - ctr[0]) if d > 1 else rnd.uniform(0, 2 * math.pi)
        t0 = 3 + d / 850 * 14  # centre parts first
        travel = 520 + rnd.uniform(0, 160)
        size = rnd.uniform(380, 470)
        col = rnd.choice(["#4a4466", "#554e74", "#625a84", "#6e6690"])
        c.shape(f"puff{i}", soft_disc(size, col, 1.0, 0.5), ks=K.transform(
            p=[(0, [x, y]), (t0, [x, y], "in"), (n, [x + math.cos(ang) * travel, y + math.sin(ang) * travel])],
            s=[(t0, [100, 100], "in"), (n, [140, 140])],
            o=[(t0 + 10, 100, "in"), (n - 2, 0)]))
    c.shape("base", [K.group([K.rect([W, W], p=(W / 2, W / 2)), K.fill("#4a4466")], nm="base")],
            ks=K.transform(o=[(0, 100), (4, 100, "in"), (16, 0)]))
    return c


# ------------------------------------------------------------------ 8. bats
def bat_drawing(flap_frames, n):
    wing = K.path([(0, -4), (-22, -26), (-46, -30), (-70, -18), (-86, 2), (-72, 0), (-64, 10), (-52, 4), (-42, 16),
                   (-30, 8), (-14, 12), (0, 8)])
    flap = []
    t = 0
    up = True
    while t <= n:
        flap.append((t, [100, 100] if up else [100, -55], "sine"))
        up = not up
        t += flap_frames / 2
    rot = [(tt, 8 if v[1] > 0 else -14, "sine") for tt, v, _ in flap]
    left = K.group([wing, K.fill("#1b1426"), K.stroke("#4a3a66", 2)], nm="wing_l", a=(0, 0), p=(-6, 0), s=flap, r=rot)
    right = K.group([wing, K.fill("#1b1426"), K.stroke("#4a3a66", 2)], nm="wing_r", a=(0, 0), p=(6, 0),
                    s=[(tt, [-100, v[1]], e) for tt, v, e in flap], r=[(tt, -v, e) for tt, v, e in rot])
    body = K.group([K.ellipse([20, 30], p=(0, 6)), K.fill("#15101e"), K.stroke("#4a3a66", 2)], nm="body")
    head = K.group([K.path([(-9, -6), (-8, -19), (-3, -11), (3, -11), (8, -19), (9, -6), (0, 2)]),
                    K.fill("#15101e"), K.stroke("#4a3a66", 2)], nm="head")
    eyes = K.group([K.ellipse([3, 3], p=(-3.5, -7)), K.ellipse([3, 3], p=(3.5, -7)), K.fill("#ff3b69")], nm="eyes")
    return [eyes, head, body, left, right]


def bats():
    n = 180
    W, H = 1920, 600
    c = K.Comp("hw26-bats", W, H, n)
    sub = K.sub_comp(n, 200, 120)
    sub.shape("bat", bat_drawing(12, n), ks=K.transform(p=(100, 60)))
    c.add_precomp("bat", sub.d["layers"])
    L = W + 300
    rnd = random.Random(3)
    specs = [(110, 0.95, 0.0), (230, 0.62, 0.35), (70, 0.48, 0.62), (330, 0.75, 0.82)]
    for i, (y, sc, ph) in enumerate(specs):
        x0 = -150 + ph * L
        bob = vec_osc(n, 60 if i % 2 else 90, (0, y), (0, rnd.uniform(14, 26)), phase=rnd.random(), n_per=6)
        for k in (0, -1):
            xs = x0 + k * L
            pos = [(t, [xs + L * t / n, v[1]], "linear") for t, v, _ in bob]
            c.precomp_layer(f"bat{i}_{k}", "bat", 200, 120, st=-rnd.randint(0, 11) if k == 0 else 0,
                            ks=K.transform(a=(100, 60), p=pos, s=(sc * 100, sc * 100),
                                           r=[(t, 4 * math.sin(4 * math.pi * t / n), "linear") for t, _, _ in bob]))
    return c


BUILDERS = {"door": ("hw26-door-open.json", door_open), "pulse": ("hw26-house-pulse.json", house_pulse),
            "pop": ("hw26-pop.json", pop), "brew": ("hw26-brew.json", brew),
            "rain": ("hw26-candy-rain.json", candy_rain), "drift": ("hw26-fog-drift.json", fog_drift),
            "lift": ("hw26-fog-lift.json", fog_lift), "bats": ("hw26-bats.json", bats)}

if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDERS)
    for nm in names:
        fn, build = BUILDERS[nm]
        size = build().save(os.path.join(OUT, fn))
        print(f"{fn:26s} {size / 1024:6.1f} KB")
