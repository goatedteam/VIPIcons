# Goated Halloween Icons

Halloween-themed icons for Goated, painted in the same house art style as the
[VIP bonus icons](../README.md): hand-painted 2.5D, bold dark ink outlines,
cel shading, the Goated ram-horn logo and the neon-lime accent (`#D4FF00`).
Here it's pushed toward Halloween with pumpkin orange, deep purple and
ghostly greens.

## Process

The same workflow as the VIP set:

| Step | Output |
|---|---|
| 1. Concept proposals, three per icon | `docs/01-proposals.md` |
| 2. Basic variants, up to three per icon | `variants/<icon>/`, `review/` |
| 3. Selection and finals | `final/` |

## Layout

```
halloween/
  docs/        proposals and per-round notes
  concepts/    prompt files (one JSON per round)
  reference/   Halloween-specific references; Goated style refs come from ../reference
  variants/    generated variants per round
  review/      in-context review boards
  final/       transparent PNG masters, final/512/ (web size), final/flat/ (flat background)
```

Generation uses the shared tooling in [`../tools`](../tools): Nano Banana Pro
(`gemini-3-pro-image`) via the Google AI Studio API, and BiRefNet for background removal.
