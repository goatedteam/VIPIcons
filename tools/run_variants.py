#!/usr/bin/env python3
"""Generate the basic A/B/C variants for every bonus in tools/concepts.json.

  python tools/run_variants.py                  # all bonuses, all concepts
  python tools/run_variants.py daily:A weekly   # only the listed ones
Existing files are skipped unless --force is given.
"""
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "tools", "concepts.json")))


def jobs(selectors):
    for key, b in CFG["bonuses"].items():
        for v in "ABC":
            if selectors and key not in selectors and f"{key}:{v}" not in selectors:
                continue
            yield key, v, b[v]


def run(job, force):
    key, v, c = job
    out = os.path.join(ROOT, "variants", key, f"{v}.png")
    if os.path.exists(out) and not force:
        return f"skip {out}"
    refs = [os.path.join(ROOT, "reference", "style", r + ".png") for r in c["refs"]]
    prompt = CFG["style_brief"].replace("{subject}", c["subject"])
    try:
        png = generate(prompt, refs, "gemini-3-pro-image", "1K")
    except Exception as e:  # keep the batch going
        return f"FAIL {key}:{v} {e}"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.open(io.BytesIO(png)).save(out, "PNG")
    return f"ok {out}"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    with ThreadPoolExecutor(max_workers=6) as ex:
        for msg in ex.map(lambda j: run(j, force), list(jobs(set(args)))):
            print(msg, flush=True)
