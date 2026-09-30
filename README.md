# Goated VIP Bonus Icons

Icons for the nine VIP bonus/reward types, painted in Goated's house art style with Nano Banana Pro
(`gemini-3-pro-image`) using Goated's own art as style references.

**Final icons → [`final/`](final/)** (transparent PNGs; 512px copies in `final/512/`, flat-background
masters in `final/flat/`). In-card preview: [`review/final_cards.png`](review/final_cards.png).

## Process

| Step | Doc | Output |
|---|---|---|
| 1. Style analysis + 3 concepts per bonus | [`docs/01-style-and-proposals.md`](docs/01-style-and-proposals.md) | — |
| 2. Round 1 variants (A/B/C) | [`docs/02-variants.md`](docs/02-variants.md) | `variants/<bonus>/`, `review/<bonus>.png` |
| 2b. Round 2 variants from feedback | [`docs/03-round2.md`](docs/03-round2.md) | `variants/round2/<bonus>/`, `review/round2/<bonus>.png` |
| 3. Finals | [`docs/04-finals.md`](docs/04-finals.md) | `final/`, `review/final_*.png` |

## Layout

```
reference/   style/ + art/  Goated art used as style references (downscaled)
             vip_tiers/     Goated VIP tier icons; derived/ holds the sheets built from them
tools/       generate.py (Gemini API), run_variants.py, run_finals.py,
             cutout.py (BiRefNet background removal), mock_cards.py, showcase.py
             concepts.json / concepts_r2.json: every prompt used
selections.json   the approved design per bonus (+ edits) that feeds the finals
```
