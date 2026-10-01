#!/usr/bin/env python3
"""Generate icon variants from a concepts file.

  python tools/run_variants.py                                   # round 1: tools/concepts.json
  python tools/run_variants.py --config tools/concepts_r2.json   # round 2
  python tools/run_variants.py daily:A weekly                    # only the listed ones
Existing files are skipped unless --force is given.

Round 1 files keep concepts under bonus -> A/B/C and write variants/<bonus>/<id>.png.
Later rounds keep them under bonus -> variants -> id and write
variants/<round>/<bonus>/<id>.png. A concept may name a "base" image (the approved
design), which is sent first and gets the file's base_prefix. Ref names resolve as:
  coin            -> reference/style/coin.png
  art:<file>      -> reference/art/<file>
  brand:<file>    -> reference/brand/<file>
  tiers:<set>     -> reference/derived/vip_tiers_<set>.png
"""
import argparse
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND1 = json.load(open(os.path.join(ROOT, "tools", "concepts.json")))


def ref_path(name):
    if name.startswith("art:"):
        return os.path.join(ROOT, "reference", "art", name[4:])
    if name.startswith("brand:"):
        return os.path.join(ROOT, "reference", "brand", name[6:])
    if name.startswith("tiers:"):
        return os.path.join(ROOT, "reference", "derived", f"vip_tiers_{name[6:]}.png")
    return os.path.join(ROOT, "reference", "style", name + ".png")


def jobs(cfg, selectors):
    rnd = cfg.get("round")
    for key, b in cfg["bonuses"].items():
        concepts = b["variants"] if rnd else {v: b[v] for v in "ABC"}
        for vid, c in concepts.items():
            if selectors and key not in selectors and f"{key}:{vid}" not in selectors:
                continue
            out = os.path.join(ROOT, "variants", *([rnd] if rnd else []), key, f"{vid}.png")
            yield key, vid, c, out


def build(cfg, c):
    subject = c["subject"] + (cfg.get("tier_note", "") if c.get("tier") else "")
    prompt = ROUND1["style_brief"].replace("{subject}", subject)
    refs = [ref_path(r) for r in c["refs"]]
    if c.get("base"):
        prompt = cfg["base_prefix"] + prompt
        refs = [os.path.join(ROOT, c["base"])] + refs
    return prompt, refs


def run(cfg, job, force):
    key, vid, c, out = job
    if os.path.exists(out) and not force:
        return f"skip {out}"
    prompt, refs = build(cfg, c)
    try:
        png = generate(prompt, refs, "gemini-3-pro-image", "1K")
    except Exception as e:  # keep the batch going
        return f"FAIL {key}:{vid} {e}"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.open(io.BytesIO(png)).save(out, "PNG")
    return f"ok {out}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("selectors", nargs="*")
    ap.add_argument("--config", default=os.path.join(ROOT, "tools", "concepts.json"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for msg in ex.map(lambda j: run(cfg, j, a.force), list(jobs(cfg, set(a.selectors)))):
            print(msg, flush=True)
