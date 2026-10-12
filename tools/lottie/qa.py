#!/usr/bin/env python3
"""Render every Haunted Trail Lottie with lottie-web and build review previews.

  python tools/lottie/qa.py [name ...]

For each animation: renders all frames (transparent), composites them over their real
context (house, candy icon, map, fog...), and writes an animated GIF plus a frame strip
to halloween/review/motion/. Also checks file size, frame rate and duration against the spec.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(ROOT, "halloween", "final", "halloween-2026")
M = os.path.join(F, "motion")
REV = os.path.join(ROOT, "halloween", "review", "motion")
RENDER = os.path.join(os.path.dirname(__file__), "render.js")
BG = (29, 27, 41, 255)

# file -> (spec size, spec seconds, loops?, context builder name)
SPEC = {
    "hw26-door-open.json": ((320, 320), 1.4, False, "house"),
    "hw26-house-pulse.json": ((400, 400), 1.6, True, "house_behind"),
    "hw26-g3-walk.json": ((256, 256), 0.6, True, "plain"),
    "hw26-pop.json": ((192, 192), 0.45, False, "candy"),
    "hw26-brew.json": ((400, 400), 1.5, False, "plain"),
    "hw26-candy-rain.json": ((1080, 1080), 3.0, False, "map"),
    "hw26-fog-drift.json": ((1200, 1200), 8.0, True, "fog"),
    "hw26-fog-lift.json": ((1200, 1200), 1.8, False, "map"),
    "hw26-bats.json": ((1920, 600), 6.0, True, "map_strip"),
}


def img(rel):
    return Image.open(os.path.join(F, rel)).convert("RGBA")


def context(kind, size):
    w, h = size
    under, over = Image.new("RGBA", size, BG), None
    if kind == "house":  # animation plays over the open house
        under.alpha_composite(img("map/hw26-house-z1-open.png").resize(size))
    elif kind == "house_behind":  # pulse sits behind the house (house drawn over it)
        house = img("map/hw26-house-z1-open.png").resize((w * 320 // 400, h * 320 // 400))
        over = Image.new("RGBA", size, (0, 0, 0, 0))
        over.alpha_composite(house, ((w - house.width) // 2, (h - house.height) // 2))
    elif kind == "candy":
        icon = img("currency/hw26-candy.png").resize((w // 2, h // 2))
        over = Image.new("RGBA", size, (0, 0, 0, 0))
        over.alpha_composite(icon, ((w - icon.width) // 2, (h - icon.height) // 2))
    elif kind == "map":
        m = img("map/hw26-map-d-zone12.png")
        under = m.crop((2560 - 600, 0, 2560 + 600, 1200)).resize(size)
    elif kind == "fog":
        fog = img("map/hw26-fog.png")
        under = img("map/hw26-map-d-zone1.png").crop((1400, 0, 2600, 1200)).resize(size)
        under.alpha_composite(fog.crop((0, 0, 1200, 1200)).resize(size))
    elif kind == "map_strip":
        under = img("map/hw26-map-d-zone123.png").resize((1920, 600))
    return under, over


def tint_copy(data, color):
    """Return a copy whose white 'tint' layers are recoloured (preview of the zone tint)."""
    d = json.loads(json.dumps(data))
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]

    def walk(x):
        if isinstance(x, dict):
            if x.get("ty") in ("fl", "st") and not x["c"].get("a"):
                x["c"]["k"][:3] = rgb
            if x.get("ty") == "gf":
                k = x["g"]["k"]["k"]
                for i in range(x["g"]["p"]):
                    k[i * 4 + 1:i * 4 + 4] = rgb
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for lay in d["layers"]:
        if lay.get("nm") == "tint":
            walk(lay.get("shapes", []))
    return d


def render(data, out_dir, every=1):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()
    r = subprocess.run(["node", RENDER, tmp.name, out_dir, "--every", str(every)], capture_output=True, text=True)
    os.unlink(tmp.name)
    info = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"errors": [r.stderr[-500:]]}
    return info


def main():
    names = sys.argv[1:] or list(SPEC)
    os.makedirs(REV, exist_ok=True)
    report = []
    for fn in names:
        fn = fn if fn.endswith(".json") else fn + ".json"
        size, secs, loops, ctx = SPEC[fn]
        path = os.path.join(M, fn)
        data = json.load(open(path))
        kb = os.path.getsize(path) / 1024
        if fn == "hw26-brew.json":  # drop a real shop item into the placeholder for the preview
            b64 = base64.b64encode(open(os.path.join(F, "shop/hw26-item-3.png"), "rb").read()).decode()
            for a in data["assets"]:
                if a.get("id") == "item":
                    a.update({"p": "data:image/png;base64," + b64, "e": 1, "u": ""})
        if any(l.get("nm") == "tint" for l in data["layers"]):
            data = tint_copy(data, "#FFAA33")  # preview with the Zone 1 colour
        every = 1 if data["op"] <= 60 else (2 if data["op"] <= 120 else 4)
        tmpdir = tempfile.mkdtemp()
        info = render(data, tmpdir, every)
        under, over = context(ctx, (data["w"], data["h"]))
        frames = []
        for f in sorted(os.listdir(tmpdir)):
            fr = under.copy()
            fr.alpha_composite(Image.open(os.path.join(tmpdir, f)).convert("RGBA"))
            if over is not None:
                fr.alpha_composite(over)
            frames.append(fr)
        shutil.rmtree(tmpdir)
        scale = min(1.0, 320 / max(data["w"], data["h"]))
        small = [fr.resize((int(fr.width * scale), int(fr.height * scale)), Image.LANCZOS).convert("RGB") for fr in frames]
        gif = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in small]
        base = os.path.join(REV, fn.replace(".json", ""))
        gif[0].save(base + ".gif", save_all=True, append_images=gif[1:], duration=int(1000 / 30 * every),
                      loop=0, optimize=True)
        k = min(8, len(small))
        idx = [round(i * (len(small) - 1) / (k - 1)) for i in range(k)]
        strip = Image.new("RGB", (small[0].width * k + 6 * (k - 1), small[0].height + 22), (15, 14, 21))
        d = ImageDraw.Draw(strip)
        for j, i in enumerate(idx):
            strip.paste(small[i], (j * (small[0].width + 6), 22))
            d.text((j * (small[0].width + 6) + 4, 5), f"f{i * every}", fill=(215, 255, 0))
        strip.save(base + "_strip.png")
        dur = data["op"] / data["fr"]
        ok = (kb < 100 and data["fr"] == 30 and (data["w"], data["h"]) == size and abs(dur - secs) <= 0.034
              and not info.get("errors"))
        report.append(f"{'OK ' if ok else 'CHK'} {fn:24s} {kb:5.1f} KB  {data['w']}x{data['h']}  {dur:.2f}s "
                      f"(spec {secs}s)  loop={loops}  errors={info.get('errors')}")
        print(report[-1], flush=True)
    return report


if __name__ == "__main__":
    main()
