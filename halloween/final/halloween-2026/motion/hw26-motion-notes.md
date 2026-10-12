# Haunted Trail: Lottie notes for developers

All files: Bodymovin JSON (v5.7.4), 30 fps, vector only, transparent, under 100 KB. Tested with lottie-web 5.12
(SVG renderer) in Chromium: no errors, correct size and duration, seamless loops where looping.

| File | Size | Length | Loop | Notes |
|---|---|---|---|---|
| hw26-door-open.json | 320×320 | 1.4 s | no | Ends fully clear, so swap to the house "done" PNG on complete |
| hw26-house-pulse.json | 400×400 | 1.6 s | yes | Whole animation is one white layer named `tint` |
| hw26-g3-walk.json | 256×256 | 0.6 s | yes | Frame 0 matches map/hw26-g3.png. Mirror for left-facing, as with the PNG |
| hw26-pop.json | 192×192 | 0.47 s (14 f) | no | Spec says 0.45 s; 14 frames is the closest whole-frame length at 30 fps |
| hw26-brew.json | 400×400 | 1.5 s | no | Item image is swapped in at runtime, see below |
| hw26-candy-rain.json | 1080×1080 | 3 s | no | 40 candies; scale to cover |
| hw26-fog-drift.json | 1200×1200 | 8 s | yes | Tiles in both directions (pattern period 600 px) |
| hw26-fog-lift.json | 1200×1200 | 1.8 s | no | Starts fully opaque, parts from the centre, ends clear |
| hw26-bats.json | 1920×600 | 6 s | yes | 4 bats, 3–4 on screen at a time |

## Zone colour (`tint` layers)
`hw26-door-open` (the bloom and ring behind the doorway) and `hw26-house-pulse` are built in white on layers named
`tint`. Recolour their fills/strokes/gradient colours to #FFAA33 / #02DE82 / #FF3B69 before `loadAnimation`, or with a
CSS filter on the rendered layer.

## Door opens: per-house anchor
One file serves all three house designs. Before loading, patch layer `door` (position) and layer `door_size` (scale):

| House | `door` position | `door_size` scale |
|---|---|---|
| Zone 1 farmhouse (default) | [168, 204] | [100, 100] |
| Zone 2 tree house | [167, 215] | [236, 143] |
| Zone 3 manor | [193, 258] | [94, 93] |

```js
const anim = structuredClone(doorOpenJson);
const L = n => anim.layers.find(l => l.nm === n);
L('door').ks.p.k = [167, 215];
L('door_size').ks.s.k = [236, 143];
```

## Cauldron brew: dropping the item in
Image asset id `item` (192×192, `p: "item.png"`) is shown by layer `item`, which rises out of the pot at frames 14–28.
Point it at the bought item's PNG before loading:
```js
const a = anim.assets.find(a => a.id === 'item');
a.u = '/halloween-2026/shop/'; a.p = 'hw26-item-3.png'; a.e = 0;
```

## Candy pop: icon scale
The burst plays behind the Candy icon. The icon's own scale curve (1 → 1.45 → 0.92 → 1) is stored on the null layer
`icon_scale_ref` (keys at frames 0, 4, 9, 13). Apply it to the icon in code.

## G3 walk: ground speed
While one boot is planted it slides back 48 px per 0.3 s on the 256 px canvas. At the on-screen size (128 px), move G3
along the trail at about **80 px/s** so her feet don't skate.
