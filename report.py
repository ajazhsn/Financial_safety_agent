"""
report.py — turn saved evaluation results into the tables for the write-up. No API calls, no cost.

  python report.py --data heldout_set.jsonl --a results/test_baseline.jsonl --b results/test_full.jsonl

Prints (and saves to results/report.md):
  1. Detection with 95% Wilson confidence intervals: scams caught, genuine called genuine, false alarms,
     scams called genuine (the dangerous error), overall and per language.
  2. A paired comparison of the two configs on the SAME messages (who was right when they disagreed)
     with an exact sign test, so a one-message difference is not reported as a win.
  3. Invented facts: how often the advice names a phone number, helpline or website that appears neither in
     the message nor in the knowledge base. Deterministic, free, reproducible.
"""

import argparse
import json
import math
import re
from collections import defaultdict

from privacy import PHONE_RE, URL_RE

AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s?[\d,]+(?:\.\d+)?", re.I)

try:
    from rbi_trai_knowledge_base import KNOWLEDGE_BASE
    KB_TEXT = "\n".join(e["text"] for e in KNOWLEDGE_BASE)
except Exception:  # run without the KB: only the message counts as support
    KB_TEXT = ""
    print("(rbi_trai_knowledge_base.py not found: facts are checked against the message only)")

SHORT_CODE_RE = re.compile(r"(?<![\d,.])(1[0-9]{3,5})(?![\d,.]|\s?(?:%|rs|₹))", re.I)  # 1930, 1947, 14440, 155260
TOLL_RE = re.compile(r"(?<!\d)1800[\s-]?(?:\d[\s-]?){6,8}(?!\d)")  # any grouping of a toll-free number
digits = lambda s: re.sub(r"\D", "", s)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - m), min(1.0, c + m)


def fmt(k, n):
    p, lo, hi = wilson(k, n)
    return f"{p:.0%} ({k}/{n}; 95% CI {lo:.0%}-{hi:.0%})"


def load(path):
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, filter(str.strip, f))}


def detection(rows):
    fr = [r for r in rows if r["label"] == "fraud"]
    lg = [r for r in rows if r["label"] == "legit"]
    return {
        "Scams caught (says scam)": (sum(r["pred"] == "yes" for r in fr), len(fr)),
        "Scams called genuine (dangerous)": (sum(r["pred"] == "no" for r in fr), len(fr)),
        "Genuine called genuine": (sum(r["pred"] == "no" for r in lg), len(lg)),
        "False alarms (genuine called scam)": (sum(r["pred"] == "yes" for r in lg), len(lg)),
        "Genuine answered 'not sure'": (sum(r["pred"] == "unclear" for r in lg), len(lg)),
    }


def correct(r):
    return r["pred"] == ("yes" if r["label"] == "fraud" else "no")


def sign_test(better, worse):
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def invented(row, message):
    """Contacts / websites in the advice that are in neither the message nor the knowledge base."""
    v = row.get("verdict") or {}
    text = " ".join([str(v.get("explanation", ""))] + [str(a) for a in v.get("actions", [])])
    support_digits, support_low = digits(message + " " + KB_TEXT), (message + " " + KB_TEXT).lower()
    bad = []
    plain = AMOUNT_RE.sub(" ", text)  # "Rs 1500" is an amount, not a helpline
    tolls = TOLL_RE.findall(plain)
    plain = TOLL_RE.sub(" ", plain)  # so its first four digits are not read as a short code
    for m in tolls + PHONE_RE.findall(plain) + SHORT_CODE_RE.findall(plain):
        d = digits(m)
        if d and d not in support_digits:
            bad.append(m.strip())
    for u in URL_RE.findall(text):
        dom = re.sub(r"^https?://|^www\.", "", u.lower()).split("/")[0].rstrip(".,;)")
        if dom and dom not in support_low:
            bad.append(dom)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="heldout_set.jsonl")
    ap.add_argument("--a", required=True, help="results of the first config, e.g. baseline")
    ap.add_argument("--b", required=True, help="results of the second config, e.g. full")
    ap.add_argument("--names", nargs=2, default=["baseline (1 call)", "full agent"])
    ap.add_argument("--out", default="results/report.md")
    args = ap.parse_args()
    na, nb = args.names
    text_of = {}
    with open(args.data, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                text_of[d["id"]] = d["text"]
    A, B = load(args.a), load(args.b)
    ids = [i for i in A if i in B]
    out = [f"# Results on {len(ids)} held-out messages\n"]

    langs = ["all"] + sorted({A[i]["lang"] for i in ids})
    for lang in langs:
        sel = [i for i in ids if lang == "all" or A[i]["lang"] == lang]
        da, db = detection([A[i] for i in sel]), detection([B[i] for i in sel])
        out += [f"\n## {'All messages' if lang == 'all' else 'Language: ' + lang} ({len(sel)} messages)\n",
                f"| Measure | {na} | {nb} |", "|---|---|---|"]
        for k in da:
            out.append(f"| {k} | {fmt(*da[k])} | {fmt(*db[k])} |")

    better = [i for i in ids if correct(B[i]) and not correct(A[i])]
    worse = [i for i in ids if correct(A[i]) and not correct(B[i])]
    out += ["\n## Paired comparison (same messages)\n",
            f"- Only **{nb}** right: {len(better)} messages {better}",
            f"- Only **{na}** right: {len(worse)} messages {worse}",
            f"- Both right or both wrong: {len(ids) - len(better) - len(worse)} messages",
            f"- Exact sign test p = {sign_test(len(better), len(worse)):.2f} "
            f"({'a real difference' if sign_test(len(better), len(worse)) < 0.05 else 'not a significant difference'})"]

    out += ["\n## Unsupported facts in the advice (a number or website named from memory: in neither the message nor the knowledge base)\n",
            f"| | {na} | {nb} |", "|---|---|---|"]
    for title, flt in (("Scam messages", lambda r: r["label"] == "fraud"), ("All messages", lambda r: True)):
        cells, examples = [], []
        for R in (A, B):
            sel = [R[i] for i in ids if flt(R[i])]
            hits = [(r["id"], invented(r, text_of.get(r["id"], ""))) for r in sel]
            hits = [(i, b) for i, b in hits if b]
            cells.append(fmt(len(hits), len(sel)))
            examples.append(hits[:4])
        out.append(f"| {title}: verdicts naming an unsupported number or website | {cells[0]} | {cells[1]} |")
    out.append(f"\nExamples ({na}): {examples[0] if examples else []}")

    cost = lambda R: sum(R[i].get("tokens", 0) for i in ids) / max(1, len(ids))
    out += ["\n## Cost per message\n", f"| | {na} | {nb} |", "|---|---|---|",
            f"| LLM calls | {sum(A[i].get('calls', 0) for i in ids) / len(ids):.1f} | {sum(B[i].get('calls', 0) for i in ids) / len(ids):.1f} |",
            f"| Tokens | {cost(A):.0f} | {cost(B):.0f} |"]
    md = "\n".join(out)
    print(md)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
