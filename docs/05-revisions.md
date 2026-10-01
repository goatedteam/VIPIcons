# Step 4: Revisions + Free Spins

Edits applied to the finished icons with Nano Banana Pro as direct image edits (`tools/run_edits.py`,
`edits.json`): the current final is sent as the image to edit, with a Change / Preserve / Constraints brief.

| Bonus | Request | Result |
|---|---|---|
| Instant Rakeback | Remove the imperfections on the rake | Smooth, clean lime head and handle |
| Weekly | Change the lock to the Goated logo | Lock is now the Goated logo, cast in gold (composited, see below) |
| Monthly | Add a lock in the shape of the Goated logo | Goated-logo lock centred on the chest front, replacing the round medallion (composited). Alternate that keeps the medallion: `final/alternates/monthly_lock_with_medallion.png` |
| Reload | Remove the light reflection that gets cut off at the battery's border | Glow kept inside the charge window only; clean outer outline |
| Lossback | Replace the coin with the cash stack; remove imperfections on the arrows | Goated cash stack centred; the same two lime arrows, smoothed |
| Tier Up | Remove the window; add a yellow Goated logo | Window removed; Goated logo decal in brand lime-yellow `#D4FF00` |
| **Free Spins (new)** | Slot machine like the reference, no coins | Lime reel drum with 777 window and lever (`tools/concepts_r3.json`, variant 1). Alternates: Goated gold trim, mid-spin |

## How the logo locks were made

Nano Banana Pro would not hold the logo's **asymmetric** silhouette inside a busy chest scene. Three passes
kept redrawing it as a symmetric fleur, so the lock is made in two deterministic steps instead:

1. **Paint the lock on its own.** The exact logo silhouette (`reference/brand/goated_logo_gold.png`, made
   from the supplied logo) was edited into a bevelled gold lock with a keyhole boss → `reference/brand/goated_lock.png`.
2. **Place it.** The old lock (or the medallion, for Monthly) was removed with a simple edit, then
   `tools/place_lock.py` composites the painted lock with shear and foreshortening to follow the chest face,
   plus a soft contact shadow.

Placements used (2048px canvas):

```bash
python tools/place_lock.py weekly_nolock.png  final/flat/weekly.png  --cx 770 --top 1150 --height 420 --shear 0.12 --squash 0.9
python tools/place_lock.py monthly_nomedal.png final/flat/monthly.png --cx 760 --top 1090 --height 470 --shear 0.2  --squash 0.9
```

## Lessons

- Free-form edits that touch a **specific shape** (logos) need the shape supplied as a finished object, or
  composited. Prompting alone drifts.
- Asking the model to "clean up" a part can make it **redesign** that part. The first Lossback edit turned two
  lime arrows into four green ones. State the count, colour and layout explicitly.
