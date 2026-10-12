# The Haunted Trail: Step 4, Lottie Animations

9 files in `final/halloween-2026/motion/` · developer notes: `motion/hw26-motion-notes.md` ·
previews (GIF + frame strip, played over their real context): `review/motion/`.

## How they were made
- **Hand-authored Bodymovin JSON** from Python (`tools/lottie_kit.py`: layers, shapes, gradients, keyframes).
  `tools/lottie_hw26.py` builds 8 of them; no image generation, so no credits used.
- **G3 walk** (`tools/lottie_g3_walk.py`): the approved map sprite was traced into vector shapes
  (`tools/lottie_trace.py`: edge-preserving smoothing, k-means in Lab colour, per-colour contour tracing) and split into
  parts that move: cloak flap, candy bag, front arm and two boots, plus head and body. Frame 0 matches `map/hw26-g3.png`.
  The face is traced finer than the rest. Backfill shapes hide gaps when parts swing.
- **QA** (`tools/lottie/qa.py`): every file is played with lottie-web 5.12 (SVG renderer, headless Chromium) and checked
  for player errors, size, fps, duration and loop seams (last→first frame difference ≈ one normal frame step);
  fog-drift tile edges were checked too.

| File | KB | Result |
|---|---|---|
| hw26-door-open | 30 | Doorway fills with light from the hinge, zone-tinted bloom and ring, candy burst onto the step, ends clear |
| hw26-house-pulse | 3 | Breathing glow and a soft ring ping, all in the `tint` layer |
| hw26-g3-walk | 92 | Boots alternate under the hem, bag and arm swing, body bobs, cloak sways |
| hw26-pop | 18 | Flash, rays and sparkles behind the candy (14 frames, the closest to 0.45 s) |
| hw26-brew | 36 | Pot rocks, brew bulges and splashes, green puff, item rises out (runtime image slot) |
| hw26-candy-rain | 35 | 40 candies tumbling with sparkles |
| hw26-fog-drift | 68 | Slow wisps drifting both ways, tiles seamlessly |
| hw26-fog-lift | 68 | Opaque fog parting from the centre outward |
| hw26-bats | 32 | Four flapping bats crossing in a seamless loop |

Re-render the QA previews with `npm install --prefix tools/lottie` and then `python tools/lottie/qa.py`.

## Revision: painted Lotties

Feedback: the vector Lotties didn't match the painted art, and the G3 walk was pixelated. Rebuilt with
`tools/lottie_painted.py`; the vector set is archived in `variants/round3/motion_vector_v1/`.

- **New painted assets** (Nano Banana 2, `concepts/round4_motion.json`): bat (3 wing poses), cauldron, green smoke,
  sparkles, fog wisps, doorway light burst, potion drops and bubbles. Cut into sprites by `tools/hw_motion_assets.py`
  (`variants/round4_motion/sprites/`).
- **Candy Rain, door and pop** use the approved Candy (`hw26-candy`).
- **G3 walk:** G3's painted cutout (~3.2× the map size) cut into the same moving parts at 3× and embedded as images, so
  she's sharp at 2× and the art is identical to the PNG. Moving parts have painted-in backfill so no gaps open.
- **Fog lift** breaks the approved shroud into soft-edged pieces that part from the centre.
- **Door opens:** the door swap to "done" now happens under the light burst (marker `swap_to_done`, frame 10).
- Size limit set aside for this pass (see the notes for current sizes). Estimated image spend for the new assets: $0.48.
