"""compare_runs.py — what changed between two eval runs, and why the agent said what it said.
  python compare_runs.py results/full.jsonl results/day2_full.jsonl
Prints every message whose answer changed, then the explanation behind each mistake in the new run."""
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, filter(str.strip, f))}


old, new = load(sys.argv[1]), load(sys.argv[2])
print(f"old: {len(old)} messages   new: {len(new)} messages\n")
print("CHANGED ANSWERS (label | old -> new)")
for i, r in new.items():
    if i in old and old[i]["pred"] != r["pred"]:
        good = lambda p: (p == "yes") == (r["label"] == "fraud") and p != "unclear"
        flag = "better" if good(r["pred"]) and not good(old[i]["pred"]) else "WORSE" if good(old[i]["pred"]) and not good(r["pred"]) else ""
        print(f"  {i:<7} {r['label']:<6} {old[i]['pred']:<8} -> {r['pred']:<8} {flag}")
print("\nMISTAKES IN THE NEW RUN")
for i, r in new.items():
    wrong = (r["label"] == "fraud" and r["pred"] != "yes") or (r["label"] == "legit" and r["pred"] != "no")
    if wrong:
        v = r.get("verdict", {})
        print(f"- {i} [{r['label']}] said {r['pred']}: {v.get('fraud_type', '')}\n    {str(v.get('explanation', ''))[:260]}")
