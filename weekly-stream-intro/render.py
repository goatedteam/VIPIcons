#!/usr/bin/env python3
"""Goated Weekly Stream — 10s motion-graphics intro.

Renders 1920x1080 @ 60fps with numpy + OpenCV, then muxes the music (from 0:25).
Every hit is keyed to an onset measured in the track (see HITS below).

  python3 render.py                 # full render -> out/goated_weekly_stream_intro.mp4
  python3 render.py --preview 1.6 3.5 9.99   # stills -> out/preview_*.png
  python3 render.py --sheet         # contact sheet of the timeline -> out/sheet.png
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")

W, H = 1920, 1080
FPS = 60
DUR = 12.0
NFRAMES = int(DUR * FPS)
MUSIC_START = 25.0

LIME = np.array([215, 255, 0], np.float32) / 255.0
WHITE = np.array([1, 1, 1], np.float32)
CX, CY = W / 2, H / 2

# Onsets measured in the track, seconds after 0:25.
# 808 hits (H) and claps (C).
H1, C1, H2A, H2B, C2, H3, C3, H4A, H4B, C4, H5, C5 = (
    1.56, 2.39, 3.42, 3.63, 4.04, 4.87, 5.69, 6.73, 6.94, 7.35, 8.17, 9.00)
# hits during the end hold: only drive gentle glow pulses
HOLD_HITS = (10.03, 10.24, 10.67, 11.48)

# Final layout (matches the reference key art, scaled to 1920x1080).
LOGO_POS = (960.0, 277.0)
LOGO_W = 88.0
GOATED_Y, GOATED_CAP = 431.0, 108.0
STREAM_Y, STREAM_CAP = 626.0, 182.0
DATE_Y = 814.0
KICK_Y = 982.0


# ----------------------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def u(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def in_cubic(x):
    x = clamp(x)
    return x ** 3


def out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def in_out_expo(x):
    x = clamp(x)
    if x <= 0 or x >= 1:
        return x
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2


def out_back(x, k=1.70158):
    x = clamp(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def env(t, t0, decay):
    """Instant attack, exponential decay impulse."""
    return math.exp(-(t - t0) / decay) if t >= t0 else 0.0


def lerp(a, b, x):
    return a + (b - a) * x


# ----------------------------------------------------------------------------- time warp
# Rain (and the background) slow to a float on the last big hit, landing on the key art.
_TT = np.arange(0, DUR + 0.5, 0.001)


def _rain_speed(t):
    if t < H5 - 0.10:
        return 1.0
    x = smooth((t - (H5 - 0.10)) / 0.40)
    return lerp(1.0, 0.035, x)


def _bg_speed(t):
    if t < H5 - 0.10:
        return 1.0
    return lerp(1.0, 0.30, smooth((t - (H5 - 0.10)) / 0.5))


_TAU = np.concatenate([[0], np.cumsum([_rain_speed(t) * 0.001 for t in _TT[:-1]])])
_BGT = np.concatenate([[0], np.cumsum([_bg_speed(t) * 0.001 for t in _TT[:-1]])])


def tau(t):
    if t <= 0:
        return t
    return float(np.interp(t, _TT, _TAU))


def bg_time(t):
    return float(np.interp(max(t, 0), _TT, _BGT))


TAU_END = tau(DUR)


# ----------------------------------------------------------------------------- image helpers
def premult(rgba_u8):
    a = rgba_u8[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba_u8[..., :3].astype(np.float32) / 255.0
    return np.concatenate([rgb * a, a], axis=2)


def crop_alpha(arr, pad=6):
    ys, xs = np.where(arr[..., 3] > 0.002)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    arr = arr[y0:y1, x0:x1]
    return cv2.copyMakeBorder(arr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)


class Img:
    """Premultiplied RGBA with a mip chain. `density` = source px per output px at scale 1."""

    def __init__(self, arr, density=1.0):
        self.levels = []
        d = density
        while True:
            self.levels.append((d, arr))
            if d <= 0.13 or min(arr.shape[:2]) < 16:
                break
            arr = cv2.resize(arr, (max(1, arr.shape[1] // 2), max(1, arr.shape[0] // 2)),
                             interpolation=cv2.INTER_AREA)
            d /= 2
        self.levels.reverse()  # smallest density first

    def pick(self, s):
        for d, arr in self.levels:
            if d >= s * 0.999:
                return d, arr
        return self.levels[-1]

    @property
    def size(self):  # output-space size at scale 1
        d, arr = self.levels[-1]
        return arr.shape[1] / d, arr.shape[0] / d


def composite(dst, patch, x0, y0, alpha=1.0):
    """Premultiplied 'over' of patch (h,w,4) onto dst (H,W,3 or 4) at (x0,y0)."""
    h, w = patch.shape[:2]
    if alpha <= 0:
        return
    region = dst[y0:y0 + h, x0:x0 + w]
    a = patch[..., 3:4] * alpha
    if dst.shape[2] == 4:
        region *= (1 - a)
        region += patch * alpha
    else:
        region *= (1 - a)
        region += patch[..., :3] * alpha


def _bbox(pts, pad=2):
    x0 = int(math.floor(pts[:, 0].min())) - pad
    y0 = int(math.floor(pts[:, 1].min())) - pad
    x1 = int(math.ceil(pts[:, 0].max())) + pad
    y1 = int(math.ceil(pts[:, 1].max())) + pad
    return x0, y0, x1, y1


def affine_for(img_arr, d, cx, cy, s, ang, sx, sy):
    h, w = img_arr.shape[:2]
    k = s / d
    c, si = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a, b = c * k * sx, -si * k * sy
    cc, dd = si * k * sx, c * k * sy
    tx = cx - (a * w / 2 + b * h / 2)
    ty = cy - (cc * w / 2 + dd * h / 2)
    M = np.array([[a, b, tx], [cc, dd, ty]], np.float64)
    corners = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], np.float64) @ M.T
    return M, corners


def blit(dst, img, states, alpha=1.0, blur=0.0, ret_patch=False):
    """Draw img at one or more transforms (averaged => motion blur).
    states: list of (cx, cy, s, ang, sx, sy)."""
    if alpha <= 0.001:
        return None
    smax = max(st[2] * max(abs(st[4]), abs(st[5])) for st in states)
    if smax <= 1e-4:
        return None
    d, arr = img.pick(smax)
    Ms, allc = [], []
    for (cx, cy, s, ang, sx, sy) in states:
        M, cr = affine_for(arr, d, cx, cy, s, ang, sx, sy)
        Ms.append(M)
        allc.append(cr)
    pad = int(blur * 3) + 2
    x0, y0, x1, y1 = _bbox(np.concatenate(allc), pad)
    Hd, Wd = dst.shape[:2]
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, Wd), min(y1, Hd)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    pw, ph = cx1 - cx0, cy1 - cy0
    acc = None
    for M in Ms:
        M2 = M.copy()
        M2[0, 2] -= cx0
        M2[1, 2] -= cy0
        p = cv2.warpAffine(arr, M2, (pw, ph), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        acc = p if acc is None else acc + p
    if len(Ms) > 1:
        acc /= len(Ms)
    if blur > 0.3:
        acc = cv2.GaussianBlur(acc, (0, 0), blur)
    if ret_patch:
        return acc, cx0, cy0
    composite(dst, acc, cx0, cy0, alpha)
    return acc, cx0, cy0


# ----------------------------------------------------------------------------- 3D sprites
F3D = 1600.0
LIGHT = np.array([-0.35, -0.55, -0.76])
LIGHT /= np.linalg.norm(LIGHT)


def rot3(rx, ry, rz):
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def sprite_quad(w_out, h_out, cx, cy, rx, ry, rz, flip):
    R = rot3(rx, ry, rz)
    hw, hh = w_out / 2, h_out / 2
    loc = np.array([[-hw, -hh, 0], [hw, -hh, 0], [hw, hh, 0], [-hw, hh, 0]], np.float64)
    if flip:
        loc[:, 0] *= -1
    P = loc @ R.T
    z = F3D / (F3D + P[:, 2])
    pts = np.stack([cx + P[:, 0] * z, cy + P[:, 1] * z], 1)
    n = R @ np.array([0, 0, 1.0])
    return pts, n


def draw_sprite(dst, img, states, alpha=1.0, blur=0.0, tint=0.0, tint_col=None, bright=1.0):
    """states: list of (cx, cy, s, rx, ry, rz, flip) — several => motion blur."""
    if alpha <= 0.002:
        return
    smax = max(st[2] for st in states)
    d, arr = img.pick(smax)
    h, w = arr.shape[:2]
    quads, normals = [], []
    for (cx, cy, s, rx, ry, rz, flip) in states:
        q, n = sprite_quad(w / d * s, h / d * s, cx, cy, rx, ry, rz, flip)
        quads.append(q)
        normals.append(n)
    pad = int(blur * 3) + 2
    x0, y0, x1, y1 = _bbox(np.concatenate(quads), pad)
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    pw, ph = cx1 - cx0, cy1 - cy0
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    acc = None
    for q in quads:
        Mp = cv2.getPerspectiveTransform(src, (q - [cx0, cy0]).astype(np.float32))
        p = cv2.warpPerspective(arr, Mp, (pw, ph), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        acc = p if acc is None else acc + p
    if len(quads) > 1:
        acc /= len(quads)
    n = normals[len(normals) // 2]
    facing = abs(n[2])
    shade = (0.62 + 0.38 * facing) * bright
    spec = abs(float(n @ LIGHT)) ** 24 * 0.45
    acc[..., :3] *= shade
    acc[..., :3] += spec * acc[..., 3:4]
    if tint > 0:
        acc[..., :3] = acc[..., :3] * (1 - tint) + tint_col * acc[..., 3:4] * tint
    if blur > 0.3:
        acc = cv2.GaussianBlur(acc, (0, 0), blur)
    composite(dst, acc, cx0, cy0, alpha)


# ----------------------------------------------------------------------------- assets
def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA"))


def hires_mask_shape(rgba, factor):
    """Upscale a small flat-colour graphic and re-sharpen its edge (vector-like)."""
    a = rgba[..., 3].astype(np.float32) / 255.0
    a = cv2.copyMakeBorder(a, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=0)
    big = cv2.resize(a, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), factor * 0.35)
    big = np.clip((big - 0.5) * 2.2 + 0.5, 0, 1)
    return big


def text_img(text, font, color, ss):
    """Render a run of text; returns (Img, width_out, ink box) with density ss."""
    l, t, r, b = font.getbbox(text, anchor="ls")
    pad = 8 * ss
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=255, anchor="ls")
    a = np.array(im).astype(np.float32) / 255.0
    arr = np.dstack([a * color[0], a * color[1], a * color[2], a]).astype(np.float32)
    # centre of the ink relative to baseline origin, in output px
    return arr, (pad - l), (pad - t)


class Glyphs:
    """Per-character layout of a line: list of (char, Img, cx, cy) in output coords,
    for a line centred at (x_center, y_center_of_caps)."""

    def __init__(self, text, font_path, size_out, color, ss, x_center, cap_center_y, track=0.0):
        font = ImageFont.truetype(font_path, int(round(size_out * ss)))
        self.font, self.ss, self.color = font, ss, color
        cap_t = font.getbbox("H", anchor="ls")[1]  # negative, cap top above baseline
        total = font.getlength(text) + track * ss * (len(text) - 1)
        base_x = x_center * ss - total / 2
        base_y = cap_center_y * ss - cap_t / 2  # baseline so caps are centred
        self.items = []
        for i, ch in enumerate(text):
            if ch == " ":
                continue
            x = base_x + font.getlength(text[:i]) + track * ss * i
            arr, ox, oy = text_img(ch, font, color, ss)
            h, w = arr.shape[:2]
            cx = (x - ox + w / 2) / ss
            cy = (base_y - oy + h / 2) / ss
            self.items.append((ch, i, Img(arr, ss), cx, cy))
        self.width = total / ss
        self.base_x, self.base_y = base_x, base_y

    def glyph_at(self, ch, x_left_ss, ss):
        arr, ox, oy = text_img(ch, self.font, self.color, ss)
        return arr, ox, oy


def word_img(text, font_path, size_out, color, ss):
    font = ImageFont.truetype(font_path, int(round(size_out * ss)))
    arr, ox, oy = text_img(text, font, color, ss)
    cap_t = font.getbbox("H", anchor="ls")[1]
    return Img(arr, ss), font, ox, oy, cap_t


class Assets:
    def __init__(self):
        self.bill = Img(crop_alpha(premult(load_rgba(os.path.join(A, "bill.png")))))
        self.dice = Img(crop_alpha(premult(load_rgba(os.path.join(A, "dice.png")))))
        self.ticket = Img(crop_alpha(premult(load_rgba(os.path.join(A, "ticket.png")))))
        self.kind = {"bill": self.bill, "dice": self.dice, "ticket": self.ticket}

        # Logo: rebuilt at 8x from the supplied mark so it stays crisp when it slams in huge.
        logo = load_rgba(os.path.join(A, "logo.png"))
        F = 8
        a = hires_mask_shape(logo, F)
        arr = np.dstack([a * LIME[0], a * LIME[1], a * LIME[2], a]).astype(np.float32)
        self.logo_native_w = logo.shape[1] + 8  # incl. the 4px border added above
        self.logo = Img(arr, F)  # scale 1 == native pixel size
        self.logo_white = Img(np.dstack([a, a, a, a]).astype(np.float32), F)

        # Kick "K" icon from the supplied lockup, upscaled the same way.
        kl = load_rgba(os.path.join(A, "kick_line.png"))
        cols = np.where(kl[..., 3].max(0) > 0)[0]
        kend = cols[np.argmax(np.diff(cols) > 3)] + 1
        kpart = kl[:, :kend]
        rows = np.where(kpart[..., 3].max(1) > 0)[0]
        kpart = kpart[rows.min():rows.max() + 1]
        self.k_h_native = kpart.shape[0]
        ka = hires_mask_shape(kpart, F)
        kcol = kpart[..., :3][kpart[..., 3] > 200].mean(0) / 255.0
        self.kick_icon = Img(np.dstack([ka * kcol[0], ka * kcol[1], ka * kcol[2], ka]).astype(np.float32), F)
        # supplied lockup geometry (text start, total width) for proportions
        self.kick_text_x_native = cols[np.argmax(np.diff(cols) > 3) + 1]
        self.kick_total_native = cols.max() + 1

        schabo = os.path.join(A, "schabo-condensed.otf")
        geist = os.path.join(A, "Geist-Medium.otf")
        SS = 2
        # "THE GOATED": cap height 108 => Schabo caps are 0.80 em
        self.goated = Glyphs("THE GOATED", schabo, GOATED_CAP / 0.8, WHITE, SS, 960, GOATED_Y)
        # "WEEKLY STREAM" as two words laid out on one centred line
        size = STREAM_CAP / 0.8
        font = ImageFont.truetype(schabo, int(round(size * SS)))
        full = "WEEKLY STREAM"
        total = font.getlength(full)
        cap_t = font.getbbox("H", anchor="ls")[1]
        bx = 960 * SS - total / 2
        by = STREAM_Y * SS - cap_t / 2
        self.words = []
        for word, start in (("WEEKLY", 0), ("STREAM", 7)):
            arr, ox, oy = text_img(word, font, LIME, SS)
            h, w = arr.shape[:2]
            x = bx + font.getlength(full[:start])
            cx = (x - ox + w / 2) / SS
            cy = (by - oy + h / 2) / SS
            white = arr.copy()
            white[..., :3] = white[..., 3:4]
            self.words.append((Img(arr, SS), Img(white, SS), cx, cy, w / SS, h / SS))
        self.stream_x0 = bx / SS
        self.stream_x1 = (bx + total) / SS

        # Date line (Geist Medium); size chosen to match the reference width (603px).
        self.date_text = "1st October at 4 PM UTC"
        f100 = ImageFont.truetype(geist, 100)
        # type size matched to the reference line ("24th September at 4 PM UTC" = 603px wide)
        dsize = 603.0 / f100.getlength("24th September at 4 PM UTC") * 100
        geist_cap = -f100.getbbox("H", anchor="ls")[1] / 100.0
        self.date = Glyphs(self.date_text, geist, dsize, WHITE, SS, 960, DATE_Y)
        self.date_size = dsize
        self.geist = geist
        # scramble glyphs for the decode effect
        dfont = ImageFont.truetype(geist, int(round(dsize * SS)))
        self.scramble = []
        for ch in "0123456789ABCDEFGHJKMNPRSTUVWXYZ#%&$":
            arr, ox, oy = text_img(ch, dfont, LIME, SS)
            self.scramble.append(Img(arr, SS))

        # Kick line: icon + "kick.com/goatedcom", proportions taken from the supplied lockup.
        ktext = "kick.com/goatedcom"
        total_out = 290.0
        k = total_out / self.kick_total_native
        text_w_out = (self.kick_total_native - self.kick_text_x_native) * k
        ksize = text_w_out / f100.getlength(ktext) * 100
        self.kick_icon_scale = k  # icon native px -> out px
        x0 = 960 - total_out / 2
        icon_w = kend * k
        self.kick_icon_pos = (x0 + icon_w / 2, KICK_Y)
        tx_center = x0 + self.kick_text_x_native * k + text_w_out / 2
        self.kick = Glyphs(ktext, geist, ksize, WHITE, SS, tx_center, KICK_Y + 0.5)
        self.kick_cursor_h = geist_cap * ksize * 1.25


# ----------------------------------------------------------------------------- choreography data
def make_rain(rng):
    """Generic falling items + hero items that land on the key-art positions."""
    items = []

    def add(kind, layer, t0, x0, vx, vy, s, flip, ax_amp, extra=None):
        it = dict(kind=kind, layer=layer, t0=t0, x0=x0, vx=vx, vy=vy, s=s, flip=flip,
                  rz0=rng.uniform(-180, 180), wz=rng.uniform(-70, 70),
                  axa=ax_amp, axw=rng.uniform(2.2, 4.2), axp=rng.uniform(0, 6.28),
                  aya=ax_amp * 0.6, ayw=rng.uniform(1.5, 3.2), ayp=rng.uniform(0, 6.28),
                  swa=rng.uniform(15, 55), sww=rng.uniform(1.0, 2.2), swp=rng.uniform(0, 6.28))
        if kind == "dice":
            it["wz"] = rng.choice([-1, 1]) * rng.uniform(80, 220)
            it["axa"] = it["aya"] = 12
            it["swa"] = rng.uniform(0, 12)
        if extra:
            it.update(extra)
        items.append(it)
        return it

    def pick_kind():
        r = rng.random()
        return "bill" if r < 0.6 else "dice" if r < 0.8 else "ticket"

    native = {"bill": 640, "dice": 330, "ticket": 260}

    def side_x(edge_frac):
        if rng.random() < 0.5:
            return rng.uniform(-60, W * edge_frac)
        return rng.uniform(W * (1 - edge_frac), W + 60)

    layers = {
        # name: (rate fn, scale range, speed mult, blur)
        "mid": (lambda t: 1.4 if t < H1 else 4.2, (0.24, 0.42), 1.0),
        "near": (lambda t: 0.0 if t < H1 + 0.2 else 0.5, (0.55, 0.85), 1.9),
    }
    for name, (rate, (s0, s1), sp) in layers.items():
        t = -4.0
        while t < TAU_END:
            t += rng.exponential(1.0 / max(rate(max(t, 0)), 1e-3)) if rate(max(t, 0)) > 0 else 0.05
            if rate(max(t, 0)) <= 0:
                continue
            kind = pick_kind()
            if name == "near" and kind == "ticket":
                kind = "bill"
            s = rng.uniform(s0, s1) * (1.25 if kind == "dice" else 1.0)
            if kind == "ticket":
                s *= 1.1
            size = native[kind] * s
            if name == "mid":
                x = side_x(0.30) if rng.random() < 0.8 else rng.uniform(0, W)
            else:
                x = side_x(0.11)
            base = {"bill": 330, "dice": 620, "ticket": 380}[kind]
            vy = base * sp * rng.uniform(0.8, 1.25)
            vx = rng.uniform(-60, 60) * sp
            it = add(kind, name, t, x, vx, vy, s, rng.random() < 0.5, 55 if kind != "dice" else 12)
            it["m"] = size * 0.6 + 40
            # nothing generic may still be on screen when the rain freezes (key art is clean)
            exit_t = t + (H + 2 * it["m"]) / vy
            if exit_t > TAU_END - 0.05:
                items.pop()

    # hero items: (kind, x, y, scale, rz, flip) in output px — reference key-art positions
    sx, sy = W / 1796.0, H / 1168.0
    heroes = [
        ("bill", 20, 85, 0.25, -62, True),
        ("bill", 362, 238, 0.43, 22, True),
        ("dice", 52, 392, 0.86, -18, False),
        ("bill", 88, 705, 0.37, -28, True),
        ("bill", 182, 1062, 0.68, -24, True),
        ("bill", 1662, 86, 0.29, -32, False),
        ("bill", 1278, 184, 0.27, -14, True),
        ("bill", 1690, 466, 0.45, 12, False),
        ("dice", 1702, 752, 0.92, 32, False),
        ("bill", 1640, 1110, 0.63, -12, False),
    ]
    for kind, x, y, s, rz, flip in heroes:
        x, y = x * sx, y * sy
        vy = rng.uniform(330, 430) if kind != "dice" else rng.uniform(520, 640)
        add(kind, "hero", 0, x, rng.uniform(-30, 30), vy, s, flip, 55 if kind != "dice" else 12,
            dict(xe=x, ye=y, rze=rz, m=native[kind] * s * 0.6 + 40))

    # gust on the double 808 (two waves, from the top corners)
    for tt, side in ((H4A, -1), (H4B, 1)):
        for j in range(5):
            kind = "bill" if j % 3 else "ticket"
            x = (W * 0.08 + rng.uniform(-120, 220)) if side < 0 else (W * 0.92 + rng.uniform(-220, 120))
            vy = rng.uniform(1500, 2100)
            s = rng.uniform(0.55, 0.9)
            m = native[kind] * s * 0.6 + 40
            t0 = tt - (m * 0.6) / vy - j * 0.03
            it = add(kind, "gust", t0, x, -side * rng.uniform(80, 260), vy, s, rng.random() < 0.5, 70)
            it["m"] = m
    return items


def rain_state(it, T):
    """Position/orientation of a rain item at warped time T. Returns None when off-screen."""
    L = it["layer"]
    if L == "hero":
        dt = T - TAU_END
        x = it["xe"] + it["vx"] * dt + it["swa"] * math.sin(it["sww"] * dt)
        y = it["ye"] + it["vy"] * dt
        rz = it["rze"] + it["wz"] * dt
        rx = it["axa"] * math.sin(it["axw"] * dt)
        ry = it["aya"] * math.sin(it["ayw"] * dt)
    else:
        dt = T - it["t0"]
        if dt < 0:
            return None
        x = it["x0"] + it["vx"] * dt + it["swa"] * math.sin(it["sww"] * dt + it["swp"])
        y = -it["m"] + it["vy"] * dt
        rz = it["rz0"] + it["wz"] * dt
        rx = it["axa"] * math.sin(it["axw"] * dt + it["axp"])
        ry = it["aya"] * math.sin(it["ayw"] * dt + it["ayp"])
    m = it["m"]
    if y < -m * 1.2 or y > H + m * 1.2 or x < -m * 1.5 or x > W + m * 1.5:
        return None
    return x, y, rz, rx, ry


def make_sparks(rng):
    sp = []
    # converge into the logo before the first 808
    for i in range(70):
        ts = rng.uniform(0.35, 1.25)
        ang = rng.uniform(0, 2 * math.pi)
        sp.append(dict(type="in", ts=ts, te=H1, ang=ang, r0=rng.uniform(700, 1300),
                       w=rng.uniform(1.2, 2.6), col=LIME if rng.random() < 0.7 else WHITE))
    # bursts: (time, x, y, count, speed range, spread)
    def burst(t0, x, y, n, v0, v1, life, up_bias=0.0, xs=0.0, g=900):
        for i in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            if up_bias:
                ang = rng.uniform(math.pi * (1 + up_bias), math.pi * (2 - up_bias))
            v = rng.uniform(v0, v1)
            sp.append(dict(type="out", ts=t0, x=x + rng.uniform(-xs, xs), y=y, vx=math.cos(ang) * v,
                           vy=math.sin(ang) * v, life=rng.uniform(*life), g=g,
                           w=rng.uniform(1.0, 3.0), col=LIME if rng.random() < 0.65 else WHITE))
    burst(H2A, 690, STREAM_Y + 80, 45, 300, 1300, (0.3, 0.7), up_bias=0.05, xs=220)
    burst(H2B, 1235, STREAM_Y + 80, 45, 300, 1300, (0.3, 0.7), up_bias=0.05, xs=220)
    burst(H5, CX, STREAM_Y, 90, 400, 1900, (0.4, 1.0), xs=400)
    # ambient embers drifting up through the whole piece
    for i in range(36):
        sp.append(dict(type="ember", x=rng.uniform(0, W), ph=rng.uniform(0, 1), sp=rng.uniform(40, 110),
                       w=rng.uniform(1.5, 3.2), tw=rng.uniform(2, 6), twp=rng.uniform(0, 6.28),
                       sway=rng.uniform(10, 40)))
    return sp


# ----------------------------------------------------------------------------- global FX curves
FLASHES = [(H1, 0.62, 0.13), (H2A, 0.22, 0.08), (H2B, 0.28, 0.09), (H3, 0.22, 0.10),
           (H4A, 0.2, 0.08), (H4B, 0.25, 0.09), (H5, 0.5, 0.2),
           (C1, 0.06, 0.08), (C2, 0.06, 0.08), (C3, 0.06, 0.08), (C4, 0.06, 0.08), (C5, 0.05, 0.08)]
SHAKES = [(H1, 10, 0.25), (H2A, 6, 0.14), (H2B, 7, 0.15), (H3, 3, 0.12), (C3, 1, 0.1),
          (H4A, 4, 0.12), (H4B, 5, 0.14), (H5, 6, 0.22), (C1, 1.5, 0.1), (C2, 1, 0.1), (C4, 1, 0.1)]
PUNCH = [(H1, 0.03, 0.22), (H2A, 0.014, 0.14), (H2B, 0.016, 0.15), (H3, 0.01, 0.14), (C3, 0.004, 0.1),
         (H4A, 0.01, 0.12), (H4B, 0.012, 0.14), (H5, 0.02, 0.3), (C5, 0.004, 0.12)]
CAS = [(H1, 16, 0.22), (H2A, 9, 0.12), (H2B, 11, 0.13), (H3, 4, 0.1), (H4A, 12, 0.1), (H4B, 14, 0.12),
       (H5, 9, 0.2)]
WAVES = [  # t0, x, y, speed, ring strength, displacement px, width
    (H1, CX, CY, 2600, 0.55, 26, 70),
    (H2A, 700, STREAM_Y, 2200, 0.18, 12, 50),
    (H2B, 1230, STREAM_Y, 2200, 0.22, 14, 50),
    (H5, CX, CY, 2000, 0.3, 18, 80),
]


def sum_env(lst, t):
    return sum(a * env(t, t0, d) for t0, a, d in lst)


def shake_offset(t):
    amp = sum_env(SHAKES, t)
    if amp < 0.05:
        return 0.0, 0.0, 0.0
    x = math.sin(t * 91.0) * 0.6 + math.sin(t * 157.0 + 1.3) * 0.4
    y = math.sin(t * 103.0 + 2.1) * 0.6 + math.sin(t * 171.0 + 0.4) * 0.4
    r = math.sin(t * 77.0 + 0.7) * amp * 0.02
    return x * amp, y * amp, r


def camera_zoom(t):
    base = 1.0 + 0.07 * (1 - out_cubic(t / DUR)) ** 1.0
    # tension pull before the first hit
    base -= 0.015 * smooth(u(t, 1.0, H1)) * (1 if t < H1 else 0)
    return base + sum_env(PUNCH, t)


# ----------------------------------------------------------------------------- renderer
class Renderer:
    def __init__(self):
        self.as_ = Assets()
        rng = np.random.default_rng(143)
        self.rain = make_rain(rng)
        self.sparks = make_sparks(rng)
        self.bg_cache = {}
        cap = cv2.VideoCapture(os.path.join(A, "background.mp4"))
        self.bg_frames = []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            self.bg_frames.append(fr)
        self.bg_n = len(self.bg_frames)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        dx, dy = xx - CX, yy - CY
        self.r = np.sqrt(dx * dx + dy * dy)
        self.theta = np.arctan2(dy, dx)
        rn = self.r / math.hypot(CX, CY)
        self.vignette = (1 - 0.38 * np.clip(rn - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
        g = np.exp(-(self.r / 520.0) ** 2)
        self.center_glow = (g[..., None] * np.array([0.10, 0.30, 1.0], np.float32)).astype(np.float32)

    # -- background ------------------------------------------------------------
    def background(self, t):
        bt = bg_time(t) * 24.0
        i = int(math.floor(bt))
        f = bt - i
        a = self.bg_frames[i % self.bg_n].astype(np.float32)
        b = self.bg_frames[(i + 1) % self.bg_n].astype(np.float32)
        img = (a * (1 - f) + b * f)[..., ::-1] / 255.0
        # open from black with a lightning flicker
        fade = out_cubic(u(t, 0.0, 0.7))
        flick = 1.0 + 0.9 * env(t, 0.12, 0.05) + 0.6 * env(t, 0.30, 0.05) + 0.4 * env(t, 0.52, 0.06)
        boost = 1.0 + 0.32 * sum_env([(h, 1, 0.16) for h in (H1, H2A, H2B, H4A, H4B, H5)], t) \
            + 0.25 * sum_env([(h, 1, 0.12) for h in (C1, C2, H3, C3, C4, C5)], t)
        tension = 1.0 - 0.18 * smooth(u(t, 1.0, H1)) * (1 if t < H1 else 0)
        img *= fade * flick * boost * tension
        glow_k = 0.10 + 0.16 * env(t, H1, 0.5) + 0.06 * sum_env([(h, 1, 0.3) for h in (H2A, H2B, H5)], t) \
            + 0.07 * smooth(u(t, 0.4, H1)) * (1 if t < H1 else 0)
        img += self.center_glow * glow_k * fade
        return np.ascontiguousarray(img, dtype=np.float32)

    # -- god rays --------------------------------------------------------------
    def rays(self, frame, t):
        k = 0.38 * env(t, H1, 0.55) + 0.25 * smooth(u(t, 0.8, H1)) * (1 if t < H1 else 0) \
            + 0.12 * env(t, H5, 0.6)
        if k < 0.01:
            return
        y0, y1 = 0, H
        th = self.theta[y0:y1]
        r = self.r[y0:y1]
        rot = t * 0.35
        ray = (0.5 + 0.5 * np.cos(th * 18 + rot)) ** 8 + 0.6 * (0.5 + 0.5 * np.cos(th * 11 - rot * 1.4 + 1.0)) ** 10
        ray *= np.exp(-r / 650.0) * np.clip(r / 60.0, 0, 1)
        col = np.array([0.75, 1.0, 0.35], np.float32)
        frame[y0:y1] += (ray * k)[..., None] * col

    # -- rain ------------------------------------------------------------------
    def draw_rain(self, frame, t, layers):
        T = tau(t)
        dt_sub = (tau(t + 0.5 / FPS) - T)  # 180deg shutter in warped time
        for it in self.rain:
            if it["layer"] not in layers:
                continue
            st = rain_state(it, T)
            if st is None:
                continue
            x, y, rz, rx, ry = st
            st2 = rain_state(it, T + dt_sub) or st
            speed = math.hypot(st2[0] - x, st2[1] - y) + abs(st2[2] - rz) * it["m"] * 0.01
            nsub = int(clamp(speed / 2.5, 1, 7))
            states = []
            for k in range(nsub):
                Tk = T + dt_sub * (k / max(nsub - 1, 1) - 0.5) if nsub > 1 else T
                sk = rain_state(it, Tk) or st
                states.append((sk[0], sk[1], it["s"], sk[3], sk[4], sk[2], it["flip"]))
            img = self.as_.kind[it["kind"]]
            L = it["layer"]
            blur, bright = (5.0, 1.05) if L in ("near", "gust") else (0.0, 1.0)
            draw_sprite(frame, img, states, 1.0, blur, bright=bright)

    # -- text ------------------------------------------------------------------
    def logo_state(self, t):
        """Return list of (cx, cy, s, ang, sx, sy) for motion blur, alpha, white-mix."""
        as_ = self.as_
        s_final = LOGO_W / as_.logo_native_w
        S0 = 300.0 / as_.logo_native_w

        def at(t):
            if t < 0.25:
                return None
            if t < H1:
                g = out_cubic(u(t, 0.25, 0.95))
                s = S0 * (0.55 + 0.35 * g)
                s *= 1 - 0.16 * in_cubic(u(t, 1.25, H1))
                tr = 1.0 * smooth(u(t, 0.6, H1))
                ox = tr * math.sin(t * 97) + tr * 0.5 * math.sin(t * 61)
                oy = tr * math.cos(t * 83)
                return (CX + ox, CY + oy, s, 0.0)
            if t < 2.02:
                x = t - H1
                s = S0 * (1 + 0.42 * math.exp(-x / 0.09) * math.cos(2 * math.pi * x / 0.34))
                return (CX, CY, s, 0.0)
            m = in_out_expo(u(t, 2.02, C1 - 0.02))
            x = lerp(CX, LOGO_POS[0], m)
            y = lerp(CY, LOGO_POS[1], m)
            s = lerp(S0, s_final, m)
            if t > C1 - 0.02:
                x2 = t - (C1 - 0.02)
                s *= 1 + 0.06 * math.exp(-x2 / 0.08) * math.cos(2 * math.pi * x2 / 0.25)
            bump = 0.04 * sum_env([(h, 1, 0.12) for h in (H3, H4A, H4B, H5)], t) \
                + 0.02 * sum_env([(h, 1, 0.1) for h in (C2, C3, C4, C5)], t)
            return (x, y, s * (1 + bump), 0.0)

        st = at(t)
        if st is None:
            return None
        sub = []
        n = 8 if 2.02 < t < C1 + 0.02 else 3 if H1 <= t < H1 + 0.2 else 1
        for k in range(n):
            tk = t + (k / max(n - 1, 1) - 0.5) * (0.5 / FPS) if n > 1 else t
            sk = at(tk) or st
            sub.append((sk[0], sk[1], sk[2], sk[3], 1.0, 1.0))
        # glitchy flicker-in
        alpha = out_cubic(u(t, 0.25, 0.55))
        if 0.25 < t < 0.6:
            alpha *= 1.0 if (int(t * 40) % 3) else 0.25
        white = env(t, H1, 0.12) * 0.9 + 0.5 * smooth(u(t, 1.1, H1)) * (1 if t < H1 else 0)
        return sub, alpha, white

    def draw_text(self, t):
        as_ = self.as_
        layer = np.zeros((H, W, 4), np.float32)
        # logo
        ls = self.logo_state(t)
        if ls:
            sub, alpha, white = ls
            blit(layer, as_.logo, sub, alpha)
            if white > 0.01:
                blit(layer, as_.logo_white, sub, alpha * white)

        # THE GOATED — glyphs slam in from the centre outward on the clap
        items = as_.goated.items
        order = sorted(items, key=lambda it: abs(it[3] - 960))
        for rank, (ch, idx, img, gx, gy) in enumerate(order):
            land = C1 + 0.032 * rank
            d = 0.24
            if t < land - d:
                continue
            p = u(t, land - d, land)
            sc = 1 + 1.3 * (1 - p) ** 2
            rot = (1 - out_cubic(p)) * (14 if idx % 2 else -14)
            oy = -50 * (1 - out_cubic(p))
            a = smooth(u(t, land - d, land - d * 0.35))
            if t > land:
                x = t - land
                sc *= 1 - 0.035 * math.exp(-x / 0.06) * math.sin(math.pi * clamp(x / 0.12))
            bump = 0.015 * sum_env([(h, 1, 0.12) for h in (H3, H4A, H4B, H5)], t)
            sub = [(gx, gy + oy, sc * (1 + bump), rot, 1, 1)]
            if p < 1:
                p2 = u(t - 0.5 / FPS, land - d, land)
                sc2 = 1 + 1.3 * (1 - p2) ** 2
                sub.append((gx, gy - 50 * (1 - out_cubic(p2)), sc2, rot, 1, 1))
            blit(layer, img, sub, a)

        # WEEKLY / STREAM — each word slams on an 808
        for wi, (img, img_w, wx, wy, ww, wh) in enumerate(as_.words):
            land = H2A if wi == 0 else H2B
            d = 0.15
            if t < land - d:
                continue
            p = u(t, land - d, land)
            sc = 1 + 2.4 * in_cubic(1 - p) if p < 1 else 1.0
            a = smooth(u(t, land - d, land - d * 0.5))
            sxx = syy = 1.0
            if t >= land:
                x = t - land
                e = math.exp(-x / 0.07)
                sxx = 1 + 0.03 * e * math.cos(2 * math.pi * x / 0.2)
                syy = 1 - 0.04 * e * math.cos(2 * math.pi * x / 0.2)
            bump = 0.015 * sum_env([(h, 1, 0.12) for h in (H3, H4A, H4B, H5)], t) \
                + 0.008 * sum_env([(h, 1, 0.1) for h in (C2, C3, C4, C5)], t)
            # words fly in from opposite sides
            ox = (-1 if wi == 0 else 1) * 260 * in_cubic(1 - p)
            # anchor the squash on the baseline
            cy = wy + wh * 0.5 * (1 - syy)
            sub = []
            n = 6 if p < 1 else 1
            for k in range(n):
                pk = u(t + (k / max(n - 1, 1) - 1.0) * (1.0 / FPS), land - d, land) if n > 1 else p
                sck = 1 + 2.4 * in_cubic(1 - pk)
                oxk = (-1 if wi == 0 else 1) * 260 * in_cubic(1 - pk)
                sub.append((wx + oxk, cy, sck * (1 + bump), 0, sxx, syy))
            blit(layer, img, sub, a)
            wmix = env(t, land, 0.07) * 0.8
            if wmix > 0.01:
                blit(layer, img_w, sub, a * wmix)

        # date — light bar, then a decode/scramble reveal from the centre out
        bar_t0 = H3 - 0.16
        if t > bar_t0:
            bw = (as_.date.width + 46) * out_expo(u(t, bar_t0, H3)) * (1 - in_cubic(u(t, H3 + 0.25, H3 + 0.55)))
            if bw > 1:
                by = int(DATE_Y + 32)
                x0, x1 = int(960 - bw / 2), int(960 + bw / 2)
                layer[by - 1:by + 2, x0:x1, :3] += np.array([*LIME], np.float32) * 0.9
                layer[by - 1:by + 2, x0:x1, 3] += 0.9
                np.clip(layer, 0, 1, out=layer)
        items = as_.date.items
        order = sorted(items, key=lambda it: abs(it[3] - 960))
        rng = np.random.default_rng(int(t * FPS / 3))
        for rank, (ch, idx, img, gx, gy) in enumerate(order):
            start = H3 + 0.010 * rank
            if t < start:
                continue
            p = u(t, start, start + 0.22)
            oy = 22 * (1 - out_cubic(p))
            a = smooth(u(t, start, start + 0.08))
            resolve = start + 0.16
            if t < resolve:
                sc = as_.scramble[rng.integers(len(as_.scramble))]
                blit(layer, sc, [(gx, gy + oy, 1, 0, 1, 1)], a)
            else:
                blit(layer, img, [(gx, gy + oy, 1, 0, 1, 1)], a)

        # kick — icon spins in, URL types on with a cursor
        it0 = C3 - 0.14
        if t > it0:
            p = u(t, it0, it0 + 0.3)
            sc = out_back(p, 2.2) * as_.kick_icon_scale
            rot = -200 * (1 - out_cubic(p))
            blit(layer, as_.kick_icon, [(*as_.kick_icon_pos, sc, rot, 1, 1)], smooth(u(t, it0, it0 + 0.1)))
        kitems = as_.kick.items
        last_x = None
        for (ch, idx, img, gx, gy) in kitems:
            start = C3 + 0.018 * idx
            if t < start:
                continue
            a = smooth(u(t, start, start + 0.05))
            ox = -8 * (1 - out_cubic(u(t, start, start + 0.12)))
            blit(layer, img, [(gx + ox, gy, 1, 0, 1, 1)], a)
            last_x = gx + 9
        typing_end = C3 + 0.018 * (len(as_.kick.items) + 1)
        if last_x is not None and t < typing_end + 0.5:
            on = t < typing_end or int((t - typing_end) * 6) % 2 == 0
            if on:
                ch_ = as_.kick_cursor_h
                y0, y1 = int(KICK_Y - ch_ / 2), int(KICK_Y + ch_ / 2)
                x0 = int(last_x)
                layer[y0:y1, x0:x0 + 3, :3] = LIME
                layer[y0:y1, x0:x0 + 3, 3] = 1

        # glitch slices on the double 808
        g = max(env(t, H4A, 0.05), env(t, H4B, 0.06))
        if g > 0.15:
            rng2 = np.random.default_rng(int(t * FPS) + 7)
            ytop, ybot = int(STREAM_Y - 110), int(STREAM_Y + 110)
            for _ in range(7):
                y0 = rng2.integers(ytop, ybot - 10)
                hgt = rng2.integers(6, 34)
                sh = int(rng2.integers(-22, 22) * g)
                layer[y0:y0 + hgt] = np.roll(layer[y0:y0 + hgt], sh, axis=1)

        # shine sweeps across the lime type on claps
        for t0, dur, k, rows in ((C2, 0.5, 0.85, (STREAM_Y - 110, STREAM_Y + 110)),
                                  (C4, 0.6, 0.85, (LOGO_POS[1] - 60, STREAM_Y + 110)),
                                  (C5, 0.6, 0.6, (LOGO_POS[1] - 60, STREAM_Y + 110))):
            if t0 <= t <= t0 + dur:
                p = in_out_expo(u(t, t0, t0 + dur)) if False else smooth(u(t, t0, t0 + dur))
                y0, y1 = int(rows[0]), int(rows[1])
                xx = self.xx[y0:y1]
                yy = self.yy[y0:y1]
                pos = lerp(300, 1700, p)
                band = np.exp(-(((xx + (yy - STREAM_Y) * 0.45) - pos) / 46.0) ** 2) * k
                band += np.exp(-(((xx + (yy - STREAM_Y) * 0.45) - pos + 95) / 14.0) ** 2) * k * 0.6
                sl = layer[y0:y1]
                sl[..., :3] += band[..., None] * sl[..., 3:4]
                np.minimum(sl[..., :3], sl[..., 3:4], out=sl[..., :3])
        return layer

    # -- particles -------------------------------------------------------------
    def draw_sparks(self, t):
        lay = np.zeros((H, W, 3), np.uint8)
        T = tau(t)
        for sp in self.sparks:
            if sp["type"] == "in":
                if not (sp["ts"] <= t <= sp["te"]):
                    continue
                def pos(tt):
                    q = u(tt, sp["ts"], sp["te"])
                    r = sp["r0"] * (1 - in_cubic(q)) ** 1.0
                    a = sp["ang"] + 0.6 * q
                    return CX + math.cos(a) * r, CY + math.sin(a) * r * 0.75
                p1 = pos(t)
                p0 = pos(t - 0.05)
                a = smooth(u(t, sp["ts"], sp["ts"] + 0.25))
                self._line(lay, p0, p1, sp["col"], a, sp["w"])
            elif sp["type"] == "out":
                dt = t - sp["ts"]
                if dt < 0 or dt > sp["life"]:
                    continue
                def pos(d):
                    k = 3.0
                    e = (1 - math.exp(-k * d)) / k
                    return sp["x"] + sp["vx"] * e, sp["y"] + sp["vy"] * e + 0.5 * sp["g"] * d * d
                p1 = pos(dt)
                p0 = pos(max(dt - 0.035, 0))
                a = (1 - dt / sp["life"]) ** 1.5
                self._line(lay, p0, p1, sp["col"], a, sp["w"])
            else:  # ember
                period = (H + 80) / sp["sp"]
                q = ((T / period) + sp["ph"]) % 1.0
                y = H + 40 - q * (H + 80)
                x = sp["x"] + sp["sway"] * math.sin(T * 0.9 + sp["twp"])
                tw = 0.5 + 0.5 * math.sin(t * sp["tw"] + sp["twp"])
                a = 0.55 * tw * out_cubic(u(t, 0.3, 1.5))
                if a > 0.03:
                    c = tuple(int(255 * v * a) for v in LIME[::-1])
                    cv2.circle(lay, (int(x * 4), int(y * 4)), int(sp["w"] * 4 / 2), c, -1, cv2.LINE_AA, 2)
        f = lay.astype(np.float32) / 255.0
        return f[..., ::-1]

    @staticmethod
    def _line(lay, p0, p1, col, a, w):
        c = tuple(int(255 * v * clamp(a)) for v in col[::-1])
        cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), c,
                 max(1, int(round(w))), cv2.LINE_AA, 2)

    # -- frame -----------------------------------------------------------------
    def frame(self, t):
        fr = self.background(t)
        self.rays(fr, t)
        # shockwave rings (additive, before the mid layer so items read in front)
        for (t0, x, y, spd, ring, disp, wdt) in WAVES:
            dt = t - t0
            if 0 <= dt < 0.9:
                R = spd * dt * (1 - 0.35 * dt)
                fade = (1 - dt / 0.9) ** 2
                rr = np.sqrt((self.xx - x) ** 2 + (self.yy - y) ** 2) if (x, y) != (CX, CY) else self.r
                ringv = np.exp(-((rr - R) / wdt) ** 2) * ring * fade
                fr += ringv[..., None] * np.array([0.7, 1.0, 0.4], np.float32)
        self.draw_rain(fr, t, ("mid", "hero"))

        # text: drop shadow, bloom, then the type itself
        tl = self.draw_text(t)
        a = tl[..., 3]
        if a.max() > 0:
            small = cv2.resize(tl, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
            sh = cv2.GaussianBlur(small[..., 3], (0, 0), 7)
            sh = cv2.resize(sh, (W, H))
            M = np.float32([[1, 0, 0], [0, 1, 10]])
            sh = cv2.warpAffine(sh, M, (W, H))
            fr *= (1 - 0.45 * sh)[..., None]
            glow_k = 0.42 + 0.6 * sum_env([(h, 1, 0.14) for h in (H2A, H2B, H5)], t) \
                + 0.45 * sum_env([(h, 1, 0.12) for h in (H1, H3, H4A, H4B)], t) \
                + 0.25 * sum_env([(h, 1, 0.12) for h in (C1, C2, C3, C4, C5)], t) \
                + 0.08 * math.sin(t * 2 * math.pi / (4 * 0.418)) * smooth(u(t, 8.6, 9.2)) \
                + 0.22 * sum_env([(h, 1, 0.15) for h in HOLD_HITS], t)
            g1 = cv2.GaussianBlur(small[..., :3], (0, 0), 6)
            g2 = cv2.GaussianBlur(small[..., :3], (0, 0), 22)
            glow = cv2.resize(g1 * 0.6 + g2 * 0.9, (W, H))
            fr += glow * glow_k * 0.55
            composite(fr, tl, 0, 0)

        self.draw_rain(fr, t, ("near", "gust"))

        # sparks (rendered with sub-pixel shift; bloom them)
        sp = self.draw_sparks(t)
        if sp.max() > 0:
            g = cv2.GaussianBlur(cv2.resize(sp, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 4)
            fr += sp * 1.2 + cv2.resize(g, (W, H)) * 1.6

        # flash
        fl = sum_env(FLASHES, t)
        if fl > 0.002:
            fr += fl * np.array([0.85, 1.0, 0.8], np.float32)

        # bloom on highlights
        small = cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        hi = np.clip(small - 0.85, 0, None)
        bl = cv2.GaussianBlur(hi, (0, 0), 6)
        fr += cv2.resize(bl, (W, H)) * 0.6

        # camera: zoom, punch, shake (+ rotation)
        z = camera_zoom(t)
        dx, dy, rot = shake_offset(t)
        z += (abs(dx) + abs(dy)) / 900.0
        if abs(z - 1) > 1e-4 or dx or dy or rot:
            M = cv2.getRotationMatrix2D((CX, CY), rot, z)
            M[0, 2] += dx
            M[1, 2] += dy
            fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

        # shockwave refraction
        for (t0, x, y, spd, ring, disp, wdt) in WAVES:
            dt = t - t0
            if 0 <= dt < 0.7:
                R = spd * dt * (1 - 0.35 * dt)
                fade = (1 - dt / 0.7) ** 2
                ddx, ddy = self.xx - x, self.yy - y
                rr = np.sqrt(ddx * ddx + ddy * ddy) + 1e-3
                q = (rr - R) / (wdt * 1.4)
                d = disp * fade * q * np.exp(-q * q) * 2.3
                mx = (self.xx - ddx / rr * d).astype(np.float32)
                my = (self.yy - ddy / rr * d).astype(np.float32)
                fr = cv2.remap(fr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

        # chromatic aberration
        ca = sum_env(CAS, t) + 18 * max(env(t, H4A, 0.04), env(t, H4B, 0.05))
        if ca > 0.4:
            k = ca / 960.0
            for ch, sgn in ((0, 1), (2, -1)):
                M = cv2.getRotationMatrix2D((CX, CY), 0, 1 + sgn * k)
                fr[..., ch] = cv2.warpAffine(np.ascontiguousarray(fr[..., ch]), M, (W, H),
                                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

        fr *= self.vignette
        # fade the very first frames up from black
        fr *= out_cubic(u(t, 0.0, 0.12))
        out = np.clip(fr, 0, 1)
        return (out * 255 + 0.5).astype(np.uint8)


# ----------------------------------------------------------------------------- driver
_R = None


def _init():
    global _R
    _R = Renderer()


def _render_chunk(args):
    i0, i1, path = args
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "4",
           "-pix_fmt", "yuv444p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(_R.frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return path


def make_audio(path):
    """Music from 0:25 plus a soft noise riser into the first 808."""
    sr = 48000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(MUSIC_START), "-t", str(DUR),
                          "-i", os.path.join(A, "music.mp3"), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    music = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    n = int(DUR * sr)
    music = np.pad(music, ((0, max(0, n - len(music))), (0, 0)))[:n]
    tt = np.arange(n) / sr
    # riser: noise through a rising resonant band-pass, swelling into H1, hard cut at the hit
    rng = np.random.default_rng(5)
    noise = rng.standard_normal((n, 2)).astype(np.float32)
    t0, t1 = 0.35, H1 - 0.015
    riser = np.zeros((n, 2), np.float32)
    m = (tt >= t0) & (tt < t1)
    idx = np.where(m)[0]
    fc = 400 * (6000 / 400) ** ((tt[idx] - t0) / (t1 - t0))
    y1 = np.zeros(2)
    y2 = np.zeros(2)
    q = 4.0
    for j, i in enumerate(idx):  # simple state-variable band-pass
        f = 2 * math.sin(math.pi * fc[j] / sr)
        hp = noise[i] - y2 - y1 / q
        y1 = y1 + f * hp
        y2 = y2 + f * y1
        riser[i] = y1
    envr = ((tt - t0) / (t1 - t0)).clip(0, 1) ** 2.2
    riser *= envr[:, None] * m[:, None]
    riser /= (np.abs(riser).max() + 1e-6)
    out = music + riser * 0.16
    fade_in = np.clip(tt / 0.02, 0, 1)
    fade_out = np.clip((DUR - tt) / 0.8, 0, 1) ** 1.5
    out *= (fade_in * fade_out)[:, None]
    peak = np.abs(out).max()
    if peak > 0.89:  # leave ~1 dB of headroom for the AAC encode
        out *= 0.89 / peak
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(sr), "-i", "-",
                    "-c:a", "pcm_s16le", path], input=out.astype(np.float32).tobytes(), check=True)


def render_full(jobs, remux=False):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, "tmp")
    os.makedirs(tmp, exist_ok=True)
    n = jobs * 3
    bounds = [round(i * NFRAMES / n) for i in range(n + 1)]
    chunks = [(bounds[i], bounds[i + 1], os.path.join(tmp, f"c{i:02d}.mp4")) for i in range(n)]
    if not remux:
        with Pool(jobs, initializer=_init) as pool:
            for pth in pool.imap(_render_chunk, chunks):
                print("done", os.path.basename(pth), flush=True)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for c in chunks:
            f.write(f"file '{c[2]}'\n")
    wav = os.path.join(tmp, "audio.wav")
    make_audio(wav)
    final = os.path.join(OUT, "goated_weekly_stream_intro.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "320k", "-shortest", final], check=True)
    print(final)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", nargs="*", type=float)
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--remux", action="store_true", help="re-encode from existing chunks (audio/encode tweaks)")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if args.preview is not None or args.sheet:
        r = Renderer()
        times = args.preview or []
        if args.sheet:
            times = [0.3, 1.0, 1.45, 1.62, 1.8, 2.2, 2.45, 2.7, 3.45, 3.7, 4.2, 4.95,
                     5.3, 5.9, 6.75, 7.0, 7.5, 8.2, 9.0, 11.99]
        ims = []
        for t in times:
            import time
            t0 = time.time()
            im = r.frame(t)
            print(f"t={t:.2f} {time.time() - t0:.2f}s", flush=True)
            if not args.sheet:
                Image.fromarray(im).save(os.path.join(OUT, f"preview_{t:05.2f}.png"))
            ims.append(im)
        if args.sheet:
            th = [cv2.resize(i, (480, 270), interpolation=cv2.INTER_AREA) for i in ims]
            for i, t in zip(th, times):
                cv2.putText(i, f"{t:.2f}s", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            rows = [np.concatenate(th[i:i + 4], 1) for i in range(0, len(th), 4)]
            Image.fromarray(np.concatenate(rows, 0)).save(os.path.join(OUT, "sheet.png"))
        return
    render_full(args.jobs, args.remux)


if __name__ == "__main__":
    main()
