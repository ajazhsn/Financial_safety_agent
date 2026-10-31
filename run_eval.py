"""
run_eval.py — the ablation table.

Two kinds of score:
  Detection  — is the fraud / not-fraud call right?  (accuracy, precision, recall, false alarms)
  Grounding  — is what the agent TELLS the user true?  A judge model checks every specific
               fact in the explanation and actions (amounts, deadlines, helplines, rules)
               against the message and the RBI/TRAI/NPCI knowledge base.

Usage:
  python run_eval.py --split hard                      # 20 hard cases, all configs, dev model
  python run_eval.py --split hard --judge              # + grounding score
  python run_eval.py --model FINAL --judge             # final numbers for the report (all 60)
  python run_eval.py --configs baseline full --limit 5 # quick smoke test

Text only — no Bodhan calls, so it costs nothing on the Bodhan credit.
Per-message results are saved to results/<config>.jsonl.
"""

import argparse
import json
import os
import time

import clients
from agent import parse_json, run
from rbi_trai_knowledge_base import KNOWLEDGE_BASE

CONFIGS = ["baseline", "rag", "agent", "full"]
KB_TEXT = "\n".join(f"[kb:{e['id']}] {e['text']}" for e in KNOWLEDGE_BASE)


def load_set(path="eval_set.jsonl", split=None):  # split None/"all" = every row
    with open(path, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    return [it for it in items if split in (None, "all") or it.get("split") == split]


# ------------------------------------------------------------------ grounding judge
def judge(message, verdict, model):
    prompt = f"""You are auditing what a fraud-safety assistant told a user.

List every SPECIFIC factual claim in the EXPLANATION and ACTIONS below: numbers, amounts,
deadlines/time limits, helpline numbers, websites, named rules or regulations, named
procedures. Ignore generic advice like "do not share your OTP" or "contact your bank".

For each claim decide: SUPPORTED if it is stated in the USER MESSAGE or in the KNOWLEDGE
BASE; UNSUPPORTED otherwise (even if it might be true in the real world).

Reply with ONLY JSON:
{{"claims": [{{"claim": "...", "supported": true|false}}], "has_specific_action": true|false}}
("has_specific_action" = at least one action is concrete, e.g. a named helpline, portal or
branch visit, rather than only vague advice.)

USER MESSAGE:
{message}

ASSISTANT EXPLANATION:
{verdict.get("explanation", "")}

ASSISTANT ACTIONS:
{json.dumps(verdict.get("actions", []), ensure_ascii=False)}

KNOWLEDGE BASE:
{KB_TEXT}"""
    try:
        return parse_json(clients.llm([{"role": "user", "content": prompt}], model=model,
                                      max_tokens=800).content)
    except Exception as e:
        return {"claims": [], "has_specific_action": False, "judge_error": str(e)}


# ------------------------------------------------------------------ run one config
def evaluate(config, items, model, judge_model=None, privacy=True, tag=""):
    os.makedirs("results", exist_ok=True)
    rows = []
    for it in items:
        clients.reset_usage()
        t0 = time.time()
        try:
            out = run(it["text"], config=config, model=model, privacy=privacy)
            pred = str(out["verdict"].get("fraud", "unclear")).lower()
            err = None
        except Exception as e:
            out, pred, err = {"verdict": {}, "trace": [], "log": []}, "error", str(e)
        row = {"id": it["id"], "split": it.get("split"), "lang": it["lang"], "label": it["label"],
               "pred": pred, "calls": clients.USAGE["calls"],
               "tokens": clients.USAGE["prompt_tokens"] + clients.USAGE["completion_tokens"],
               "seconds": round(time.time() - t0, 1), "error": err,
               "verdict": out["verdict"], "log": out["log"], "hidden": out.get("hidden", [])}
        if judge_model and not err:  # judge tokens are NOT counted in the agent's cost
            row["judge"] = judge(it["text"], out["verdict"], judge_model)
        rows.append(row)
        g = ""
        if row["hidden"]:
            g += " hidden=" + ",".join(h["type"] for h in row["hidden"])
        if "judge" in row:
            bad = sum(not c.get("supported", True) for c in row["judge"].get("claims", []))
            g += f" unsupported={bad}"
        print(f"  [{config}] {it['id']:>4} label={it['label']:<5} pred={pred:<7} calls={row['calls']}{g}")
    with open(f"results/{tag}{config}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def summarize(rows):
    n = len(rows) or 1
    tp = sum(r["label"] == "fraud" and r["pred"] == "yes" for r in rows)
    fp = sum(r["label"] == "legit" and r["pred"] == "yes" for r in rows)
    fn = sum(r["label"] == "fraud" and r["pred"] != "yes" for r in rows)
    tn = sum(r["label"] == "legit" and r["pred"] != "yes" for r in rows)
    s = {
        "accuracy": (tp + tn) / n,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_alarms": fp,
        "missed_frauds": fn,
        "unclear": sum(r["pred"] == "unclear" for r in rows),
        "unclear_genuine": sum(r["label"] == "legit" and r["pred"] == "unclear" for r in rows),
        "genuine_ok": (sum(r["label"] == "legit" and r["pred"] == "no" for r in rows) /
                       max(1, sum(r["label"] == "legit" for r in rows))),
        "errors": sum(r["pred"] == "error" for r in rows),
        "avg_calls": sum(r["calls"] for r in rows) / n,
        "avg_tokens": sum(r["tokens"] for r in rows) / n,
    }
    judged = [r for r in rows if "judge" in r]
    if judged:
        claims = [c for r in judged for c in r["judge"].get("claims", [])]
        unsupported = sum(not c.get("supported", True) for c in claims)
        s["unsupported_per_msg"] = unsupported / len(judged)
        s["fully_grounded"] = sum(all(c.get("supported", True) for c in r["judge"].get("claims", []))
                                  for r in judged) / len(judged)
        fraud_judged = [r for r in judged if r["label"] == "fraud"]  # genuine messages need no helpline
        s["specific_action"] = (sum(bool(r["judge"].get("has_specific_action")) for r in fraud_judged)
                                / len(fraud_judged)) if fraud_judged else 0.0
    return s


def print_table(title, table):
    print(f"\n### {title}")
    has_g = any("fully_grounded" in s for s in table.values())
    head = ("| Config | Acc | Prec | Recall | False alarms | Missed | Unclear | of which genuine | "
            "Genuine called genuine | Err | Calls/msg | Tokens/msg |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    if has_g:
        head += " Unsupported facts/msg | Fully grounded | Specific action (fraud only) |"
        sep += "---|---|---|"
    print(head)
    print(sep)
    for cfg, s in table.items():
        line = (f"| {cfg} | {s['accuracy']:.2f} | {s['precision']:.2f} | {s['recall']:.2f} | "
                f"{s['false_alarms']} | {s['missed_frauds']} | {s['unclear']} | {s['unclear_genuine']} | "
                f"{s['genuine_ok']:.0%} | {s['errors']} | "
                f"{s['avg_calls']:.1f} | {s['avg_tokens']:.0f} |")
        if has_g:
            line += (f" {s.get('unsupported_per_msg', 0):.2f} | {s.get('fully_grounded', 0):.0%} | "
                     f"{s.get('specific_action', 0):.0%} |")
        print(line)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=CONFIGS)
    ap.add_argument("--model", default="DEV", help="DEV, FINAL, or an OpenRouter model name")
    ap.add_argument("--split", default="all", choices=["all", "easy", "hard", "real", "heldout"])
    ap.add_argument("--data", default="eval_set.jsonl", help="eval file, e.g. heldout_set.jsonl")
    ap.add_argument("--judge", action="store_true", help="also score grounding (uses FINAL_MODEL as judge)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-mask", action="store_true", help="switch off privacy masking (ablation)")
    ap.add_argument("--tag", default="", help="prefix for result files, e.g. day2_ (keeps old results)")
    args = ap.parse_args()

    model = {"DEV": clients.DEV_MODEL, "FINAL": clients.FINAL_MODEL}.get(args.model, args.model)
    judge_model = clients.FINAL_MODEL if args.judge else None
    items = load_set(args.data, split=args.split)[: args.limit]
    print(f"Model: {model} | judge: {judge_model} | split: {args.split} | messages: {len(items)} | "
          f"privacy masking: {'off' if args.no_mask else 'on'}")

    all_rows = {cfg: evaluate(cfg, items, model, judge_model, not args.no_mask, args.tag) for cfg in args.configs}

    print_table(f"All ({len(items)} messages)", {c: summarize(r) for c, r in all_rows.items()})
    for split in ("easy", "hard", "real", "heldout"):
        sub = {c: [x for x in r if x["split"] == split] for c, r in all_rows.items()}
        if args.split == "all" and any(sub.values()):
            print_table(f"{split} only", {c: summarize(r) for c, r in sub.items()})

    langs = sorted({r["lang"] for rows in all_rows.values() for r in rows})
    if len(langs) > 1:  # per-language table
        for lang in langs:
            sub = {c: [x for x in r if x["lang"] == lang] for c, r in all_rows.items()}
            print_table(f"language: {lang} ({len(next(iter(sub.values())))} messages)", {c: summarize(r) for c, r in sub.items()})

    with open(f"results/{args.tag}summary.json", "w", encoding="utf-8") as f:
        json.dump({"model": model, "judge": judge_model, "split": args.split, "n": len(items), "privacy": not args.no_mask,
                   "table": {c: summarize(r) for c, r in all_rows.items()}}, f, indent=2)
