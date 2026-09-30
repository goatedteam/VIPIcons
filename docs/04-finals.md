# Step 3: Final Icons

Selections: `selections.json` · Generator: `tools/run_finals.py` · Previews: `review/final_cards.png`, `review/final_before_after.png`

| Bonus | Approved design | Final changes requested |
|---|---|---|
| Daily Bonus | Round 2 #3: Goat Bank | none |
| Weekly Bonus | Round 2 #2: Classic chest, overflowing, right view | none |
| Monthly Bonus | Round 2 #2: Royal chest (mirrored), richer hoard | none |
| VIP Bonus | Round 2 #1: Crown on velvet cushion | none |
| Instant Rakeback | Round 2 #1: Lime rake, no coins | none |
| Lossback | Round 2 #3: Re-roll arrow | die replaced with a small Goated coin |
| Reload | Round 2 #2: Battery with charge bars | none |
| Level Up Bonus | Round 2 #2: Winged rank shield | none |
| Tier Up Bonus | Round 2 #2: Goated rocket | all gems/tier icons removed (plain glass porthole) |

## How the finals were made

1. The approved variant was sent to **Nano Banana Pro** (`gemini-3-pro-image`) as the master reference, alongside the Goated style references, with a brief to keep the design and polish the linework, shading and ram-horn glyphs. For Lossback and Tier Up, `selections.json` replaces the concept subject so the removed objects don't creep back in.
2. Rendered at **2048×2048** on flat `#D0D0D0` → `final/flat/<bonus>.png`.
3. Background removed with **BiRefNet** (`birefnet-general`), trimmed and re-centred on a square canvas with 6% padding → `final/<bonus>.png` (RGBA, about 2000px).
4. 512×512 copies for web use → `final/512/<bonus>.png`.

## Deliverables

| File | Use |
|---|---|
| `final/<bonus>.png` | Transparent PNG master (about 2000px square) |
| `final/512/<bonus>.png` | Transparent PNG, 512×512, ready for the modal |
| `final/flat/<bonus>.png` | 2048×2048 on flat grey, if you'd rather do your own background removal |

## Re-running

```bash
export GEMINI_API_KEY=...        # Google AI Studio key
pip install pillow "rembg[cpu]"
python tools/run_finals.py selections.json lossback   # re-roll one icon
python tools/showcase.py --current-dir <folder with current live cards>
```

Each generation is a fresh sample, so re-running gives a slightly different render of the same design.
The key's quota for Nano Banana Pro is 20 requests per minute; `generate.py` waits and retries on 429.
