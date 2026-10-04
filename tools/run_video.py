#!/usr/bin/env python3
"""Mystery Chest reveal video: keyframes with Nano Banana Pro, motion + audio with Veo 3.1.

  python tools/run_video.py frames [n]      # video/frames/start.png (9:16 outpaint) + reveal_<i>.png
  python tools/run_video.py shot <name> <first.png> [--last <last.png>] --seconds N [--n K]
                                            # -> video/shots/<name>_<k>.mp4

Reads GEMINI_API_KEY. Prompts live in this file.
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from generate import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "video", "frames")
SHOTS = os.path.join(ROOT, "video", "shots")
API = "https://generativelanguage.googleapis.com/v1beta"
VEO = "veo-3.1-generate-preview"

OUTPAINT = """Extend the attached painting to a taller 9:16 portrait canvas. Keep the existing painting exactly as it is (the chest, the pedestal, the lightning, the clouds, the colours and the art style) and centred, and only paint new content above and below it: more stormy slate-navy clouds with forking neon-lime lightning above, and more of the dark cloth-draped pedestal falling into shadow below. Seamless, same hand-painted comic-ink style. No text, no logo."""

REVEAL = """Using the attached painting as the exact style, palette and subject reference, paint the next moment of the same scene, as a 9:16 portrait frame.

CAMERA: pushed in close on the chest: the chest's front fills about 80% of the frame width, seen from slightly below the lid line so we look up a little at what comes out. Same chest, same red-brown wood, light-grey steel corner caps and straps with rivets, brass keyhole plate, gold strap.

ACTION: the lid has burst wide open and tipped back. From inside the chest, a blinding warm ORANGE light floods upward, mixed with the crackling neon-lime (#D4FF00) lightning that still arcs around the chest and over its steel caps. Floating up out of the open chest, centred, hovering just above the rim, is a single JUICE BOX: a classic rectangular drink carton with a bent white-and-orange striped straw poking from its top corner, painted bright orange with a big stylised orange-slice graphic on its front and a couple of cartoon water droplets, no words or letters on it. The juice box glows intensely orange (#FF8A00 to #FFB13B) with a soft orange halo and orange light rays behind it, lit like a legendary loot drop. Lime sparks and a few orange embers swirl up around it.

BACKGROUND: the same dark stormy slate-navy clouds and forking neon-lime lightning, now partly out of focus behind the chest.

STYLE: identical hand-painted 2.5D game art with bold dark ink outlines and cel shading, as in the attached painting; the juice box drawn in the same ink-outlined style. No text, letters, numbers or logos anywhere."""


def outpaint():
    src = os.path.join(ROOT, "poster", "raw", "lightning_2.png")
    png = generate(OUTPAINT, [src], "gemini-3-pro-image", "2K", aspect="9:16")
    out = os.path.join(FRAMES, "start.png")
    Image.open(io.BytesIO(png)).convert("RGB").save(out)
    print("wrote", out, flush=True)
    return out


def reveal(i):
    png = generate(REVEAL, [os.path.join(ROOT, "poster", "raw", "lightning_2.png")],
                   "gemini-3-pro-image", "2K", aspect="9:16")
    out = os.path.join(FRAMES, f"reveal_{i}.png")
    Image.open(io.BytesIO(png)).convert("RGB").save(out)
    print("wrote", out, flush=True)


def _img(path):
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return {"bytesBase64Encoded": base64.b64encode(buf.getvalue()).decode(), "mimeType": "image/png"}


def _call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def veo(prompt, first, last, seconds, out):
    inst = {"prompt": prompt, "image": _img(first)}
    if last:
        inst["lastFrame"] = _img(last)
    body = {"instances": [inst],
            "parameters": {"aspectRatio": "9:16", "durationSeconds": seconds, "resolution": "1080p",
                           "negativePrompt": "text, letters, words, logo, watermark, purple, pink, blue lightning, "
                                             "photorealistic, 3D render, deformed chest, extra chests, people, hands"}}
    op = _call(f"{API}/models/{VEO}:predictLongRunning", body)
    while not op.get("done"):
        time.sleep(10)
        op = _call(f"{API}/{op['name']}")
    if "error" in op:
        raise RuntimeError(json.dumps(op["error"]))
    resp = op["response"]["generateVideoResponse"]
    samples = resp.get("generatedSamples")
    if not samples:
        raise RuntimeError("no video: " + json.dumps(resp)[:800])
    req = urllib.request.Request(samples[0]["video"]["uri"],
                                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        f.write(r.read())
    print("wrote", out, flush=True)


SHOT_PROMPTS = {
    "open": """Hand-painted 2D comic-ink game-art animation, keeping the exact art style, colours and design of the first frame. The camera starts on the wide shot and makes a dramatic, accelerating push-in toward the treasure chest. Neon-lime lightning crackles and forks across the stormy navy sky behind it, flickering and flashing; small lime electric arcs crawl over the chest's steel caps and the pedestal; sparks swirl in the air. The chest shudders and rattles harder and harder as the energy builds, the lime light pulsing out of its lid seam. Then a huge lightning strike hits, the lid bursts open, and blinding warm orange light floods out as a glowing orange juice box starts to rise out of the chest.
Audio: deep rolling thunder, sharp electric crackles and buzzing arcs, a rising whoosh as the camera pushes in, the wooden chest rattling and creaking, a massive thunder-crack as the lid bursts open with a heavy wooden thud and a bright magical shimmer. No music, no voices.""",
    "float": """Hand-painted 2D comic-ink game-art animation, keeping the exact art style, colours and design of the first frame. The glowing orange juice box floats slowly upward out of the open treasure chest and turns gently toward the camera, pulsing with warm orange light, orange light rays sweeping behind it. Neon-lime lightning keeps crackling around the chest and across the stormy sky, lime sparks and orange embers swirl upward around the juice box. The camera drifts in slowly and settles on the juice box as a triumphant hero shot.
Audio: a bright magical shimmer and rising choir-like glow hum as the juice box floats, gentle sparkle chimes, soft electric crackles and distant thunder rumbling, ending on a satisfying sparkling 'ding'. No music, no voices.""",
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--last")
    ap.add_argument("--seconds", type=int, default=8)
    ap.add_argument("--n", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(FRAMES, exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    if a.cmd == "frames":
        n = int(a.args[0]) if a.args else 2
        with ThreadPoolExecutor(n + 1) as ex:
            jobs = [ex.submit(outpaint)] + [ex.submit(reveal, i) for i in range(1, n + 1)]
            [j.result() for j in jobs]
    elif a.cmd == "shot":
        name, first = a.args
        with ThreadPoolExecutor(a.n) as ex:
            jobs = [ex.submit(veo, SHOT_PROMPTS[name], first, a.last, a.seconds,
                              os.path.join(SHOTS, f"{name}_{k}.mp4")) for k in range(1, a.n + 1)]
            [j.result() for j in jobs]
