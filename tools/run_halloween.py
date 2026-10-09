#!/usr/bin/env python3
"""Generate Haunted Trail variants from a halloween/concepts/<round>.json file.

  python tools/run_halloween.py halloween/concepts/round1.json [design | design:V ...]

Writes halloween/variants/<round>/<design>/<V>.png, logs token usage to
halloween/usage_ledger.jsonl, and stops submitting new work as soon as the
estimated remaining credit (tools/spend.py + halloween/budget.json) reaches the
warn threshold. Existing files are skipped unless --force is given.
"""
import io
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "halloween")
os.environ.setdefault("GEN_LEDGER", os.path.join(HW, "usage_ledger.jsonl"))
sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

STOP = threading.Event()


def budget_ok():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "spend.py"),
                        os.path.join(HW, "budget.json"), os.environ["GEN_LEDGER"]],
                       capture_output=True, text=True)
    print(r.stdout.strip(), flush=True)
    return r.returncode != 3


def build(cfg, d, v):
    """Variant keys: subject, or mode="edit" with change; optional refs (overrides the
    design's, in order, so an approved base image can be sent first), prefix, roles."""
    refs = v.get("refs", d.get("refs", []))
    if v.get("mode") == "edit":
        roles = f"REFERENCE IMAGES: {v['roles']}\n" if v.get("roles") else ""
        brief = cfg[d.get("edit_brief", "edit_brief")]
        prompt = brief.replace("{change}", v["change"]).replace("{roles}", roles)
    else:
        layout = cfg["layouts"][v.get("layout", d.get("layout"))]
        prompt = cfg["style_brief"].replace("{subject}", v["subject"]).replace("{layout}", layout)
        if d.get("g3"):
            prompt = cfg["g3_brief"] + prompt
    if v.get("prefix"):
        prompt = v["prefix"] + "\n\n" + prompt
    return prompt, [os.path.join(ROOT, r) for r in refs]


def run(cfg, job, force):
    key, vid, d, v = job
    out = os.path.join(HW, "variants", cfg["round"], key, f"{vid}.png")
    if os.path.exists(out) and not force:
        return f"skip {key}:{vid}"
    if STOP.is_set():
        return f"held {key}:{vid} (budget)"
    prompt, refs = build(cfg, d, v)
    try:
        png = generate(prompt, refs, cfg["model"], v.get("size", d.get("size", "1K")),
                       aspect=v.get("aspect", d.get("aspect", "1:1")), tag=f"{cfg['round']}:{key}:{vid}")
    except Exception as e:  # keep the batch going
        return f"FAIL {key}:{vid} {str(e)[:300]}"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.open(io.BytesIO(png)).save(out, "PNG")
    if not budget_ok():
        STOP.set()
    return f"ok {key}:{vid}"


def load(path):
    """A config may name an "inherit" file whose top-level keys it doesn't define itself."""
    cfg = json.load(open(path))
    if cfg.get("inherit"):
        base = load(os.path.join(os.path.dirname(path), cfg["inherit"]))
        cfg = {**{k: v for k, v in base.items() if k != "designs"}, **cfg}
    return cfg


if __name__ == "__main__":
    cfg = load(sys.argv[1])
    sel = {a for a in sys.argv[2:] if not a.startswith("--")}
    force = "--force" in sys.argv
    jobs = [(k, vid, d, v) for k, d in cfg["designs"].items() for vid, v in d["variants"].items()
            if not sel or k in sel or f"{k}:{vid}" in sel]
    if not budget_ok():
        sys.exit("budget threshold already reached; not generating")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for msg in ex.map(lambda j: run(cfg, j, force), jobs):
            print(msg, flush=True)
    if STOP.is_set():
        print("STOPPED: estimated remaining credit reached the warn threshold")
