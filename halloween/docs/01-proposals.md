# The Haunted Trail: Step 1, Concept Proposals (images)

Source: `docs/Haunted_Trail_Asset_List.pdf` (36 PNG · 9 Lottie · 8 sounds). **This step covers the 36 PNGs only.**

**Model:** Nano Banana 2 Lite (`gemini-3.1-flash-lite-image`) via the Google AI Studio API.
**Style:** Goated house style (hand-painted 2.5D, bold ink outlines, cel shading), with Goated's art passed as style
references. Halloween palette: night purples and slate navies, the three zone colours (Pumpkin `#FFAA33`,
Hollow Woods `#02DE82`, Graveyard `#FF3B69`) and Goated lime `#D4FF00` as the brand accent. Spooky-cute, never gory.
**G3:** every G3 image passes `reference/g3_reference.png` first, with the instruction to keep her hair, horns
(shape and placement), face and proportions exactly. She is always shown modestly dressed for the event.

## How the 36 files map to designs

| Spec file(s) | Count | Made from |
|---|---|---|
| `map/hw26-map-{d,m}` | 2 | One map design; mobile is a vertical re-layout of the approved desktop map |
| `map/hw26-fog` | 1 | Painted fog, then made seamlessly tileable in code |
| `map/hw26-house-z{1,2,3}-{dark,open,done}` | 9 | One design per zone; the other two states are image edits of the approved one, so the house never changes |
| `map/hw26-house-glow` | 1 | **Drawn in code**: pure white radial gradient (exact, tint-ready) |
| `map/hw26-g3` | 1 | G3 design |
| `currency/hw26-candy` | 1 | Candy design |
| `meter/hw26-meter-{track,fill}` | 2 | Meter design; strips cut and made horizontally tileable in code |
| `meter/hw26-lantern-{off,on}` | 2 | One lantern; "off" is an edit of "on" |
| `char/hw26-keeper-{full,bust,avatar}` | 3 | One full-body design; bust and avatar are re-framed from it so he stays identical |
| `char/hw26-kid-{full,bust,avatar}` | 3 | Same approach as the Keeper |
| `modal/hw26-new-zone` | 1 | **Round 2**: needs the approved Trail Keeper |
| `shop/hw26-shop` | 1 | **Round 2**: needs the approved Goat Kid |
| `shop/hw26-item-{1–8}` | 8 | One design each |
| `shop/hw26-sold-out` | 1 | One design |

## Concepts (three per design → variants A/B/C)

| Design | A | B | C |
|---|---|---|---|
| **Map** | Winding dirt trail left → right through moonlit pumpkin farmland, twisted woods and a graveyard, with 12 empty clearings | Board-game feel: trail of glowing stepping stones, slightly top-down, with clearer lots | Big-moon panorama: layered hill silhouettes, a faint lime glow along the trail |
| **Fog** | Soft, dense purple-grey cloud banks | Layered wisps with darker swirls | Thick rolling fog with faint lime-tinted edges |
| **House Z1** (pumpkin patch) | Red-and-cream farmhouse, pumpkins on the porch, scarecrow | Cottage built into a giant pumpkin | Wooden farmhouse with hay bales and a crooked windmill |
| **House Z2** (woodland) | Crooked log cabin, mossy roof, glowing mushrooms | Cabin carved into a hollow tree trunk | Stone-and-timber cottage, crooked chimney, hanging lanterns |
| **House Z3** (graveyard) | Tall gothic manor with spires behind an iron fence | Mausoleum-style crypt house with stone angels | Haunted Victorian house with a tower and broken shutters |
| **G3 on map** | Purple hooded cloak, hood down, orange candy bag | Witchy cloak with lime trim, pointed hood down | Hood up, with horn-holes so her horns come through |
| **Candy** | Purple wrapped sweet with lime twisted ends | Round purple candy with lime twists and a ram-horn emboss | Glossy purple hard candy, lime twists, slight tilt |
| **Fog meter** | Wrought-iron rail with rivets, lime mist fill | Gnarled wooden rail with vines | Carved stone rail with skull studs (cute) |
| **Lantern** | Black wrought-iron hanging lantern | Square cage lantern with a bat-wing finial | Round cage lantern with a tiny jack-o'-lantern inside |
| **Trail Keeper** | Elder goat with a long white beard, hood up, horns curling out of the hood | Taller, spectral goat with glowing lime eyes (spooky-cute) | Robed goat with a crooked staff, the lantern hanging from it |
| **Goat Kid** | Little goat girl standing upright, oversized witch hat | Chubbier toddler goat, hat slipping over one eye | Freckled goat kid, tiny horns poking through the hat brim |
| **Item 1** · 10 FS Limbo | 3 glowing chips with a rocket emblem | Chips stacked like a rocket launch pad | Chips with the rocket emblem and lime glow trails |
| **Item 2** · 25 FS Any Original | Chip pile spilling from a pumpkin bucket | Overflowing jack-o'-lantern bucket, chips cascading | Bucket on its side, chips fanning out |
| **Item 3** · $5 Casino Bonus | Gold coin with a carved jack-o'-lantern face | Coin face glowing orange from inside | Coin standing on edge with a little pumpkin stem on top |
| **Item 4** · Rakeback Boost 24h | Potion bottle, lime glow, up-arrow label | Round flask with a bubbling lime potion and an arrow-shaped stopper | Tall vial with a lime up-arrow rising in the bubbles |
| **Item 5** · Pumpkin Avatar Frame | Pumpkin-vine ring with leaves, empty centre | Vine ring with tiny pumpkins at four points | Twisted vine ring with curling tendrils |
| **Item 6** · Ghost Chat Flair | Cute ghost peeking out of a speech bubble | Ghost wrapped around the bubble | Ghost popping up from behind the bubble |
| **Item 7** · Bat-Wing Name Color | Paint pot with bat wings, purple drips | Paint pot flying on bat wings | Paint pot with a brush and bat wings |
| **Item 8** · Mystery Treat | Candy-stripe gift box with a "?" tag | Box with a "?" tag, lid lifting slightly | Box tied with a lime ribbon and a "?" tag |
| **Sold-out stamp** | Grey empty cauldron tipped over | Tipped cauldron with a crack | Tipped cauldron with the ladle beside it |

The "?" tag on item 8 is the one place text-like art is needed. The spec says "no text in the art", but the "?"
is part of the object, so it stays.
