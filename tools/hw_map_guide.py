#!/usr/bin/env python3
"""Draw the Haunted Trail map layout guides and record the 12 house-lot positions.

  python tools/hw_map_guide.py

Writes halloween/reference/map_guide_{d,m}.png (fed to the image model as a layout
sketch) and halloween/final/halloween-2026/map/hw26-map-lots.json with each lot's
centre in the EXPORT pixel space of the final map (3840x1200 desktop, 1170x3600
mobile), so the lots land where code places the houses.

Guides are drawn at the model's 1K output size; the final maps are cropped to the
export aspect and scaled, using the same transform as tools/hw_export.py.
"""
import json
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")

# model output size per aspect (Nano Banana 2 Lite, 1K)
GEN = {"d": (1584, 672), "m": (512, 2064)}
EXPORT = {"d": (3840, 1200), "m": (1170, 3600)}


def crop_box(kind):
    """Centre-crop of the generated image to the export aspect (desktop keeps the bottom)."""
    gw, gh = GEN[kind]
    ew, eh = EXPORT[kind]
    if gw / gh > ew / eh:
        w = round(gh * ew / eh)
        return ((gw - w) // 2, 0, (gw - w) // 2 + w, gh)
    h = round(gw * eh / ew)
    top = gh - h if kind == "d" else (gh - h) // 2
    return (0, top, gw, top + h)


def serpentine(kind, n=12):
    """Points of a winding trail inside the crop box plus 12 evenly spaced lots on it."""
    x0, y0, x1, y1 = crop_box(kind)
    pts = []
    for i in range(400):
        t = i / 399
        # 3 S-waves with a slower second harmonic so the curve isn't mechanical
        wave = math.sin(t * math.pi * 6 + 0.4) * 0.8 + math.sin(t * math.pi * 2.3 + 1.1) * 0.2
        if kind == "d":  # left -> right
            x = x0 - 20 + t * (x1 - x0 + 40)
            y = y0 + (y1 - y0) * (0.6 + 0.26 * wave)
        else:  # top -> bottom
            y = y0 - 20 + t * (y1 - y0 + 40)
            x = x0 + (x1 - x0) * (0.5 + 0.3 * wave)
        pts.append((x, y))
    # lots spaced evenly by arc length over the trail inside a 7% margin, so no house is clipped
    m = 0.07
    if kind == "d":
        inner = [p for p in pts if x0 + m * (x1 - x0) <= p[0] <= x1 - m * (x1 - x0)]
    else:
        inner = [p for p in pts if y0 + m * (y1 - y0) <= p[1] <= y1 - m * (y1 - y0)]
    seg = [math.dist(inner[i], inner[i + 1]) for i in range(len(inner) - 1)]
    total = sum(seg)
    lots, acc, k = [], 0.0, 0
    targets = [j / (n - 1) * total for j in range(n)]
    targets[-1] -= 1e-6
    for i, s in enumerate(seg):
        while k < n and acc + s >= targets[k]:
            f = (targets[k] - acc) / s if s else 0
            a, b = inner[i], inner[i + 1]
            lots.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
            k += 1
        acc += s
    return pts, lots


def draw(kind):
    gw, gh = GEN[kind]
    im = Image.new("RGB", (gw, gh), (22, 18, 40))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = crop_box(kind)
    # Zones are described in the prompt, not painted here: tinted bands in the guide get
    # copied into the art as flat colour blocks.
    pts, lots = serpentine(kind)
    d.line(pts, fill=(205, 190, 160), width=34 if kind == "d" else 30, joint="curve")
    r = 34 if kind == "d" else 30
    for x, y in lots:
        d.ellipse((x - r * 1.35, y - r, x + r * 1.35, y + r), fill=(120, 100, 80), outline=(240, 240, 240), width=3)
    return im, lots


def main():
    out = {}
    for kind in ("d", "m"):
        im, lots = draw(kind)
        im.save(os.path.join(HW, "reference", f"map_guide_{kind}.png"))
        x0, y0, x1, y1 = crop_box(kind)
        ew, eh = EXPORT[kind]
        sx, sy = ew / (x1 - x0), eh / (y1 - y0)
        out["desktop" if kind == "d" else "mobile"] = {
            "size": [ew, eh],
            "lots": [{"stop": i + 1, "zone": i // 4 + 1, "x": round((x - x0) * sx), "y": round((y - y0) * sy)}
                     for i, (x, y) in enumerate(lots)],
        }
    dst = os.path.join(HW, "final", "halloween-2026", "map", "hw26-map-lots.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w"), indent=2)
    print("wrote guides and", dst)


if __name__ == "__main__":
    main()
