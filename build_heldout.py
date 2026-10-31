"""
build_heldout.py — a FRESH test set that the prompts have never seen.

The 104 messages in eval_set.jsonl were used to tune the agent, so they are the DEVELOPMENT set.
This builds the final TEST set (target: 40 scams + 40 genuine) from messages that are NOT in
real_candidates.csv or eval_set.jsonl.

Step 1 — candidates (free, no API calls):
    python build_heldout.py extract
    -> heldout_candidates.csv  (80 new scam candidates from the IMC 2025 dataset)
    Open it in Excel / VS Code. For every row put y or n in "keep" (n = marketing spam, not a scam,
    unreadable, or not Indian). Keep about 40 scams.
    Then ADD YOUR OWN GENUINE MESSAGES at the bottom, one row each (about 40):
        id = g01, g02 ...   lang = en / hi / hi-en (Hinglish)   label = legit   keep = y   text = the SMS
    Copy real messages from your phone: bank debit/credit alerts, OTPs, bills, deliveries, telecom,
    chats with friends. Personal data is masked automatically in step 2.

Step 2 — build the test set:
    python build_heldout.py merge
    -> heldout_set.jsonl  (OTPs, card/account numbers and greeting names are masked with privacy.py,
       so the file is safe to commit)

Step 3 — run it ONCE per config (it is the final test, do not tune on it):
    python run_eval.py --data heldout_set.jsonl --configs baseline full --tag test_
"""

import csv
import json
import sys

import pandas as pd

from build_real_set import CANDIDATES, EVAL_SET, EXCLUDE_TYPES, INDIAN_CUES, INDIAN_ENTITIES, SRC, clean
from privacy import mask_pii

OUT_CSV = "heldout_candidates.csv"
OUT_SET = "heldout_set.jsonl"
N_ENGLISH, N_HINDI, SEED = 60, 20, 11


def key(text):
    return pd.Series([str(text)]).str.lower().str.replace(r"[^a-z0-9ऀ-ॿ]+", "", regex=True).iloc[0]


def used_keys():
    keys = set()
    with open(CANDIDATES, encoding="utf-8-sig") as f:
        keys |= {key(r["text"]) for r in csv.DictReader(f)}
    with open(EVAL_SET, encoding="utf-8") as f:
        keys |= {key(json.loads(line)["text"]) for line in f if line.strip()}
    return keys


def extract():
    df = pd.read_csv(SRC)
    df = df[df["language"].isin(["English", "Hindi"]) & ~df["scam_type"].isin(EXCLUDE_TYPES)]
    india = df["named_entity"].isin(INDIAN_ENTITIES) | df["text"].str.contains(INDIAN_CUES, na=False)
    df = df[india].copy()
    df["clean"] = df["text"].astype(str).map(clean)
    df = df[df["clean"].str.len().between(40, 450)]
    df["key"] = df["clean"].str.lower().str.replace(r"[^a-z0-9ऀ-ॿ]+", "", regex=True)
    df = df.drop_duplicates("key")
    df = df[~df["key"].isin(used_keys())]  # never reuse a development message

    en = df[df["language"] == "English"].sample(frac=1, random_state=SEED)
    per_group = en.fillna({"named_entity": "-"}).groupby(["scam_type", "named_entity"]).cumcount()
    en = en[per_group < 4].head(N_ENGLISH)
    hi = df[df["language"] == "Hindi"].sample(frac=1, random_state=SEED).head(N_HINDI)

    rows = []
    for lang, part in (("en", en), ("hi", hi)):
        for i, r in enumerate(part.itertuples(), 1):
            rows.append({"id": f"h{lang}{i:02d}", "lang": lang, "label": "fraud", "keep": "",
                         "scam_type": r.scam_type, "brand": r.named_entity if isinstance(r.named_entity, str) else "",
                         "text": r.clean})
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} new scam candidates to {OUT_CSV} (English {len(en)}, Hindi {len(hi)}).")
    print("Put y/n in 'keep'. Then add ~40 of your own genuine messages at the bottom (see the file header).")


def merge():
    with open(OUT_CSV, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["keep"].strip().lower() == "y"]
    items, masked = [], 0
    for r in rows:
        text, hidden = mask_pii(r["text"].strip())
        masked += bool(hidden)
        label = r["label"].strip().lower()
        items.append({"id": r["id"].strip(), "lang": r["lang"].strip() or "en",
                      "label": "fraud" if label == "fraud" else "legit", "split": "heldout",
                      "source": (r.get("source") or "").strip() or ("IMC2025" if r.get("scam_type") else "own phone"),
                      "text": text})
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate ids in heldout_candidates.csv"
    with open(OUT_SET, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    n_f = sum(i["label"] == "fraud" for i in items)
    langs = {l: sum(i["lang"] == l for i in items) for l in sorted({i["lang"] for i in items})}
    print(f"Wrote {len(items)} messages to {OUT_SET}: {n_f} fraud, {len(items) - n_f} genuine, languages {langs}.")
    print(f"Personal data was masked in {masked} messages. Open {OUT_SET} and read it once before committing.")


if __name__ == "__main__":
    {"extract": extract, "merge": merge}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
