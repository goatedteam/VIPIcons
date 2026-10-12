#!/usr/bin/env python3
"""Bake the fog shroud over the locked zones of the Haunted Trail map.

  python tools/hw_zone_shroud.py [--out-dir DIR]

For desktop and mobile, writes three maps: zone 1 open, zones 1+2 open, all open.

1. Seam fix (all variants): the painted maps have hard straight seams where the zones
   meet. The colour step across each seam is removed (per-line mean correction that keeps
   detail), and a soft, noise-broken mist bank is laid along it.
2. Shroud: a dense lilac-grey haze with desaturated fog wisps (from map/hw26-fog.png).
   Its edge is a wide falloff around a boundary that wanders across the map (smooth 1-D
   noise), billowed by 2-D noise, with thin tendrils drifting into the open zone. Open
   lots are always kept clear; locked lots sit under the shroud.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = os.path.join(ROOT, "halloween", "final", "halloween-2026", "map")
# Plain maps (before the seam fix) that the shroud is built on. The files in FINAL are
# replaced by the seam-fixed versions, so the inputs are kept here.
BASE = os.path.join(ROOT, "halloween", "variants", "round3", "map_zones", "base")
HAZE = np.array([66, 60, 88], dtype=np.float32) / 255

# seam positions along the trail axis, measured from column/row colour steps (export px)
SEAMS = {"desktop": [1270, 2509], "mobile": [1221, 2043]}  # re-measured on the 4K re-render


def smooth_noise(h, w, seed, scales=((6, 0.55), (14, 0.3), (32, 0.15))):
    """Sum of upsampled random grids: soft, cloud-like noise in [0, 1]."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for cells, amp in scales:
        gh = max(2, round(cells * h / max(h, w)) + 2)
        gw = max(2, round(cells * w / max(h, w)) + 2)
        grid = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8))
        acc += np.asarray(grid.resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
    acc -= acc.min()
    return acc / acc.max()


def noise1d(n, seed, cells=5):
    rng = np.random.default_rng(seed)
    g = Image.fromarray((rng.random((1, cells + 2)) * 255).astype(np.uint8))
    return np.asarray(g.resize((n, 1), Image.BICUBIC), np.float32)[0] / 255


def tile(tex, size, scale, offset):
    t = tex.resize((max(1, int(tex.width * scale)), max(1, int(tex.height * scale))), Image.LANCZOS)
    out = Image.new("RGBA", (size[0] + t.width, size[1] + t.height))
    for x in range(0, out.width, t.width):
        for y in range(0, out.height, t.height):
            out.paste(t, (x, y))
    ox, oy = offset[0] % t.width, offset[1] % t.height
    return out.crop((ox, oy, ox + size[0], oy + size[1]))


def shroud_rgb(size, seed):
    """Dense lilac-grey haze with two layers of desaturated fog wisps."""
    w, h = size
    fog = Image.open(os.path.join(FINAL, "hw26-fog.png")).convert("RGBA")
    n = smooth_noise(h, w, seed)
    rgb = HAZE * (0.7 + 0.6 * n[..., None])
    base_scale = min(w, h) / 1200
    for scale, off, strength in ((0.9, (0, 0), 0.85), (1.5, (777, 333), 0.55)):
        wisp = np.asarray(tile(fog, size, scale * base_scale, off), np.float32) / 255
        grey = wisp[..., :3].mean(axis=2, keepdims=True)
        col = grey * 0.75 + wisp[..., :3] * 0.25  # mostly desaturated: a shroud, not a rainbow
        col = col * np.array([1.0, 0.96, 1.08])  # keep a lilac cast
        a = wisp[..., 3:] * strength
        rgb = rgb * (1 - a) + col * a
    return np.clip(rgb, 0, 1)


def axis_grids(kind, w, h):
    """(coordinate along the trail, coordinate across it, length across)."""
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return (xx, yy, h) if kind == "desktop" else (yy, xx, w)


def lot_clearance(lots, open_zones, w, h, r):
    """1 everywhere except soft holes around the open lots."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    keep = np.ones((h, w), np.float32)
    for l in lots:
        if l["zone"] <= open_zones:
            d = np.hypot((xx - l["x"]) / (r * 1.7), (yy - l["y"]) / (r * 1.3))
            keep *= np.clip((d - 0.75) / 0.6, 0, 1)
    return keep


def fix_seams(base, kind):
    """Remove the colour step across each seam, keeping the detail, then mist over it."""
    h, w = base.shape[:2]
    along = 1 if kind == "desktop" else 0  # axis the trail runs along
    out = base.copy()
    for s in SEAMS[kind]:
        lo, hi = max(0, s - 300), min(base.shape[along], s + 300)
        prof = base.mean(axis=1 - along)  # per column (desktop) / per row (mobile)
        seg = prof[lo:hi]
        k = np.exp(-0.5 * (np.arange(-150, 151) / 60.0) ** 2)
        k /= k.sum()
        smooth = np.stack([np.convolve(np.pad(seg[:, c], 150, mode="edge"), k, "valid") for c in range(3)], 1)
        corr = smooth - seg  # per-line offset that turns the step into a ramp
        wgt = np.clip(1 - np.abs(np.arange(lo, hi) - s) / 300, 0, 1)[:, None]
        corr = corr * wgt
        if along == 1:
            out[:, lo:hi] += corr[None, :, :]
        else:
            out[lo:hi, :] += corr[:, None, :]
    return np.clip(melt_seams(np.clip(out, 0, 1), kind), 0, 1)


def trail_mask(img):
    """Pale beige trail pixels (and a little around them), so seam blending skips the trail."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    m = ((r > 0.62) & (g > 0.55) & (b > 0.42) & (r - b < 0.28)).astype(np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
                   .filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
    return m


def melt_seams(img, kind, half=70, seed=91):
    """Blend toward a soft (downsampled) copy inside a narrow band around each seam whose
    centre wanders, so the two zones melt together with no straight edge. Skips the trail."""
    h, w = img.shape[:2]
    along_c, _, across_n = axis_grids(kind, w, h)
    pil = Image.fromarray((img * 255).astype(np.uint8))
    soft = np.asarray(pil.resize((w // 4, h // 4), Image.BILINEAR)
                      .filter(ImageFilter.BoxBlur(3)).resize((w, h), Image.BICUBIC), np.float32) / 255
    keep_trail = 1 - trail_mask(img)
    out = img
    for i, s in enumerate(SEAMS[kind]):
        wander = (noise1d(across_n, seed + i, cells=6) - 0.5) * 120
        wander = wander[:, None] if kind == "desktop" else wander[None, :]
        d = np.abs(along_c - s - wander) / half
        wgt = np.clip(1 - d, 0, 1) ** 1.5 * 0.85 * keep_trail
        out = out * (1 - wgt[..., None]) + soft * wgt[..., None]
    return out


def seam_mist(kind, w, h, lots, seed):
    """Soft, uneven mist band along each zone seam (alpha), clear of every lot."""
    along_c, across_c, across_n = axis_grids(kind, w, h)
    n = smooth_noise(h, w, seed, scales=((10, 0.6), (24, 0.4)))
    a = np.zeros((h, w), np.float32)
    for i, s in enumerate(SEAMS[kind]):
        wander = (noise1d(across_n, seed + i, cells=4) - 0.5) * 220
        wander = wander[:, None] if kind == "desktop" else wander[None, :]
        sigma = 120 * (0.7 + 0.6 * n)
        band = np.exp(-0.5 * ((along_c - s - wander) / sigma) ** 2)
        # continuous along the seam but uneven in density, so it reads as a drifting fog bank
        a = np.maximum(a, band * (0.45 + 0.55 * n) * 0.85)
    r = (w if kind == "desktop" else h) * 0.034
    return a * lot_clearance(lots, 3, w, h, r)


def shroud_mask(kind, w, h, lots, open_zones, seed):
    along_c, across_c, across_n = axis_grids(kind, w, h)
    key = "x" if kind == "desktop" else "y"
    last_open = max(l[key] for l in lots if l["zone"] == open_zones)
    first_locked = min(l[key] for l in lots if l["zone"] == open_zones + 1)
    span_axis = w if kind == "desktop" else h
    r = span_axis * 0.034
    gap = first_locked - last_open
    # boundary wanders across the map: never left of just-past the last open lot
    mid = last_open + gap * 0.55
    amp = max(gap * 0.9, span_axis * 0.06)
    wander = (noise1d(across_n, seed, cells=5) - 0.5) * 2 * amp
    wander = wander[:, None] if kind == "desktop" else wander[None, :]
    boundary = mid + wander
    width = max(gap * 1.6, span_axis * 0.09)  # wide falloff
    n = smooth_noise(h, w, seed + 1)
    t = (along_c - boundary) / width + 0.5 + (n - 0.5) * 0.8
    body = np.clip(t, 0, 1)
    body = body * body * (3 - 2 * body)
    # tendrils into the open zone (up to ~1.5 falloff widths), faint
    wisp_n = smooth_noise(h, w, seed + 7, scales=((16, 0.6), (40, 0.4)))
    reach = np.clip((along_c - (boundary - width * 1.5)) / (width * 1.5), 0, 1)
    tendril = np.clip((wisp_n - 0.6) * 2.5, 0, 1) * reach * 0.4
    m = np.maximum(body, tendril)
    return m * lot_clearance(lots, open_zones, w, h, r)


def build(kind, src, lots, open_zones, seed):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    base = fix_seams(np.asarray(im, np.float32) / 255, kind)
    shroud = shroud_rgb((w, h), seed)
    mist = seam_mist(kind, w, h, lots, seed + 50)[..., None]
    base = base * (1 - mist) + shroud * mist
    if open_zones < 3:
        a = (shroud_mask(kind, w, h, lots, open_zones, seed) * 0.97)[..., None]
        base = base * (1 - a) + shroud * a
    return Image.fromarray((base * 255).round().clip(0, 255).astype(np.uint8), "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "halloween", "variants", "round3", "map_zones"))
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    lots = json.load(open(os.path.join(FINAL, "hw26-map-lots.json")))
    for kind, fn, tag in (("desktop", "hw26-map-d.png", "d"), ("mobile", "hw26-map-m.png", "m")):
        for open_zones, name in ((1, "zone1"), (2, "zone12"), (3, "zone123")):
            out = build(kind, os.path.join(BASE, fn), lots[kind]["lots"], open_zones, seed=26)
            dst = os.path.join(a.out_dir, f"hw26-map-{tag}-{name}.png")
            out.save(dst)
            print("wrote", dst, out.size)


if __name__ == "__main__":
    main()
