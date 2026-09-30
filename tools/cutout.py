#!/usr/bin/env python3
"""Remove the flat background from generated icons (BiRefNet via rembg).

  python tools/cutout.py in.png [in2.png ...] --out-dir DIR [--trim]
Writes DIR/<same name>.png as RGBA. --trim crops to the alpha bounding box and
re-centres on a square transparent canvas with 6% padding.
"""
import argparse
import os

from PIL import Image
from rembg import new_session, remove


def trim_square(im, pad=0.06):
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    im = im.crop(box)
    side = int(max(im.size) * (1 + 2 * pad))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--trim", action="store_true")
    a = ap.parse_args()
    session = new_session("birefnet-general")
    os.makedirs(a.out_dir, exist_ok=True)
    for path in a.inputs:
        out = remove(Image.open(path).convert("RGB"), session=session)
        if a.trim:
            out = trim_square(out)
        dst = os.path.join(a.out_dir, os.path.basename(path))
        out.save(dst, "PNG", optimize=True)
        print("wrote", dst, out.size, flush=True)


if __name__ == "__main__":
    main()
