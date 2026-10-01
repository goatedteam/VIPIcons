#!/usr/bin/env python3
"""Composite the painted Goated-logo lock onto a chest icon.

  python tools/place_lock.py BASE.png OUT.png --cx 780 --top 1180 --height 400 [--shear 0.15] [--squash 0.88]

The image model will not hold the logo's asymmetric silhouette inside a busy chest
scene, so the lock is painted on its own (reference/brand/goated_lock.png, edited
from the exact logo silhouette) and placed here deterministically. --shear tilts it
to follow the slope of the chest face, --squash foreshortens it horizontally, and a
soft contact shadow seats it on the surface. Coordinates are in BASE pixels.
"""
import argparse
import os
import sys

from PIL import Image, ImageFilter
from rembg import new_session, remove

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "reference", "brand", "goated_lock.png")


def lock_rgba():
    im = remove(Image.open(LOCK).convert("RGB"), session=new_session("birefnet-general"))
    return im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--cx", type=int, required=True, help="lock centre x")
    ap.add_argument("--top", type=int, required=True, help="lock top y")
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--shear", type=float, default=0.0, help="vertical shear (dy per dx)")
    ap.add_argument("--squash", type=float, default=1.0, help="horizontal scale factor")
    a = ap.parse_args()

    base = Image.open(a.base).convert("RGBA")
    lock = lock_rgba()
    w = int(lock.width * a.height / lock.height * a.squash)
    lock = lock.resize((w, a.height), Image.LANCZOS)
    if a.shear:
        extra = int(abs(a.shear) * w)
        sheared = Image.new("RGBA", (w, a.height + extra), (0, 0, 0, 0))
        # y_out = y_in + shear * x  ->  inverse: y_in = y_out - shear * x
        off = extra if a.shear < 0 else 0
        lock = lock.transform(sheared.size, Image.AFFINE, (1, 0, 0, -a.shear, 1, -off), Image.BICUBIC)

    x, y = a.cx - lock.width // 2, a.top
    shadow = Image.new("RGBA", lock.size, (40, 20, 5, 0))
    shadow.putalpha(lock.getchannel("A").point(lambda v: v * 0.45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, a.height // 60)))
    base.alpha_composite(shadow, (x + a.height // 40, y + a.height // 30))
    base.alpha_composite(lock, (x, y))
    base.convert("RGB").save(a.out)
    print("wrote", a.out, lock.size, "at", (x, y), file=sys.stderr)


if __name__ == "__main__":
    main()
