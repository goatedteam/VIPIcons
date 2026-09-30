#!/usr/bin/env python3
"""Generate Goated-style bonus icons with Nano Banana Pro (Gemini image API).

Usage:
  python tools/generate.py --prompt-file prompt.txt --out out.png \
      [--ref img1.png --ref img2.png ...] [--size 1K|2K|4K] [--model gemini-3-pro-image]

Reads GEMINI_API_KEY from the environment. Reference images are downscaled and
composited onto a flat background before upload (the API ignores alpha).
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def encode_ref(path, max_side=768, bg=(208, 208, 208)):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((max_side, max_side))
    flat = Image.new("RGB", im.size, bg)
    flat.paste(im, (0, 0), im)
    buf = io.BytesIO()
    flat.save(buf, "PNG")
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}


def generate(prompt, refs, model, size, aspect="1:1", retries=5):
    parts = [encode_ref(r) for r in refs] + [{"text": prompt}]
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect, "imageSize": size},
        },
    }
    req = urllib.request.Request(
        API.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            for cand in data.get("candidates", []):
                for p in cand.get("content", {}).get("parts", []):
                    blob = p.get("inline_data") or p.get("inlineData")
                    if blob:
                        return base64.b64decode(blob["data"])
            raise RuntimeError("no image in response: " + json.dumps(data)[:800])
        except (urllib.error.URLError, RuntimeError) as e:
            detail = e.read().decode()[:800] if isinstance(e, urllib.error.HTTPError) else str(e)
            if attempt == retries - 1:
                print(f"attempt {attempt + 1} failed: {detail}", file=sys.stderr)
                raise
            # 429s carry "retry in N.Ns"; the per-model quota is per minute
            wait = re.search(r"retry in ([\d.]+)s", detail)
            delay = float(wait.group(1)) + 2 if wait else 2 ** (attempt + 2)
            print(f"attempt {attempt + 1} failed ({getattr(e, 'code', 'error')}), retrying in {delay:.0f}s",
                  file=sys.stderr)
            time.sleep(delay)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--size", default="1K")
    ap.add_argument("--model", default="gemini-3-pro-image")
    a = ap.parse_args()
    png = generate(open(a.prompt_file).read(), a.ref, a.model, a.size)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    Image.open(io.BytesIO(png)).save(a.out, "PNG")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
