#!/usr/bin/env python3
"""Door-opening Lotties with a full background, one per house (round 7 scenes).

  python tools/lottie_door_scenes.py [z1 z2 z3 z4]

Each scene exists twice: the approved scene (round7/house_scene) and a Nano Banana 2 edit with
the door in the other state (round7/house_scene_door). The approved scene is the background;
only a feathered patch around the door (where the two differ) is taken from each state, so
nothing else in the frame moves. The closed door rattles, a burst of light opens it (an iris
matte reveals the open-door patch), light rays, sparkles and Candy fly out, and the camera
pushes in slightly. One-shot, 1920x1080, 30 fps; the last frame holds the open state.
Output: halloween/final/halloween-2026/motion/scenes/hw26-door-scene-z{n}.json
"""
import math
import os
import random
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import lottie_kit as K  # noqa: E402
from lottie_painted import Painter, candy_img, halo_ring, soft_disc, sprite  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "halloween", "variants", "round7")
OUT = os.path.join(ROOT, "halloween", "final", "halloween-2026", "motion", "scenes")
W, H = 1920, 1080
GOLD = "#FFC861"

# roi: where the door and its light spill may differ, as fractions of the frame (x0, y0, x1, y1).
# door: door centre and door height in frame pixels. hinge: +1 / -1 for the rattle direction.
HOUSES = {
    "z1": dict(closed="scene", roi=(0.34, 0.46, 0.60, 0.88), door=(965, 632), dh=230, zone="#FFAA33"),
    "z2": dict(closed="scene", roi=(0.38, 0.42, 0.80, 1.00), door=(985, 700), dh=290, zone="#02DE82"),
    "z3": dict(closed="edit", roi=(0.47, 0.58, 0.62, 0.90), door=(1063, 752), dh=210, zone="#FF3B69"),
    "z4": dict(closed="edit", roi=(0.40, 0.43, 0.56, 1.00), door=(928, 590), dh=200, zone="#D4FF00"),
}


def frame(path):
    """Fit an image to the 1920x1080 frame (cover, centre crop)."""
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def door_mask(a, b, roi):
    """Feathered alpha (0..1) where a and b differ, limited to roi."""
    d = cv2.GaussianBlur(np.abs(np.asarray(a, np.float32) - np.asarray(b, np.float32)).mean(2), (0, 0), 3)
    m = np.clip((d - 6) / 18, 0, 1)
    box = np.zeros((H, W), np.float32)
    x0, y0, x1, y1 = (round(roi[0] * W), round(roi[1] * H), round(roi[2] * W), round(roi[3] * H))
    box[y0:y1, x0:x1] = 1
    box = cv2.GaussianBlur(box, (0, 0), 14)
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    m = cv2.GaussianBlur(m, (0, 0), 9) * box
    return np.clip(m * 1.4, 0, 1)


def patch(im, m):
    """RGBA crop of im with alpha m; returns (image, top-left)."""
    rgba = np.dstack([np.asarray(im), (m * 255).astype(np.uint8)])
    ys, xs = np.where(m > 0.01)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    return Image.fromarray(rgba[y0:y1, x0:x1], "RGBA"), (int(x0), int(y0))


