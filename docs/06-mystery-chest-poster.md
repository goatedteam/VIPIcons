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

## Round 2: lightning storm

Feedback: no Goated logo on the chest (use `reference/art/Chest_mystery_glow.png` as the chest), the
GOATED wordmark (`reference/brand/goated_wordmark.png`) unframed in the footer, and no swirls. From five
proposed backgrounds (loot starburst, vault door, spotlight, floating loot, lime lightning storm), the
lightning storm was picked.

Painted with Nano Banana Pro (`gemini-3-pro-image`, 4:5, 2K); prompt in `tools/run_poster.py`.

```
python tools/run_poster.py paint 3                       # -> poster/raw/lightning_<n>.png
python tools/run_poster.py logo poster/raw/lightning_*.png  # -> poster/lightning_<n>.png + _1080x1350
```

Variants: [`poster/lightning_compare.png`](../poster/lightning_compare.png).

## Reveal video

[`video/mystery_chest_reveal.mp4`](../video/mystery_chest_reveal.mp4): 10 s, 1080×1350 (4:5), 30 fps, with sound.
The chosen poster (`poster/raw/lightning_2.png`, no logo) is animated as motion graphics by
`tools/make_reveal.py` (NumPy/PIL frames, encoded with ffmpeg). All sound is synthesized in the same script
and timed to the same event list as the picture.

| Time | Picture | Sound |
|---|---|---|
| 0–5.5 s | Accelerating push-in; 9 lime lightning strikes with flashes and camera shake; sparks; seam glow building; chest rattling faster and faster from 2.9 s | Storm rumble and wind, thunder on every strike, electric hum and crackle, wooden knocks with metal rattle, riser + whoosh |
| 5.5 s | Giant strike, white flash, lid bursts open (cut to the open-chest painting), punch-in | Sub drop, huge thunder crack, lid slam, arc zap |
| 5.6–7.3 s | Juice box shoots up out of the chest (hidden below the rim), squash-and-stretch, orange halo, rays, embers | Shimmer, D-major choir pad, rising whoosh |
| 7.3 s | Box settles; shockwave ring, orange flash, glints | Chime, sparkle arpeggio, soft boom |
| 7.3–10 s | Hero shot: box bobs and glows, sunburst, lightning keeps crackling | Pad, shimmer, distant thunder, final sparkle ding at 9.15 s |

Painted inputs in `video/assets/`: `chest_open.png` (the poster edited to an open, orange-lit chest) and
`juicebox.png` (keyed from `juicebox_ai.jpg`), both from Nano Banana via ElevenLabs. Audio is about -13 LUFS.

```
python tools/make_reveal.py            # -> video/mystery_chest_reveal.mp4 + video/reveal_audio.wav
python tools/make_reveal.py --preview  # a few stills along the timeline
```
