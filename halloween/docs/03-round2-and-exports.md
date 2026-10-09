# The Haunted Trail: Step 3, Picks, Round 2 and Spec Exports (images)

## Picks (round 1) → what was made

| Design | Pick | Change requested | Source used for export |
|---|---|---|---|
| Map | C | More winding, exactly 12 clearings, spookier | `variants/round2/map/E2` (desktop) · `F1` (mobile) |
| Fog | B | More dispersed, a bit transparent | `variants/round2/fog/1` → alpha 85%, tileable |
| Meter | B | — | `variants/round2/meter/{track,fill}` |
| G3 | C | Witch outfit, more adult | `variants/round2/g3/1` (confirmed) |
| Trail Keeper | B | — | `variants/round1/keeper/B` |
| Goat Kid | A | — | `variants/round1/kid/A` |
| Candy | B | Goated logo orange | `variants/round2/candy/orange_logo` |
| Lantern | A | — | on: `round1/lantern/A` · off: `round2/lantern/off` (edit) |
| Sold-out | A | — | `round1/soldout/A` |
| Houses | Z1 A · Z2 B · Z3 A | — | open = the pick; dark/done = edits of the pick |
| Items | 1A 2A 3B 4A 5C 6B 7B 8C | 1A: rocket → white Goated logo | `round2/item1/logo`, others round 1 |

## How the map was made

The image model kept getting the lot count wrong (13, then 11) and laid the lots out in a line.
So the layout is now fixed in code: `tools/hw_map_guide.py` draws a winding trail with 12 evenly spaced lots
(`reference/map_guide_{d,m}.png`), and that guide is passed to the model as a layout sketch. The same script writes
**`final/halloween-2026/map/hw26-map-lots.json`**, the 12 lot centres in export pixels (desktop 3840×1200,
mobile 1170×3600) with stop and zone numbers, as the spec requires. The guide is neutral (no zone colours),
because tinted bands in the guide got copied into the art as flat colour blocks. Two follow-up edits removed
leftover flat blocks (desktop sky, mobile zone seams).

## Export pipeline (`tools/hw_export.py`)

- Background removal: BiRefNet, then trimmed and placed at the spec size. Houses, characters and G3 are anchored bottom-centre.
- Characters: full, bust and avatar are cut from **one** cutout, so the character is identical in all three. Each character has its own face framing.
- Fog: tiled with an overlap cross-fade (no duplicated content; edge-pixel differences ≤ neighbour differences),
  then converted black → alpha at 85% max opacity. The meter fill uses the same approach horizontally.
- House glow: generated in code, pure white radial falloff, ready to tint.
- Compression: libimagequant (the engine TinyPNG uses), no dithering on soft textures.
- Upscaling: the model's 1K output is Lanczos-upscaled (+ light sharpening) to the export size for the maps and fog.
  **The full-size maps and fog are softer than native art.** If a crisper map is needed, an upscaler or Nano Banana Pro at 4K would help.

## Scenes

| File | Pick | Source |
|---|---|---|
| `modal/hw26-new-zone.png` (1040×560, opaque) | Popup B | `variants/round2/popup/B`, left half kept dark for the headline |
| `shop/hw26-shop.png` (1600×600, opaque) | Shop header A | `variants/round2/shop/A`, left 55% kept dark for the title and Candy balance |

**All 36 spec PNGs are delivered** in `final/halloween-2026/`, plus `map/hw26-map-lots.json`.