def build(z):
    h = HOUSES[z]
    scene = frame(os.path.join(V, "house_scene", f"{z}.png"))
    edit = frame(os.path.join(V, "house_scene_door", f"{z}.png"))
    closed, opened = (scene, edit) if h["closed"] == "scene" else (edit, scene)
    m = door_mask(closed, opened, h["roi"])
    p_open, o_open = patch(opened, m)
    p_closed, o_closed = patch(closed, m)
    dx, dy = h["door"]
    k = h["dh"] / 220  # effects are tuned for a ~220 px tall door

    n = 96
    c = K.Comp(f"hw26-door-scene-{z}", W, H, n)
    P = Painter(c)
    rnd = random.Random(int(z[1]) * 7)
    c.marker(30, "door_open")
    P.assets["bg"] = c.add_image("bg", scene, jpeg=88)
    P.assets["open"] = c.add_image("open", p_open)
    P.assets["closed"] = c.add_image("closed", p_closed)
    P.asset("candy", candy_img(), 160)
    for i in (1, 2, 3, 4, 7):
        P.asset(f"spark{i}", sprite(f"sparkle_{i}"), 96)
    P.asset("burst", sprite("burst_1"), 512)

    # camera: a slow push-in centred on the door (scale >= 100 keeps the frame covered)
    cam = c.null("camera", ks=K.transform(a=(dx, dy), p=(dx, dy), s=[(0, [100, 100], "inout"), (n - 1, [105, 105])]))
    door = c.null("door", ks=K.transform(p=(dx, dy)), parent=cam)

    # top to bottom: effects, open patch (+ its iris matte), closed patch, background
    fade = [(0, 100), (62, 100, "in"), (74, 0)]
    for i in range(9):
        a = -math.pi / 2 + (i - 4) * 0.36
        dist = rnd.uniform(150, 260) * k
        t0 = 30 + i
        P.put(f"spark{i}", f"spark{(1, 2, 3, 4, 7)[i % 5]}", rnd.uniform(60, 96) * k,
              p=[(t0, [0, -20 * k], "out"), (t0 + 16, [math.cos(a) * dist, -20 * k + math.sin(a) * dist])],
              s=[(t0, [0, 0], "out"), (t0 + 5, [115, 115], "inout"), (t0 + 18, [0, 0])],
              r=[(t0, 0, "linear"), (t0 + 18, 80)], parent=door, ip=t0)
    order = list(range(12))
    rnd.shuffle(order)
    for i in range(12):
        # a wide fan: each piece arcs up out of the doorway and lands on the ground in front
        sx = (i - 5.5) * rnd.uniform(70, 92) * k
        peak, land = -rnd.uniform(140, 300) * k, h["dh"] * 0.5 + rnd.uniform(20, 120) * k
        t0 = 31 + order[i] // 2
        P.put(f"candy{i}", "candy", rnd.uniform(58, 76) * k,
              p=[(t0, [0, 10 * k], "out"), (t0 + 11, [sx * 0.55, peak], "in"), (t0 + 26, [sx, land])],
              s=[(t0, [15, 15], "back"), (t0 + 6, [100, 100])],
              r=[(t0, rnd.uniform(-30, 30), "linear"), (t0 + 26, rnd.uniform(-260, 260))], o=fade, parent=door, ip=t0)
    # zone-coloured ring and warm bloom from the doorway
    c.shape("ring", [K.group(halo_ring(320 * k, h["zone"], 0.95), nm="ring", s=[(30, [30, 30], "out"), (56, [260, 260])],
                             o=[(30, 100), (56, 0)])], parent=door, ip=30)
    P.put("rays", "burst", 380 * k, p=(0, -10 * k), parent=door, ip=27,
          s=[(27, [25, 25], "out"), (36, [100, 100], "inout"), (44, [92, 92], "in"), (70, [115, 115])],
          o=[(27, 0, "out"), (32, 100), (44, 95, "in"), (72, 0)])
    c.shape("flash", soft_disc(520 * k, GOLD, 0.9, 0.18), parent=door, ip=24,
            ks=K.transform(s=[(24, [20, 20], "out"), (34, [110, 110], "inout"), (60, [80, 80])],
                           o=[(24, 0, "out"), (31, 95), (44, 60, "in"), (66, 0)]))
    # lasting warm glow in the open doorway, breathing until the end
    c.shape("glow", soft_disc(300 * k, GOLD, 0.55, 0.1), parent=door, ip=34,
            ks=K.transform(p=(0, 10 * k), o=[(34, 0, "out"), (48, 70, "inout"), (64, 45, "inout"), (80, 62, "inout"), (n, 50)]))
    # iris matte: a soft disc growing from the door reveals the open-door patch
    c.shape("iris", soft_disc(220, "#ffffff", 1.0, 0.55), parent=door, ip=26, td=1,
            ks=K.transform(s=[(26, [0, 0], "out"), (40, [320 * k, 320 * k])]))
    c.image_layer("door_open", "open", ks=K.transform(p=(o_open[0] - dx, o_open[1] - dy)), parent=door, ip=26, tt=1)
    # closed door rattles (pivot at its base) just before it bursts open
    base = (dx - o_closed[0], dy + h["dh"] * 0.45 - o_closed[1])
    rat = [(0, 0), (10, 0, "inout")] + [(12 + 2 * j, (1.2 if j % 2 else -1.2) * (0.6 + 0.1 * j), "inout") for j in range(7)] + [(27, 0)]
    c.image_layer("door_closed", "closed", parent=door, op=40,
                  ks=K.transform(a=base, p=(o_closed[0] - dx + base[0], o_closed[1] - dy + base[1]), r=rat,
                                 o=[(0, 100), (32, 100, "in"), (38, 0)]))
    c.shape("leak", soft_disc(200 * k, GOLD, 0.5, 0.1), parent=door, op=34,
            ks=K.transform(o=[(0, 0), (8, 0, "inout"), (14, 45, "inout"), (18, 20, "inout"), (22, 60, "inout"), (26, 30), (33, 0)]))
    c.image_layer("background", "bg", parent=cam)
    return c


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for z in sys.argv[1:] or list(HOUSES):
        size = build(z).save(os.path.join(OUT, f"hw26-door-scene-{z}.json"))
        print(f"hw26-door-scene-{z}.json {size / 1024:8.1f} KB", flush=True)
