# Step 2: Basic Variants (A / B / C)

Each bonus got one basic variant per concept from Step 1, 27 images in total.

- **Model:** Nano Banana Pro (`gemini-3-pro-image`) via the Google AI Studio API
- **Output:** 1024×1024 on a flat `#D0D0D0` background (`variants/<bonus>/<A|B|C>.png`)
- **Style input:** Goated reference art in `reference/style/` (coin, lime chip, money bag, chest, calendar, gift box, envelope), chosen per concept
- **Prompts:** `tools/concepts.json` (a shared style brief plus a subject line per concept)

The review boards in `review/<bonus>.png` show the **current live card** next to A/B/C, with each variant
background-removed and placed inside a replica of the VIP modal card. That's how they'll actually be seen.

| Bonus | A | B | C |
|---|---|---|---|
| Daily | Daily Coin Pouch | Tear-off Day Calendar | Morning Mug of Coins |
| Weekly | Classic Goated Chest | Week Calendar Strip | Goated Gift Box |
| Monthly | Royal Vault Chest | Month Calendar + Wax Seal | Bank Vault Door |
| VIP | Goated Crown | VIP Invitation Envelope | Crowned VIP Chip |
| Instant Rakeback | Goated Rake | Croupier's Table Rake | Coin Magnet |
| Lossback | Return Arrow + Coins | Boomerang | Life Ring |
| Reload | Refresh Ring + Goated Coin | Coin Battery | Chip Rack Refill |
| Level Up | Power Bolt | Rank Shield | Level-Up Potion |
| Tier Up | Lime Arrow + Coin Stacks | Coin Staircase | Goated Rocket |

## Observations to carry into the finals

- Small **detached effects** (the lime sparks on Level Up A, the motion streaks on Rakeback C, the battery sparks on Reload B) are dropped by background removal. The final prompt keeps effects touching the main object.
- The **ram-horn glyph** drifts slightly between images. The final pass uses the coin reference to lock it.
- **Hierarchy:** Daily A (pouch) → Weekly A (chest) → Monthly A (royal vault chest) reads as a clear small → medium → large ladder if you want the time-based bonuses to feel like a family.
