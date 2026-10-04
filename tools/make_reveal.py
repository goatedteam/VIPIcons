#!/usr/bin/env python3
"""Mystery Chest reveal: 10 s motion-graphics video with synthesized sound, rendered with NumPy/PIL + ffmpeg.

  python tools/make_reveal.py [--fps 30] [--preview]

Inputs (video/assets/): the clean poster painting (poster/raw/lightning_2.png), the open-chest
frame painted from it (chest_open.png) and the keyed juice box (juicebox.png).
Output: video/mystery_chest_reveal.mp4 (1080x1350, 4:5) and its audio as video/reveal_audio.wav.

Everything is driven by one timeline (TIMELINE below) so picture and sound stay in sync:
build-up with accelerating push-in and lightning strikes, the chest rattling harder and harder,
a giant strike that blows the lid open, then the glowing juice box rising out as the hero shot.
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "video", "assets")
OUT_DIR = os.path.join(ROOT, "video")

W, H = 1080, 1350
DUR = 10.0
SR = 48000

LIME = np.array([212, 255, 0], np.float32) / 255
LIME_HOT = np.array([235, 255, 170], np.float32) / 255
ORANGE = np.array([255, 105, 0], np.float32) / 255
ORANGE_HOT = np.array([255, 205, 120], np.float32) / 255

# ---------------------------------------------------------------- timeline
T_OPEN = 5.5            # giant strike, lid bursts open
T_RISE = (5.62, 7.3)    # juice box rises out of the chest
T_LAND = 7.3            # juice box settles: shockwave + chime
T_DING = 9.15           # final sparkle ding
STRIKES = [(0.55, 0.55), (1.45, 0.65), (2.3, 0.7), (3.0, 0.75), (3.55, 0.8),
           (4.0, 0.85), (4.4, 0.9), (4.75, 0.95), (5.08, 1.0), (T_OPEN, 1.6)]
POST_STRIKES = [(6.3, 0.5), (7.9, 0.45), (8.8, 0.4), (9.55, 0.35)]


def _knocks():
    """Chest rattle knocks between 2.9 s and the burst, getting faster."""
    t, dt, out = 2.9, 0.32, []
    rng = np.random.default_rng(7)
    while t < T_OPEN - 0.06:
        out.append((t, min(1.0, 0.35 + (t - 2.9) / 2.6)))
        t += dt * rng.uniform(0.8, 1.2)
        dt = max(0.055, dt * 0.88)
    return out


KNOCKS = _knocks()

# source-space geometry (poster is 1856x2304)
SRC_W, SRC_H = 1856, 2304
VIEW_W1 = SRC_H * W / H                    # source width visible at zoom 1
CHEST_BOX = (400, 800, 1460, 1660)         # rattle region of the closed chest
SEAM = (470, 1205, 1400, 1300)             # glowing seam of the closed chest
OPENING = (925, 1160)                      # centre of the open chest's mouth
RIM_Y = 1192                               # front rim: the juice box is hidden below this
JB_H = 560                                 # juice box height in source px when settled
JB_START, JB_END = (925, 1500), (925, 760)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 2.6


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_out_back(x, k=1.9):
    x = min(max(x, 0.0), 1.0)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def pulse(t, t0, attack, decay):
    if t < t0 - attack:
        return 0.0
    if t < t0:
        return (t - (t0 - attack)) / attack if attack > 0 else 1.0
    return math.exp(-(t - t0) / decay)


# ---------------------------------------------------------------- camera
def camera(t):
    """Returns (cx, cy, zoom, rot) in source space, including shake."""
    if t < T_OPEN:
        p = ease_in(t / T_OPEN)
        z = 1.0 + 0.62 * p
        cx, cy = 928, 1152 + 90 * p
    else:
        p = ease_out((t - T_OPEN) / (DUR - T_OPEN))
        z = 1.5 + 0.38 * p
        z += 0.12 * (1 - ease_out((t - T_OPEN) / 0.25))     # punch-in on the burst
        jb = juicebox_state(t)
        box_y = JB_START[1] if jb is None else min(jb[1], JB_START[1])
        follow = smooth((t - T_RISE[0]) / 0.9)
        cx, cy = 928, 1242 + follow * ((box_y + 1250) / 2 - 1242) * 0.9
    # shake: strikes + rattle + burst
    amp = 0.0
    for ts, s in STRIKES + POST_STRIKES:
        amp += 14 * s * pulse(t, ts, 0.0, 0.18)
    for tk, s in KNOCKS:
        amp += 5 * s * pulse(t, tk, 0.0, 0.06)
    amp += 34 * pulse(t, T_OPEN, 0.0, 0.35)
    amp += 10 * pulse(t, T_LAND, 0.0, 0.2)
    n1 = math.sin(t * 91.3) + 0.6 * math.sin(t * 57.1 + 1.3) + 0.4 * math.sin(t * 131.7 + 0.4)
    n2 = math.sin(t * 83.9 + 2.1) + 0.6 * math.sin(t * 61.7 + 0.2) + 0.4 * math.sin(t * 143.1 + 1.1)
    cx += amp * n1 / 2
    cy += amp * n2 / 2
    rot = amp * 0.0009 * math.sin(t * 47.3)
    return cx, cy, z, rot


class Cam:
    def __init__(self, t):
        self.cx, self.cy, self.z, self.rot = camera(t)
        self.s = (VIEW_W1 / self.z) / W           # source px per output px
        self.c, self.sn = math.cos(self.rot), math.sin(self.rot)

    def affine(self):
        s, c, sn = self.s, self.c, self.sn
        a, b = s * c, -s * sn
        d, e = s * sn, s * c
        return (a, b, self.cx - a * W / 2 - b * H / 2, d, e, self.cy - d * W / 2 - e * H / 2)

    def view(self, img, resample=Image.BICUBIC):
        return img.transform((W, H), Image.AFFINE, self.affine(), resample=resample)

    def to_out(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        return (W / 2 + (self.c * dx + self.sn * dy) / self.s,
                H / 2 + (-self.sn * dx + self.c * dy) / self.s)


# ---------------------------------------------------------------- procedural lightning
def bolt_path(p0, p1, rng, rough=0.22, depth=6):
    pts = [np.array(p0, float), np.array(p1, float)]
    for _ in range(depth):
        new = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2
            d = b - a
            n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-6)
            m = m + n * rng.normal(0, rough) * np.hypot(*d)
            new += [m, b]
        pts = new
    return pts


def make_strike(seed, strength, origin):
    """A strike: 2-4 main bolts from behind the chest to the frame edges, with branches."""
    rng = np.random.default_rng(seed)
    bolts = []
    for _ in range(int(2 + 2 * strength)):
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05) if rng.random() < 0.75 else rng.uniform(-0.2, 0.25) + (0 if rng.random() < 0.5 else math.pi)
        L = rng.uniform(1300, 1900)
        p1 = (origin[0] + L * math.cos(ang), origin[1] + L * math.sin(ang))
        main = bolt_path(origin, p1, rng)
        bolts.append((main, 1.0))
        for _ in range(rng.integers(2, 5)):
            i = rng.integers(len(main) // 6, len(main) * 3 // 4)
            q0 = main[i]
            bang = ang + rng.choice([-1, 1]) * rng.uniform(0.35, 0.9)
            bl = rng.uniform(180, 520)
            bolts.append((bolt_path(q0, (q0[0] + bl * math.cos(bang), q0[1] + bl * math.sin(bang)), rng, depth=5), 0.5))
    return bolts


STRIKE_BOLTS = {i: make_strike(100 + i, s, (928, 1100) if ts <= T_OPEN else OPENING)
                for i, (ts, s) in enumerate(STRIKES + POST_STRIKES)}


def strike_level(t, ts):
    """Flickering envelope of a strike: a bright hit and two re-strikes."""
    dt = t - ts
    if dt < -0.03 or dt > 0.42:
        return 0.0
    if dt < 0:
        return 0.4
    return max(math.exp(-dt / 0.05), 0.75 * math.exp(-abs(dt - 0.11) / 0.035), 0.5 * math.exp(-abs(dt - 0.22) / 0.04))


def draw_bolts(cam, t):
    """Returns (outline, glow, core) float masks in output space for all active strikes."""
    glow = Image.new("L", (W, H))
    core = Image.new("L", (W, H))
    ink = Image.new("L", (W, H))
    dg, dc, di = ImageDraw.Draw(glow), ImageDraw.Draw(core), ImageDraw.Draw(ink)
    any_on = False
    for i, (ts, s) in enumerate(STRIKES + POST_STRIKES):
        lv = strike_level(t, ts) * min(1.0, s)
        if lv <= 0.02:
            continue
        any_on = True
        for path, wgt in STRIKE_BOLTS[i]:
            pts = [cam.to_out(*p) for p in path]
            w = max(1, int(round((5.5 * wgt + 1) * cam.z * 0.75)))
            v = int(255 * lv)
            di.line(pts, fill=int(200 * lv), width=w + 5, joint="curve")
            dg.line(pts, fill=v, width=w * 4, joint="curve")
            dc.line(pts, fill=v, width=w, joint="curve")
    if not any_on:
        return None
    f = lambda im, r: np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
    return f(ink, 1.2), f(glow, 14), f(core, 0.8)


# ---------------------------------------------------------------- particles
class Particles:
    def __init__(self, n, seed, spawn, life, color, size):
        rng = np.random.default_rng(seed)
        self.t0 = rng.uniform(*spawn, n)
        self.life = rng.uniform(*life, n)
        self.x0, self.y0, self.vx, self.vy = [np.zeros(n) for _ in range(4)]
        self.color, self.size, self.rng = color, size, rng
        self.ph = rng.uniform(0, 6.28, n)

    def draw(self, cam, t, d, gain=1.0):
        on = (t >= self.t0) & (t < self.t0 + self.life)
        for i in np.nonzero(on)[0]:
            a = (t - self.t0[i]) / self.life[i]
            x = self.x0[i] + self.vx[i] * (t - self.t0[i]) + 18 * math.sin(self.ph[i] + 6 * t)
            y = self.y0[i] + self.vy[i] * (t - self.t0[i])
            u, v = cam.to_out(x, y)
            if not (-20 < u < W + 20 and -20 < v < H + 20):
                continue
            fade = math.sin(math.pi * a) * gain * (0.6 + 0.4 * math.sin(self.ph[i] * 3 + 25 * t))
            r = self.size * cam.z * 0.55 * (1 - 0.5 * a)
            col = tuple(int(255 * c * fade) for c in self.color)
            d.ellipse((u - r, v - r, u + r, v + r), fill=col)


def sparks_lime():
    p = Particles(420, 1, (0.0, T_OPEN + 0.4), (0.5, 1.4), LIME_HOT, 4.0)
    r = p.rng
    ang = r.uniform(0, 2 * math.pi, len(p.t0))
    rad = r.uniform(380, 640, len(p.t0))
    p.x0 = 928 + rad * np.cos(ang)
    p.y0 = 1240 + 0.75 * rad * np.sin(ang)
    sp = r.uniform(60, 260, len(p.t0))
    p.vx = sp * np.cos(ang) * 0.7
    p.vy = sp * np.sin(ang) * 0.5 - 120
    return p


def embers_orange():
    p = Particles(300, 2, (T_OPEN, DUR), (0.9, 2.2), ORANGE_HOT, 4.6)
    r = p.rng
    p.x0 = OPENING[0] + r.normal(0, 210, len(p.t0))
    p.y0 = OPENING[1] + r.uniform(-30, 40, len(p.t0))
    p.vx = r.normal(0, 140, len(p.t0))
    p.vy = -r.uniform(250, 700, len(p.t0))
    return p


def burst_lime():
    p = Particles(260, 3, (T_OPEN, T_OPEN + 0.12), (0.6, 1.3), LIME_HOT, 5.0)
    r = p.rng
    ang = r.uniform(0, 2 * math.pi, len(p.t0))
    sp = r.uniform(500, 1500, len(p.t0))
    p.x0 = OPENING[0] + 0 * ang
    p.y0 = OPENING[1] + 0 * ang
    p.vx, p.vy = sp * np.cos(ang), sp * np.sin(ang) - 200
    return p


PARTS = None


# ---------------------------------------------------------------- assets
def lightning_mask(img):
    a = np.asarray(img.convert("RGB"), np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = ((g > 200) & (g - b > 45) & (r > 120)) | ((r > 238) & (g > 240) & (b > 205))
    mm = Image.fromarray((m * 255).astype(np.uint8))
    # keep it to the sky/bolts, not the chest seam or steel
    return mm.filter(ImageFilter.GaussianBlur(3))


def soft_ellipse(box, blur, size=(SRC_W, SRC_H)):
    im = Image.new("L", size)
    ImageDraw.Draw(im).ellipse(box, fill=255)
    return im.filter(ImageFilter.GaussianBlur(blur))


A = {}


def load_assets():
    closed = Image.open(os.path.join(ROOT, "poster", "raw", "lightning_2.png")).convert("RGB")
    opened = Image.open(os.path.join(ASSETS, "chest_open.png")).convert("RGB").resize(closed.size, Image.LANCZOS)
    A["closed"], A["open"] = closed, opened
    A["lm_closed"], A["lm_open"] = lightning_mask(closed), lightning_mask(opened)
    x0, y0, x1, y1 = SEAM
    A["seam"] = soft_ellipse((x0, y0, x1, y1), 28)
    A["open_glow"] = soft_ellipse((OPENING[0] - 520, OPENING[1] - 380, OPENING[0] + 520, OPENING[1] + 160), 120)
    cb = CHEST_BOX
    A["chest_crop"] = closed.crop(cb)
    A["chest_mask"] = Image.new("L", (cb[2] - cb[0], cb[3] - cb[1]))
    ImageDraw.Draw(A["chest_mask"]).rounded_rectangle((40, 40, cb[2] - cb[0] - 40, cb[3] - cb[1] - 40), 60, fill=255)
    A["chest_mask"] = A["chest_mask"].filter(ImageFilter.GaussianBlur(22))
    jb = Image.open(os.path.join(ASSETS, "juicebox.png")).convert("RGBA")
    A["jb"] = jb
    A["jb_glow"] = jb.getchannel("A").filter(ImageFilter.GaussianBlur(22))
    yy, xx = np.mgrid[0:H, 0:W]
    rr = np.hypot((xx - W / 2) / (W * 0.62), (yy - H / 2) / (H * 0.62))
    A["vignette"] = np.clip(1.05 - 0.55 * rr ** 2.2, 0.35, 1.0)[..., None].astype(np.float32)
    global PARTS
    PARTS = [sparks_lime(), burst_lime(), embers_orange()]


def add(img, mask, color, gain=1.0):
    img += (mask[..., None] if mask.ndim == 2 else mask) * (np.asarray(color, np.float32) * gain)


def screen(img, mask, color, gain=1.0):
    m = (mask[..., None] if mask.ndim == 2 else mask) * gain
    img[:] = 1 - (1 - img) * (1 - np.clip(m * np.asarray(color, np.float32), 0, 1))


def rays(cam, t, center, n, spread, length, rot_speed, seed):
    rng = np.random.default_rng(seed)
    im = Image.new("L", (W, H))
    d = ImageDraw.Draw(im)
    u0, v0 = cam.to_out(*center)
    base = rng.uniform(0, 2 * math.pi, n)
    widths = rng.uniform(0.03, 0.09, n)
    for i in range(n):
        a = base[i] + rot_speed * t
        if spread and not (-math.pi + 0.15 < ((a + math.pi) % (2 * math.pi)) - math.pi < -0.15):
            continue     # only upward rays when spread is set
        w = widths[i]
        Ln = length * cam.z / cam.z * (0.7 + 0.3 * math.sin(base[i] * 5 + t * 2))
        p1 = (u0 + Ln * math.cos(a - w), v0 + Ln * math.sin(a - w))
        p2 = (u0 + Ln * math.cos(a + w), v0 + Ln * math.sin(a + w))
        d.polygon([(u0, v0), p1, p2], fill=int(140 + 115 * rng.random()))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(10)), np.float32) / 255


def star(d, u, v, r, val):
    d.polygon([(u, v - r), (u + r * 0.16, v - r * 0.16), (u + r, v), (u + r * 0.16, v + r * 0.16),
               (u, v + r), (u - r * 0.16, v + r * 0.16), (u - r, v), (u - r * 0.16, v - r * 0.16)], fill=val)


def juicebox_state(t):
    """(x, y, height, angle, xscale) of the juice box in source space, or None before the rise."""
    if t < T_RISE[0]:
        return None
    p = (t - T_RISE[0]) / (T_RISE[1] - T_RISE[0])
    e = ease_out_back(p, 1.4)
    x = JB_START[0] + (JB_END[0] - JB_START[0]) * e
    y = JB_START[1] + (JB_END[1] - JB_START[1]) * e
    hgt = JB_H * (0.78 + 0.22 * ease_out(p))
    ang = 14 * math.sin(p * math.pi * 1.5) * (1 - ease_out(p)) if p < 1 else 0.0
    xs = 1.0 - 0.18 * math.sin(min(p, 1) * math.pi)           # squash-stretch while it shoots up
    if t > T_RISE[1]:
        dt = t - T_RISE[1]
        y += -16 * math.sin(2 * math.pi * 0.55 * dt)
        ang = 4.5 * math.sin(2 * math.pi * 0.4 * dt + 0.3)
        xs = 1.0 + 0.02 * math.sin(2 * math.pi * 0.55 * dt)
    return x, y, hgt, ang, xs


# ---------------------------------------------------------------- frame
def render(t):
    cam = Cam(t)
    opened = t >= T_OPEN
    src = A["open"] if opened else A["closed"]
    if not opened:
        # chest rattle: offset the chest region inside the frame
        jx = jy = 0.0
        for tk, s in KNOCKS:
            k = pulse(t, tk, 0.0, 0.05)
            jx += 7 * s * k * math.sin(tk * 113)
            jy += -10 * s * k
        build = smooth((t - 2.8) / (T_OPEN - 2.8))
        jx += 2.5 * build * math.sin(t * 157)
        if abs(jx) + abs(jy) > 0.3:
            src = src.copy()
            cb = CHEST_BOX
            src.paste(A["chest_crop"], (int(cb[0] + jx), int(cb[1] + jy)), A["chest_mask"])
    img = np.asarray(cam.view(src), np.float32) / 255

    # painted lightning flickers with the strikes
    fl = 0.12 * (0.5 + 0.5 * math.sin(t * 23) * math.sin(t * 7.1))
    for ts, s in STRIKES + POST_STRIKES:
        fl += 0.9 * s * strike_level(t, ts)
    lm = np.asarray(cam.view(A["lm_open" if opened else "lm_closed"]), np.float32) / 255
    add(img, lm, LIME, 0.55 * min(fl, 1.6))

    if not opened:
        b = 0.25 + 1.1 * ease_in(t / T_OPEN)
        for tk, s in KNOCKS:
            b += 0.6 * s * pulse(t, tk, 0.0, 0.08)
        seam = np.asarray(cam.view(A["seam"]), np.float32) / 255
        add(img, seam, LIME, 0.5 * b)
    else:
        tt = t - T_OPEN
        og = np.asarray(cam.view(A["open_glow"]), np.float32) / 255
        throb = 0.85 + 0.15 * math.sin(tt * 5.3)
        add(img, og, ORANGE, (0.22 + 0.7 * math.exp(-tt / 0.5)) * throb)
        ray = rays(cam, t, OPENING, 26, True, 1500, 0.12, 5)
        screen(img, ray, ORANGE_HOT, 0.28 * smooth(tt / 0.3))

    bolts = draw_bolts(cam, t)
    if bolts is not None:
        ink, glow, core = bolts
        img *= 1 - 0.55 * ink[..., None]
        add(img, glow, LIME, 0.9)
        screen(img, core, LIME_HOT, 1.0)

    # juice box
    jb = juicebox_state(t)
    if jb is not None:
        x, y, hgt, ang, xs = jb
        k = hgt / A["jb"].height / cam.s
        sz = (max(2, int(A["jb"].width * k * xs)), max(2, int(A["jb"].height * k)))
        spr = A["jb"].resize(sz, Image.LANCZOS).rotate(ang, Image.BICUBIC, expand=True)
        gl = A["jb_glow"].resize((int(sz[0] * 1.25), int(sz[1] * 1.18)), Image.BILINEAR).rotate(ang, Image.BILINEAR, expand=True)
        u, v = cam.to_out(x, y)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(spr, (int(u - spr.width / 2), int(v - spr.height / 2)))
        glow = Image.new("L", (W, H))
        glow.paste(gl, (int(u - gl.width / 2), int(v - gl.height / 2)))
        # hide everything below the chest's front rim
        ru0, rv0 = cam.to_out(0, RIM_Y)
        ru1, rv1 = cam.to_out(SRC_W, RIM_Y)
        clip = Image.new("L", (W, H))
        ImageDraw.Draw(clip).polygon([(ru0 - 2000, rv0), (ru1 + 2000, rv1), (W + 2000, -2000), (-2000, -2000)], fill=255)
        clip = clip.filter(ImageFilter.GaussianBlur(1.5))
        la = np.asarray(layer, np.float32) / 255
        cl = np.asarray(clip, np.float32) / 255
        alpha = la[..., 3:4] * cl[..., None]
        gpulse = 0.75 + 0.25 * math.sin((t - T_RISE[0]) * 4.2)
        gm = np.asarray(glow.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255 * cl
        halo_on = smooth((t - T_RISE[0]) / 0.5)
        add(img, gm, ORANGE, 0.75 * gpulse * halo_on)
        # sunburst behind the box once it is out
        if t > T_RISE[0] + 0.5:
            sb = rays(cam, t, (x, y), 18, False, 900, 0.35, 9)
            add(img, sb, ORANGE, 0.28 * smooth((t - T_RISE[0] - 0.5) / 0.6))
        # shockwave when the box settles
        if T_LAND - 0.02 < t < T_LAND + 0.7:
            k = (t - T_LAND) / 0.7
            u, v = cam.to_out(x, y)
            r = (80 + 1100 * ease_out(k)) / cam.s * 0.5
            ring = Image.new("L", (W, H))
            ImageDraw.Draw(ring).ellipse((u - r, v - r * 0.85, u + r, v + r * 0.85), outline=int(255 * (1 - k)), width=max(2, int(30 * (1 - k))))
            add(img, np.asarray(ring.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255, ORANGE_HOT, 1.4)
        img[:] = img * (1 - alpha) + la[..., :3] * alpha
        # warm rim light on the box
        add(img, alpha[..., 0] * (np.asarray(glow, np.float32) / 255 > 0.0), ORANGE_HOT, 0.06 * gpulse)

    # particles + glints
    pl = Image.new("RGB", (W, H))
    pd = ImageDraw.Draw(pl)
    PARTS[0].draw(cam, t, pd, 0.9 + 0.8 * ease_in(t / T_OPEN))
    PARTS[1].draw(cam, t, pd, 1.2)
    PARTS[2].draw(cam, t, pd, 1.0)
    st = Image.new("L", (W, H))
    sd = ImageDraw.Draw(st)
    if jb is not None and t > T_LAND - 0.1:
        rng = np.random.default_rng(42)
        for i in range(9):
            ph = rng.uniform(0, 6.28)
            tw = max(0.0, math.sin(t * rng.uniform(2.5, 4.5) + ph)) ** 3
            ox, oy = rng.uniform(-330, 330), rng.uniform(-380, 320)
            u, v = cam.to_out(jb[0] + ox, jb[1] + oy)
            star(sd, u, v, (18 + 26 * tw) * cam.z * 0.6, int(255 * tw))
        for tg in (T_LAND, T_DING):
            k = pulse(t, tg, 0.0, 0.35)
            if k > 0.02:
                u, v = cam.to_out(jb[0] + 120, jb[1] - 190)
                star(sd, u, v, 120 * k * cam.z * 0.6, int(255 * k))
    plf = np.asarray(pl.filter(ImageFilter.GaussianBlur(1.6)), np.float32) / 255
    img += plf * 1.6 + np.asarray(pl.filter(ImageFilter.GaussianBlur(7)), np.float32) / 255 * 1.4
    stf = np.asarray(st.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    screen(img, stf, (1.0, 0.95, 0.8), 1.0)
    add(img, np.asarray(st.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255, ORANGE_HOT, 0.8)

    # bloom
    br = np.clip(img - 0.82, 0, None)
    small = Image.fromarray((np.clip(br, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    img += np.asarray(small, np.float32) / 255 * 0.7

    # flashes
    fl = 0.0
    for ts, s in STRIKES + POST_STRIKES:
        fl += 0.22 * s * strike_level(t, ts) * (0.3 if ts == T_OPEN else 1)
    flash_lime = min(fl, 0.6)
    screen(img, np.ones((H, W), np.float32), LIME_HOT, flash_lime * 0.55)
    big = pulse(t, T_OPEN, 0.07, 0.32)
    screen(img, np.ones((H, W), np.float32), (1.0, 0.97, 0.88), min(1.0, big * 1.05))
    land = pulse(t, T_LAND, 0.0, 0.12)
    screen(img, np.ones((H, W), np.float32), ORANGE_HOT, 0.35 * land)

    img *= A["vignette"]
    img *= smooth(t / 0.4)                                   # fade in from black
    img = img / (1 + 0.18 * np.clip(img - 1, 0, None))        # soft shoulder
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def render_to(args):
    i, fps, folder = args
    Image.fromarray(render(i / fps)).save(os.path.join(folder, f"{i:04d}.png"), compress_level=1)
    return i


def _init():
    load_assets()


# ================================================================ audio
def env(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / d)
    return e


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x)


class Mix:
    def __init__(self):
        self.L = np.zeros(int(SR * (DUR + 3)))
        self.R = np.zeros_like(self.L)
        self.dry_L = np.zeros_like(self.L)
        self.dry_R = np.zeros_like(self.L)

    def put(self, t, x, gain=1.0, pan=0.0, dry=False):
        i = int(t * SR)
        if i < 0:
            x, i = x[-i:], 0
        x = x[: len(self.L) - i]
        gl, gr = gain * math.cos((pan + 1) * math.pi / 4) * 1.414, gain * math.sin((pan + 1) * math.pi / 4) * 1.414
        L, R = (self.dry_L, self.dry_R) if dry else (self.L, self.R)
        L[i:i + len(x)] += x * gl
        R[i:i + len(x)] += x * gr


def thunder(rng, strength, length=3.0):
    n = int(SR * length)
    w = rng.standard_normal(n)
    crack = hp(w, 1800) * env(n, 0.001, 0.035) * 1.2
    mid = bp(w, 180, 2500) * env(n, 0.004, 0.28)
    crackle = (rng.random(n) < 0.004 * np.exp(-np.arange(n) / SR / 0.5)) * rng.standard_normal(n)
    crackle = bp(crackle, 1500, 9000) * 6
    brown = np.cumsum(rng.standard_normal(n))
    brown = hp(brown, 18)
    brown /= np.abs(brown).max() + 1e-9
    rumble = lp(brown, 110, 4) * env(n, 0.06, 0.9 + 1.2 * strength)
    lfo = 1 + 0.5 * np.sin(2 * np.pi * np.cumsum(rng.uniform(1.5, 4, n)) / SR)
    rumble *= lfo
    x = crack * strength + mid * 0.8 * strength + crackle * strength + rumble * 2.2 * strength
    return x


def zap(rng, length):
    """Electric arc: buzzing saw + spitting noise, flickery."""
    n = int(SR * length)
    t = np.arange(n) / SR
    f = 118 + 6 * np.sin(2 * np.pi * 9 * t)
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) + 0.5 * signal.sawtooth(2 * np.pi * np.cumsum(f * 2.01) / SR)
    flick = (np.repeat(rng.random(n // 240 + 1), 240)[:n] > 0.35).astype(float)
    flick = lp(flick, 300)
    hiss = bp(rng.standard_normal(n), 2500, 11000) * 0.8
    x = bp(saw, 90, 4000) * 0.6 + hiss
    return x * flick * env(n, 0.004, length * 0.45)


def knock(rng, strength):
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    wood = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / d)
               for f, a, d in ((165, 1.0, 0.07), (322, 0.6, 0.05), (587, 0.35, 0.03), (1130, 0.15, 0.015)))
    click = bp(rng.standard_normal(n), 700, 3500) * env(n, 0.0005, 0.012)
    metal = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / 0.04) for f in (2630, 3910, 5420)) * 0.12
    metal *= rng.random() < 0.7
    return (wood + click * 0.9 + metal) * strength


def bell(freq, length=2.5, bright=1.0):
    n = int(SR * length)
    t = np.arange(n) / SR
    parts = ((1.0, 1.0, 1.4), (2.76, 0.45 * bright, 0.7), (5.40, 0.25 * bright, 0.35), (8.93, 0.12 * bright, 0.2), (2.0, 0.3, 1.0))
    return sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / d) for r, a, d in parts) * env(n, 0.002, 10)


def shimmer(rng, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for _ in range(36):
        f = rng.uniform(1800, 7500)
        x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(3, 11) * t + rng.uniform(0, 6))) ** 4
    return x / 36


def pad(length, freqs):
    """Choir-ish glow pad: detuned saws through vowel formants, slow vibrato."""
    n = int(SR * length)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.006, 0.0, 0.007):
            ff = f * (1 + det) * (1 + 0.004 * np.sin(2 * np.pi * 5.2 * t + f))
            x += signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR)
    x = bp(x, 500, 950) * 1.0 + bp(x, 1050, 1500) * 0.6 + lp(x, 400) * 0.4
    return x / len(freqs) / 3


def sweep_noise(rng, length, f0, f1, q=0.6):
    """Noise through a band-pass whose centre glides f0 -> f1 (state-variable filter)."""
    n = int(SR * length)
    w = rng.standard_normal(n)
    fc = f0 * (f1 / f0) ** (np.arange(n) / n)
    F = 2 * np.sin(np.pi * np.minimum(fc, SR / 6) / SR)
    low = band = 0.0
    out = np.empty(n)
    for i in range(n):
        high = w[i] - low - q * band
        band += F[i] * high
        low += F[i] * band
        out[i] = band
    return out / (np.abs(out).max() + 1e-9)


def make_audio(path):
    rng = np.random.default_rng(11)
    m = Mix()
    n_all = int(SR * DUR)
    t_all = np.arange(n_all) / SR
    # storm bed: rolling low rumble + wind, swelling into the burst, calmer after
    brown = hp(np.cumsum(rng.standard_normal(n_all)), 15)
    brown /= np.abs(brown).max()
    bed = lp(brown, 140, 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t_all))
    shape = np.where(t_all < T_OPEN, 0.5 + 0.6 * (t_all / T_OPEN) ** 2, 0.45)
    shape *= np.minimum(t_all / 0.4, 1)
    m.put(0, bed * shape, 1.4)
    wind = bp(rng.standard_normal(n_all), 300, 1400) * (0.3 + 0.3 * np.sin(2 * np.pi * 0.15 * t_all + 1)) * shape
    m.put(0, wind, 0.08, -0.2)
    m.put(0, bp(rng.standard_normal(n_all), 320, 1500) * (0.3 + 0.3 * np.sin(2 * np.pi * 0.11 * t_all)) * shape, 0.08, 0.25)
    # constant electric hum around the chest, building
    hum_len = T_OPEN
    hum = zap(np.random.default_rng(5), hum_len) / (env(int(SR * hum_len), 0.004, hum_len * 0.45) + 1e-3)
    hum *= (np.arange(len(hum)) / len(hum)) ** 1.6
    m.put(0, hum, 0.05)
    # strikes: thunder + zaps
    for ts, s in STRIKES[:-1] + POST_STRIKES:
        r = np.random.default_rng(int(ts * 1000))
        m.put(ts - 0.01, thunder(r, s), 0.75, r.uniform(-0.6, 0.6))
        m.put(ts - 0.02, zap(r, 0.45), 0.35 * s, r.uniform(-0.5, 0.5))
    # sparks crackle bed (density follows the build)
    n = int(SR * DUR)
    dens = np.interp(t_all, [0, 2.5, T_OPEN, T_OPEN + 0.1, DUR], [0.0004, 0.001, 0.004, 0.0015, 0.0008])
    cr = (rng.random(n) < dens) * rng.standard_normal(n)
    cr = hp(cr, 2500) * 2.5
    m.put(0, cr, 0.35, 0.3)
    m.put(0, np.roll(cr, 9000), 0.3, -0.3)
    # rattle knocks
    for tk, s in KNOCKS:
        r = np.random.default_rng(int(tk * 997))
        m.put(tk, knock(r, s), 0.55, r.uniform(-0.25, 0.25))
    # risers into the burst: tonal + whoosh, cut just before the hit
    rl = T_OPEN - 1.2
    rise_t = np.arange(int(SR * (T_OPEN - rl))) / SR
    rf = 110 * (900 / 110) ** ((rise_t / rise_t[-1]) ** 1.5)
    riser = sum(signal.sawtooth(2 * np.pi * np.cumsum(rf * k) / SR) for k in (1, 1.5, 2.003)) / 3
    riser = lp(riser, 3000) * (rise_t / rise_t[-1]) ** 2
    riser[-int(SR * 0.04):] *= np.linspace(1, 0, int(SR * 0.04))
    m.put(rl, riser, 0.18)
    wh = sweep_noise(rng, T_OPEN - 0.5, 150, 5000) * np.linspace(0, 1, int(SR * (T_OPEN - 0.5))) ** 2.5
    wh[-int(SR * 0.03):] *= np.linspace(1, 0, int(SR * 0.03))
    m.put(0.5, wh, 0.35)
    # THE BURST: sub drop + giant thunder + lid slam + shimmer
    nb = int(SR * 2.4)
    tb = np.arange(nb) / SR
    sub = np.sin(2 * np.pi * np.cumsum(28 + 80 * np.exp(-tb / 0.18)) / SR) * env(nb, 0.003, 0.9)
    m.put(T_OPEN, sub, 1.3, dry=True)
    m.put(T_OPEN - 0.005, thunder(np.random.default_rng(99), 1.6, 3.5), 0.9)
    m.put(T_OPEN, knock(np.random.default_rng(3), 1.0) * 1.8 + lp(knock(np.random.default_rng(4), 1.0), 400) * 2, 0.8)
    m.put(T_OPEN, zap(np.random.default_rng(8), 0.9), 0.6)
    imp = bp(rng.standard_normal(nb), 60, 9000) * env(nb, 0.001, 0.25)
    m.put(T_OPEN, imp, 0.7)
    # magic: shimmer + choir pad + rising whoosh for the juice box
    sh = shimmer(np.random.default_rng(21), DUR - T_OPEN + 1) * env(int(SR * (DUR - T_OPEN + 1)), 0.6, 6)
    m.put(T_OPEN + 0.05, sh, 0.55, 0.1)
    plen = DUR - T_OPEN + 0.5
    p = pad(plen, (146.8, 220.0, 293.7, 370.0, 440.0))       # D major
    pe = np.minimum(np.arange(len(p)) / SR / 1.2, 1) * np.clip((plen - np.arange(len(p)) / SR) / 0.8, 0, 1)
    m.put(T_OPEN + 0.15, p * pe, 0.45)
    up = sweep_noise(np.random.default_rng(31), T_RISE[1] - T_RISE[0], 300, 7000, 0.8)
    up *= np.sin(np.linspace(0, np.pi, len(up))) ** 1.2
    m.put(T_RISE[0], up, 0.3)
    # landing: chime + sparkle arpeggio + soft boom
    m.put(T_LAND, bell(880, 3.0), 0.32, -0.1)
    m.put(T_LAND, bell(1318.5, 2.5) * 0.7, 0.3, 0.15)
    for i, f in enumerate((1760, 2217, 2637, 3520, 4434)):
        m.put(T_LAND + 0.06 + i * 0.07, bell(f, 1.2, 0.6), 0.12, -0.6 + 0.3 * i)
    nl = int(SR * 1.2)
    tl = np.arange(nl) / SR
    m.put(T_LAND, np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-tl / 0.1)) / SR) * env(nl, 0.003, 0.4), 0.7, dry=True)
    # final ding
    m.put(T_DING, bell(1760, 2.5), 0.28, 0.05)
    for i, f in enumerate((2637, 3520, 4186, 5274)):
        m.put(T_DING + 0.05 + i * 0.06, bell(f, 1.0, 0.5), 0.09, 0.5 - 0.3 * i)
    # reverb (stereo exponential-noise IR)
    nir = int(SR * 1.9)
    tir = np.arange(nir) / SR
    irL = rng.standard_normal(nir) * np.exp(-tir / 0.42)
    irR = rng.standard_normal(nir) * np.exp(-tir / 0.42)
    irL[: int(SR * 0.012)] = 0
    irR[: int(SR * 0.017)] = 0
    irL, irR = lp(irL, 6000) / 40, lp(irR, 6000) / 40
    wetL = signal.fftconvolve(m.L, irL)[: len(m.L)]
    wetR = signal.fftconvolve(m.R, irR)[: len(m.R)]
    L = m.L + m.dry_L + 0.35 * wetL
    R = m.R + m.dry_R + 0.35 * wetR
    st = np.stack([L, R], 1)[:n_all]
    st = hp(st.T, 22).T
    st /= np.abs(st).max() + 1e-9
    st = np.tanh(st * 3.2) / np.tanh(3.2)                   # glue + limiter
    st *= 10 ** (-1 / 20) / (np.abs(st).max() + 1e-9)
    fade = np.minimum(np.arange(n_all) / SR / 0.05, 1) * np.clip((DUR - np.arange(n_all) / SR) / 0.25, 0, 1)
    st *= fade[:, None]
    from scipy.io import wavfile
    wavfile.write(path, SR, (st * 32767).astype(np.int16))


# ================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preview", action="store_true", help="render a few stills instead of the video")
    ap.add_argument("--frames-dir", default=os.path.join(OUT_DIR, "_frames"))
    a = ap.parse_args()
    if a.preview:
        load_assets()
        for t in (0.2, 2.31, 4.6, 5.52, 5.9, 6.6, 7.35, 8.5, 9.9):
            Image.fromarray(render(t)).save(os.path.join(a.frames_dir, f"preview_{t:.2f}.png"))
            print("preview", t, flush=True)
        return
    os.makedirs(a.frames_dir, exist_ok=True)
    wav = os.path.join(OUT_DIR, "reveal_audio.wav")
    make_audio(wav)
    print("wrote", wav, flush=True)
    n = int(DUR * a.fps)
    with Pool(os.cpu_count(), initializer=_init) as pool:
        for k, _ in enumerate(pool.imap_unordered(render_to, [(i, a.fps, a.frames_dir) for i in range(n)], chunksize=4)):
            if k % 30 == 0:
                print(f"frame {k}/{n}", flush=True)
    out = os.path.join(OUT_DIR, "mystery_chest_reveal.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(a.frames_dir, "%04d.png"),
                    "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(a.frames_dir)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())
