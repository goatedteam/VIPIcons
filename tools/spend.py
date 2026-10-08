#!/usr/bin/env python3
"""Total the estimated spend in a usage ledger against a budget.

  python tools/spend.py halloween/budget.json halloween/usage_ledger.jsonl

Exits with code 3 when the estimated remaining balance is at or below the
budget's warn threshold, so batch scripts can stop and alert.
"""
import json
import sys


def cost(rec, rates):
    r = rates.get(rec["model"])
    if not r:
        return 0.0
    u = rec["usage"]
    out = {d["modality"]: d["tokenCount"] for d in u.get("candidatesTokensDetails", [])}
    img_out = out.get("IMAGE", 0)
    txt_out = u.get("candidatesTokenCount", 0) - img_out  # includes any thinking text
    return (u.get("promptTokenCount", 0) * r["input"] + img_out * r["output_image"]
            + max(txt_out, 0) * r["output_text"]) / 1e6


def main():
    budget = json.load(open(sys.argv[1]))
    recs = [json.loads(line) for line in open(sys.argv[2]) if line.strip()]
    spent = sum(cost(r, budget["rates_per_1m_tokens"]) for r in recs)
    left = budget["start_balance_usd"] - spent
    print(f"calls={len(recs)} est_spent=${spent:.2f} est_remaining=${left:.2f}")
    if left <= budget["warn_when_remaining_usd"]:
        print("WARNING: estimated remaining credit is at or below the warn threshold")
        sys.exit(3)


if __name__ == "__main__":
    main()
