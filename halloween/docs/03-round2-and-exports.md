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

## Map zone states (approved)

| File | Shows |
|---|---|
| `map/hw26-map-{d,m}-zone1.png` | Zone 1 open (Oct 13); Zones 2–3 under the shroud |
| `map/hw26-map-{d,m}-zone12.png` | Zones 1–2 open (Oct 20); Zone 3 under the shroud |
| `map/hw26-map-{d,m}-zone123.png` | All zones open (Oct 27) |
| `map/hw26-map-{d,m}.png` | Same as zone123 (the spec's single map file), now seam-fixed |

Made by `tools/hw_zone_shroud.py` (no generation): a dense lilac-grey shroud built from the approved fog, with a
billowing, wandering edge and faint tendrils; open lots always clear. The painted zone seams are melted
(colour-step correction, wandering cross-blend that skips the trail, soft mist bank). Inputs are the plain maps in
`variants/round3/map_zones/base/`; `tools/hw_export.py` writes its map output there, so re-running both
scripts reproduces the finals.

## Round 5: Zone 4 haunted house and zone icons (Nano Banana 2, 2K)

| File | Pick | Source |
|---|---|---|
| `map/hw26-house-z4-done.png` (320×320) | House B, castle-manor, lit | `variants/round5/house_z4/B` |
| `map/hw26-house-z4-dark.png` (320×320) | House B, dark, doors shut | `variants/round5/house_z4_dark_fix/B` (edit of the dark state) |
| `zone/hw26-zone1-icon-{512,128}.png` | Pumpkin Fields (from the supplied example) | `variants/round5/icon_pumpkin/A` |
| `zone/hw26-zone2-icon-{512,128}.png` | Hollow Woods B, tree stump | `variants/round5/icon_woods/B` |
| `zone/hw26-zone3-icon-{512,128}.png` | Graveyard B, skull candle | `variants/round5/icon_grave/B` |
| `masters/*@2048.png` | 2048 px transparent masters of all of the above | |

Prompts: `concepts/round5.json`. Boards: `review/round5/`.

## Higher-resolution map and fog meter (Nano Banana 2, 4K)

The maps were 1.6K renders stretched to 3840×1200. They are now re-rendered natively at 4K from the approved maps
(`variants/round2/map/E2_4k.png` 6336×2688, `F1_4k.png` 2048×8256), with the reference sent at full size and an
instruction to keep everything in place. All 12 lots still match `hw26-map-lots.json` exactly. The lots are now drawn
as stone plinths with a lime rim. Exports are downscaled (no longer stretched), and the zone states were rebuilt on
the new base with the seams re-measured. Full-resolution crops: `masters/hw26-map-{d,m}@native.png`.

Fog meter track and fill re-rendered at 4K (`variants/round2/meter/{track,fill}_4k.png`). The fill keeps its
proportions (the core of the band is repeated along the bar, with brightness evened out so no pattern shows).
Masters at 4× the on-screen size: `masters/hw26-meter-{track,fill}@4x.png` (2400×96).

## Round 6: board-style trail map (no fog)

Recreates the art director's reference map (`halloween/reference/map_style_ref.png`: zone signs, numbered
glowing trail, a house at every stop, the castle-manor at the top right) in Goated style, at 4K
(`halloween/concepts/round6.json`, Nano Banana 2, 16:9, 5504×3072).

- `map_board/A–C`: three first passes. A was the strongest; B skipped the number 3 and C ignored "no text".
  All three still had haze in the corners and around the falls.
- `map_board_fix/A_nofog`: A edited to remove all fog, mist and haze. Final **labelled** map.
- `map_board_fix/A_clean`: A_nofog with the numbers and sign lettering removed, so the game can set live
  text. Final **clean** map.

Exports: `trailmap/hw26-trailmap{,-clean}.png` (2752×1536), `masters/hw26-trailmap{,-clean}@native.png`
(5504×3072) and `trailmap/hw26-trailmap-markers.json` (the 12 marker centres measured on the clean map,
as fractions of the image so they hold at any size).
