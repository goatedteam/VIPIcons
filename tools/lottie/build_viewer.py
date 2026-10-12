#!/usr/bin/env python3
"""Build the self-contained Lottie viewer page (halloween/review/lottie-viewer.html).

Embeds the 9 motion JSON files, the context art they play over (houses, candy icon,
map crops, shop items) and per-animation integration notes into viewer_template.html.
"""
import base64
import io
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(ROOT, "halloween", "final", "halloween-2026")
TPL = os.path.join(os.path.dirname(__file__), "viewer_template.html")
OUT = os.path.join(ROOT, "halloween", "review", "lottie-viewer.html")


def uri(im, fmt="PNG", q=82):
    buf = io.BytesIO()
    if fmt == "JPEG":
        im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True)
    else:
        im.save(buf, "PNG", optimize=True)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def img(rel):
    return Image.open(os.path.join(F, rel)).convert("RGBA")


def images():
    lots = json.load(open(os.path.join(F, "map", "hw26-map-lots.json")))["desktop"]["lots"]
    out = {f"house-{z}": uri(img(f"map/hw26-house-{z}-open.png")) for z in ("z1", "z2", "z3")}
    out["candy"] = uri(img("currency/hw26-candy.png"))
    for i in range(1, 9):
        out[f"item-{i}"] = uri(img(f"shop/hw26-item-{i}.png"))
    m12 = img("map/hw26-map-d-zone12.png")
    out["map-zone"] = uri(m12.crop((1960, 0, 3160, 1200)).resize((720, 720), Image.LANCZOS), "JPEG")
    fogged = img("map/hw26-map-d-zone1.png").crop((1400, 0, 2600, 1200))
    fogged.alpha_composite(img("map/hw26-fog.png").crop((0, 0, 1200, 1200)))
    out["map-fog"] = uri(fogged.resize((720, 720), Image.LANCZOS), "JPEG")
    out["map-sky"] = uri(img("map/hw26-map-d-zone123.png").resize((1440, 450), Image.LANCZOS), "JPEG")
    lot = lots[1]  # G3 at map scale (both @2x): her 256 canvas covers 256 map px, feet on the lot
    out["map-lot"] = uri(img("map/hw26-map-d-zone1.png").crop((lot["x"] - 128, lot["y"] - 238, lot["x"] + 128, lot["y"] + 18)), "JPEG", 88)
    return out


DOOR_SNIPPET = """const anim = structuredClone(doorOpenJson);
const L = n => anim.layers.find(l => l.nm === n);
// per house: z1 [168,204] [100,100] · z2 [167,215] [236,143] · z3 [193,258] [94,93]
L('door').ks.p.k = [167, 215];
L('door_size').ks.s.k = [236, 143];
lottie.loadAnimation({ container, renderer: 'svg', loop: false, animationData: anim })
  .addEventListener('complete', () => showHouse('done'));"""

TINT_SNIPPET = """// recolour the white "tint" layer to the zone colour before loading
const ZONE = { 1: '#FFAA33', 2: '#02DE82', 3: '#FF3B69' };
function tint(json, hex) {
  const rgb = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
  const walk = x => {
    if (Array.isArray(x)) return x.forEach(walk);
    if (!x || typeof x !== 'object') return;
    if ((x.ty === 'fl' || x.ty === 'st') && !x.c.a) x.c.k.splice(0, 3, ...rgb);
    if (x.ty === 'gf') for (let i = 0; i < x.g.p; i++) x.g.k.k.splice(i * 4 + 1, 3, ...rgb);
    Object.values(x).forEach(walk);
  };
  const d = structuredClone(json);
  d.layers.filter(l => l.nm === 'tint').forEach(l => walk(l.shapes));
  return d;
}"""

BREW_SNIPPET = """const anim = structuredClone(brewJson);
const item = anim.assets.find(a => a.id === 'item');   // 192×192 slot
item.u = '/halloween-2026/shop/';
item.p = 'hw26-item-3.png';
item.e = 0;
lottie.loadAnimation({ container, renderer: 'svg', loop: false, animationData: anim });"""

POP_SNIPPET = """// the burst plays behind the icon; scale the icon itself in code
icon.animate(
  [{ transform: 'scale(1)' }, { transform: 'scale(1.45)', offset: 4 / 13 },
   { transform: 'scale(0.92)', offset: 9 / 13 }, { transform: 'scale(1)' }],
  { duration: 433, easing: 'ease-in-out' });"""

