"""
build_real_set.py — build a REAL test set from the IMC 2025 smishing dataset.

Source: "Fishing for Smishing" (IMC 2025), github.com/reportsmishing/Smishing-Dataset-IMC25
        27k+ real scam SMS reported by users on Twitter/Reddit/Smishtank (CC BY 4.0).
        The authors masked URLs, phone numbers and some names as <URL>, <PHONE_NUMBER>, ...

Step 1 — make candidates for you to check:
    python build_real_set.py extract
    -> real_candidates.csv  (open it, put y or n in the "keep" column for every row)

    Optional: add your own GENUINE messages as extra rows at the bottom with
    label = legit, lang = en or hi, keep = y  (change account digits / names first).

Step 2 — add the rows you kept to the eval set:
    python build_real_set.py merge
    -> appends them to eval_set.jsonl as split "real" (re-running replaces the old real rows)

Then:  python run_eval.py --configs baseline full --split real
"""

import csv
import json
import re
import sys

SRC = "../Smishing-Dataset-IMC25/dataset/final_dataset_output.csv"
CANDIDATES = "real_candidates.csv"
EVAL_SET = "eval_set.jsonl"
N_ENGLISH = 45
N_HINDI = 30
SEED = 7

INDIAN_ENTITIES = {
    "State Bank of India", "Paytm", "HDFC Bank", "Kotak Mahindra Bank", "ICICI Bank", "Axis Bank",
    "Airtel", "Jio", "BSNL", "electricity office", "PhonePe", "Google Pay",
}
INDIAN_CUES = re.compile(
    r"(?:₹|\brs\.?\s?\d|\binr\b|\bupi\b|\bkyc\b|\bpan\b|aadha+r|\bsbi\b|\byono\b|hdfc|icici|paytm|phonepe|"
    r"bijli|बिजली|खाता|बैंक|केवाईसी|पैन|आधार|ग्राहक|रुपये|इनाम|लोन)", re.I)
# Not fraud in our sense (marketing spam) or not the kind of message the app targets
EXCLUDE_TYPES = {"spam", "wrong number", "hey mum/dad"}

# The dataset's anonymiser sometimes mislabels things (e.g. <UK_NHS>, <US_BANK_NUMBER> on Indian SMS).
# Map every placeholder to a neutral, readable token so the model is not confused by them.
PLACEHOLDERS = {
    "<URL>": "[link removed]",
    "<PHONE_NUMBER>": "[phone number]",
    "<DATE_TIME>": "[date/time]",
}


def clean(text):
    for k, v in PLACEHOLDERS.items():
        text = text.replace(k, v)
    text = re.sub(r"<[A-Z_]+>", "[…]", text)  # any other placeholder
    return re.sub(r"\s+", " ", text).strip()


def extract():
    import pandas as pd  # only needed for this step

    df = pd.read_csv(SRC)
    df = df[df["language"].isin(["English", "Hindi"])
            & ~df["scam_type"].isin(EXCLUDE_TYPES)]
    india = df["named_entity"].isin(
        INDIAN_ENTITIES) | df["text"].str.contains(INDIAN_CUES, na=False)
    df = df[india].copy()
    df["clean"] = df["text"].astype(str).map(clean)
    df = df[df["clean"].str.len().between(40, 450)]
    df["key"] = df["clean"].str.lower().str.replace(
        r"[^a-z0-9ऀ-ॿ]+", "", regex=True)
    df = df.drop_duplicates("key")

    en = df[df["language"] == "English"]
    # spread the sample across scam types and brands instead of 45 copies of "SBI KYC blocked"
    en = en.sample(frac=1, random_state=SEED)
    per_group = en.fillna({"named_entity": "-"}
                          ).groupby(["scam_type", "named_entity"]).cumcount()
    en = en[per_group < 3].head(N_ENGLISH)
    hi = df[df["language"] == "Hindi"].sample(
        frac=1, random_state=SEED).head(N_HINDI)

    rows = []
    for lang_code, part in (("en", en), ("hi", hi)):
        for i, r in enumerate(part.itertuples(), 1):
            rows.append({"id": f"r{lang_code}{i:02d}", "lang": lang_code, "label": "fraud", "keep": "",
                         "scam_type": r.scam_type, "brand": r.named_entity if isinstance(r.named_entity, str) else "",
                         "date": r.time, "text": r.clean, "note": ""})

    # utf-8-sig: Hindi shows correctly in Excel
    with open(CANDIDATES, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} candidates to {CANDIDATES}  "
          f"(English {len(en)}, Hindi {len(hi)}). Put y/n in the 'keep' column for each row.")


def merge():
    with open(CANDIDATES, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    unchecked = [r["id"]
                 for r in rows if r["keep"].strip().lower() not in ("y", "n")]
    if unchecked:
        print(
            f"Warning: {len(unchecked)} rows have no y/n in 'keep' and are skipped: {unchecked[:10]}...")
    kept = [r for r in rows if r["keep"].strip().lower() == "y"]

    with open(EVAL_SET, encoding="utf-8") as f:
        existing = [json.loads(line) for line in f if line.strip()]
    # re-running replaces old real rows
    existing = [e for e in existing if e.get("split") != "real"]

    seen = set()
    new = []
    for i, r in enumerate(kept, 1):
        rid = r["id"].strip() or f"rx{i:02d}"
        if rid in seen:
            rid = f"{rid}_{i}"
        seen.add(rid)
        new.append({"id": rid, "lang": r["lang"].strip() or "en", "label": r["label"].strip() or "fraud",
                    "split": "real", "source": "IMC2025" if r.get("scam_type") else "own phone",
                    "text": r["text"].strip()})

    with open(EVAL_SET, "w", encoding="utf-8") as f:
        for e in existing + new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    fraud = sum(n["label"] == "fraud" for n in new)
    print(f"Added {len(new)} real messages to {EVAL_SET}: {fraud} fraud, {len(new) - fraud} legit "
          f"(en {sum(n['lang'] == 'en' for n in new)}, hi {sum(n['lang'] == 'hi' for n in new)}).")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step == "extract":
        extract()
    elif step == "merge":
        merge()
    else:
        print(__doc__)
