# Mystery Chest Poster

A Goated version of a competitor's 4:5 "mystery box" social post
([`reference/competitor/mystery_box.webp`](../reference/competitor/mystery_box.webp)).

**Final:** [`poster/mystery_chest_1080x1350.png`](../poster/mystery_chest_1080x1350.png) (Instagram 4:5),
[`poster/mystery_chest.png`](../poster/mystery_chest.png) (full 1856×2304), and the painting
without the footer in [`poster/raw/mystery_chest.png`](../poster/raw/mystery_chest.png).

## What changed from the reference

| Reference | Goated version |
|---|---|
| Frosted pink cube with a `?` | Closed Goated wood-and-steel chest (Chest B), painted in the house style: ink outlines, cel shading |
| Plain front | The lock is a gold Goated ram-horn logo with a keyhole; lime light leaks from the lid seam and keyhole |
| Purple/magenta swirls | Neon-lime (`#D4FF00`) dry-brush swirls on deep slate navy, with olive-lime for depth |
| Lavender pedestal | Slate-navy cloth pedestal, lime rim light |
| SHUFFLE.COM pill | Lime Goated glyph + GOATED.COM, composited by `tools/run_poster.py` so the logo is pixel-exact |

## How it was made

Painted with Nano Banana 2 (`gemini-3.1-flash-image`, 4:5, 2K) through ElevenLabs. The repo's own
Gemini key is currently refused by Google with a billing ("dunning") denial, and the ElevenLabs credits only
covered one 2K image. References: Chest B front closed, Chest B right opened, the lime Goated logo, and
the competitor post for layout only. The full prompt is below.

```
python tools/run_poster.py poster/raw/mystery_chest.png   # adds the footer pill -> poster/mystery_chest.png
```

<details><summary>Prompt</summary>

Paint a 4:5 portrait social-media promo poster for Goated, a crypto casino: a MYSTERY CHEST reveal.

Using the attached references:
- Reference 1 and Reference 2 are Goated's own painted treasure chest art. They give the exact chest design AND the art style for the chest: hand-painted 2.5D game art, chunky exaggerated proportions, bold dark ink outlines, cel-shaded value blocks with soft gradient blending, warm red-brown wood planks with painterly grain, cool steel-grey corner bands with rivets, gold trim.
- Reference 3 is the Goated logo: two separate angular ram-horn shapes with a gap between them. It is NOT symmetric: the LEFT horn has a long straight stem that runs far down to a point, the RIGHT horn is shorter. Reproduce this exact silhouette wherever it appears; it must not read as a letter M.
- Reference 4 gives ONLY the composition and layout. Do not copy its colours, its cube, its question mark or its logo.

COMPOSITION (from Reference 4): one CLOSED Goated treasure chest (rounded lid, the design of Reference 1) sits centred slightly above the middle of the frame, front-facing, seen very slightly from above, filling about 40% of the frame width, on a wide, soft, cloth-covered pedestal that fills the lower third and runs off both sides of the frame. Behind and around it, big swirling vortices of thick, dry, textured painterly brush strokes with flecks and splatter fill the whole background, spiralling around the chest, some large blurred strokes in the near foreground corners for depth, with a few tiny star specks. A strong glow behind the chest. The bottom 12% of the frame is calm, dark and out of focus, with nothing in it, reserved for a logo.

THE CHEST: instead of a keyhole plate, its lock is a solid bevelled gold Goated logo (the two ram horns of Reference 3) with a small round keyhole boss set in the gap between the horns. Mysterious neon-lime (#D4FF00) light leaks out of the thin seam between the lid and the body and from the keyhole, casting lime light onto the pedestal. Its contents stay hidden.

PALETTE (Goated brand only): deep near-black slate navy (#0B0F1A to #1A2233) for the darkness; Goated neon lime (#D4FF00) as the dominant glow and swirl colour, with darker olive-lime and acid-green shades for depth; warm gold only on the chest hardware. The pedestal is dark slate-navy fabric with lime rim light from the chest. The background and pedestal are softer and more atmospheric, like game key-art, so the ink-outlined chest pops in front. No purple, magenta, pink or blue anywhere.

No text, letters or numbers anywhere in the image. One chest only.
</details>