ANIMS = [
    dict(id="door-open", file="hw26-door-open.json", title="Door opens", ctx={"under": "house-z1"}, door=True, tint=True, thumbAt=0.45,
         desc="Plays once when a stop is cleared: light fills the doorway as the door swings open, a zone-coloured glow rings out, candy bursts onto the step.",
         spec="320×320 · 1.4 s · one file for all houses",
         notes="<p>Ends fully clear, so swap the house to its <b>done</b> PNG on <code>complete</code>. Before loading, move the <code>door</code> layer and scale <code>door_size</code> to the house's doorway (pick a house above to see each). The bloom and ring are the white <code>tint</code> layer.</p>",
         snippet=DOOR_SNIPPET),
    dict(id="house-pulse", file="hw26-house-pulse.json", title="Current house pulse", ctx={"over": "house-z1", "overFrac": 0.8}, tint=True, thumbAt=0.3,
         desc="Porch-light glow breathing around the current stop, with a soft ring ping. Sits behind the house.",
         spec="400×400 · 1.6 s loop",
         notes="<p>The whole animation is one white layer named <code>tint</code>. Recolour it per zone (#FFAA33 · #02DE82 · #FF3B69) before loading, then place it behind the house PNG.</p>",
         snippet=TINT_SNIPPET),
    dict(id="g3-walk", file="hw26-g3-walk.json", title="G3 walk", ctx={"under": "map-lot"}, thumbAt=0.0,
         desc="Walk cycle traced from the approved map sprite: boots step under the hem, the candy bag and arm swing, the body bobs and the cloak sways.",
         spec="256×256 · 0.6 s loop · frame 0 matches hw26-g3.png",
         notes="<p>Frame 0 matches <code>map/hw26-g3.png</code>, so swap between them freely. Mirror the layer for left-facing walks, as with the PNG. A planted boot slides back 48 px per 0.3 s on the 256 px canvas: at the on-screen 128 px, move G3 along the trail at about <b>80 px/s</b> so her feet don't skate.</p>",
         snippet=""),
    dict(id="pop", file="hw26-pop.json", title="Candy pop", ctx={"over": "candy", "overFrac": 0.5}, thumbAt=0.45,
         desc="Sparkle burst behind the Candy icon when the balance goes up.",
         spec="192×192 · 0.47 s (spec 0.45 s; 14 whole frames)",
         notes="<p>The burst plays behind the icon. The icon's own scale (1 → 1.45 → 0.92 → 1) is applied in code; the same curve is stored on the null layer <code>icon_scale_ref</code> (keys at frames 0, 4, 9, 13).</p>",
         snippet=POP_SNIPPET),
    dict(id="brew", file="hw26-brew.json", title="Cauldron brew", ctx={}, brew=True, thumbAt=0.65,
         desc="Plays on purchase: the pot rocks, the brew bulges and splashes, a green puff, and the bought item rises out.",
         spec="400×400 · 1.5 s · runtime image slot",
         notes="<p>The image asset <code>item</code> (192×192) rises out of the pot between frames 14 and 28. Point it at the bought item's PNG before loading. Pick an item above to preview each one.</p>",
         snippet=BREW_SNIPPET),
    dict(id="candy-rain", file="hw26-candy-rain.json", title="Candy Rain", ctx={"under": "map-zone"}, thumbAt=0.5,
         desc="Plays when the fog meter reaches a tier: about 40 candies tumble down the screen with sparkles.",
         spec="1080×1080 · 3 s",
         notes="<p>Scale to cover the viewport (<code>preserveAspectRatio: 'xMidYMid slice'</code>). Starts and ends empty.</p>",
         snippet="lottie.loadAnimation({ container, renderer: 'svg', loop: false, animationData: rainJson,\n  rendererSettings: { preserveAspectRatio: 'xMidYMid slice' } });"),
    dict(id="fog-drift", file="hw26-fog-drift.json", title="Fog drift", ctx={"under": "map-fog"}, thumbAt=0.0,
         desc="Slow wisps drifting both ways over the fog texture on locked zones.",
         spec="1200×1200 · 8 s loop · tiles both ways",
         notes="<p>Tiles seamlessly in both directions (the pattern repeats every 600 px), so the same file covers any locked zone. Lay it over <code>map/hw26-fog.png</code>, or over the baked shroud in the zone maps.</p>",
         snippet=""),
    dict(id="fog-lift", file="hw26-fog-lift.json", title="Fog lift", ctx={"under": "map-zone"}, thumbAt=0.45,
         desc="Plays when a zone opens: opaque fog parts outward from the centre to reveal the zone.",
         spec="1200×1200 · 1.8 s",
         notes="<p>Starts fully opaque and ends clear. Place it over the zone that is opening, then switch the map to that zone's open state (for example <code>hw26-map-d-zone12.png</code>) underneath before it starts.</p>",
         snippet=""),
    dict(id="bats", file="hw26-bats.json", title="Bats", ctx={"under": "map-sky"}, thumbAt=0.3,
         desc="Four flapping bats crossing the sky in a loop, used in any zone.",
         spec="1920×600 · 6 s loop",
         notes="<p>Matches the desktop map's on-screen size (1920×600). Three or four bats are on screen at a time, and the loop has no visible restart.</p>",
         snippet=""),
]


def main():
    anims = []
    for a in ANIMS:
        path = os.path.join(F, "motion", a["file"])
        data = json.load(open(path))
        a = dict(a, data=data, w=data["w"], h=data["h"], fr=data["fr"], op=int(round(data["op"])),
                 kb=os.path.getsize(path) / 1024, layers=len(data["layers"]),
                 loop=a["id"] in ("house-pulse", "g3-walk", "fog-drift", "bats"),
                 tint=a.get("tint", False), door=a.get("door", False), brew=a.get("brew", False))
        anims.append(a)
    items = [(f"item-{i}", n) for i, n in enumerate(
        ["1 · 10 Free Spins · Limbo", "2 · 25 Free Spins · Any Original", "3 · $5 Casino Bonus", "4 · Rakeback Boost 24h",
         "5 · Pumpkin Avatar Frame", "6 · Ghost Chat Flair", "7 · Bat-Wing Name Color", "8 · Mystery Treat"], 1)]
    payload = json.dumps({"anims": anims, "images": images(), "items": items}, separators=(",", ":"))
    html = open(TPL).read().replace("/*DATA*/null", payload.replace("</", "<\\/"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(html)
    print("wrote", OUT, f"{os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
