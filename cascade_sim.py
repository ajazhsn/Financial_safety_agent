"""
cascade_sim.py — what the cascade (the app's default mode) would have scored on the held-out test,
computed from the SAVED rag and full results. No API calls, no cost.

Rule (fixed in agent.py before running this): use the rag answer; if it is "unclear", use the full
agent's answer and pay for both. (The held-out set has no "already acted" messages.)

  python cascade_sim.py
  python report.py --data heldout_set.jsonl --a results/test_cascade.jsonl --b results/test_full.jsonl \
                   --names "cascade (app default)" "full agent" --out results/report_cascade_vs_full.md

Caveat for the write-up: this replays saved answers; a live run can differ slightly because the
model is not perfectly deterministic.
"""
import json

load = lambda p: {r["id"]: r for r in map(json.loads, filter(str.strip, open(p, encoding="utf-8")))}
rag, full = load("results/test_rag.jsonl"), load("results/test_full.jsonl")
rows, escalated = [], []
for i, r in rag.items():
    if r["pred"] == "unclear" and i in full:
        f = full[i]
        rows.append({**f, "calls": r["calls"] + f["calls"], "tokens": r["tokens"] + f["tokens"]})
        escalated.append(i)
    else:
        rows.append(r)
with open("results/test_cascade.jsonl", "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
n = len(rows)
print(f"Cascade on {n} messages: escalated {len(escalated)} to the full agent {escalated}")
print(f"Average tokens per message: cascade {sum(r['tokens'] for r in rows) / n:.0f}, "
      f"full agent {sum(full[i]['tokens'] for i in rag if i in full) / n:.0f}")
print("Saved results/test_cascade.jsonl — compare it with report.py (command in this file's header).")
