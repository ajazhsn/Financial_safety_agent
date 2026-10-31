"""
privacy.py — hide personal data before a message is sent to the LLM.

The LLM runs outside India (OpenRouter), so the agent never sends it:
  OTPs / PINs / CVVs              -> [OTP hidden], [CVV hidden]
  card and account numbers        -> [card ending 4321], [account ending 4321]
  Aadhaar and PAN numbers         -> [Aadhaar hidden], [PAN hidden]
  the user's name after a greeting -> [name hidden]   ("Dear Rahul Sharma," / "प्रिय राहुल")

It deliberately KEEPS what the fraud check needs: links, phone numbers, UPI IDs, amounts,
brand names and e-mail addresses. Those are the scammer's details, not the user's.

Pure regex, no model, no network: it runs on every message and is unit-tested
(tests/test_privacy.py).
"""

import re

# Shared with agent.py (signals, contact guard): what must never be masked.
URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:in|com|net|org|xyz|top|info|online|site|link|click|co|ly|me|io|app)(?:/[^\s]*)?)", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)|(?<!\d)1800[\s-]?\d{3}[\s-]?\d{3,4}(?!\d)")
UPI_RE = re.compile(r"\b[\w.\-]{2,}@(?:ok\w+|ybl|ibl|axl|upi|paytm|apl|\w*bank\w*)\b", re.I)
EMAIL_RE = re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b")

OTP_WORDS = (r"otp|one[\s-]?time[\s-]?password|verification\s+code|security\s+code|login\s+code|"
             r"m-?pin|upi\s+pin|\bpin\b(?!\s*code)|password|ओटीपी|पिन|ஓடிபி|ஓ\.டி\.பி|கடவுச்சொல்")
# a 4-8 digit group that is not part of a longer number ("1800 1234" is a helpline, not an OTP)
OTP_DIGITS = r"(?<![\d.,])(?<!\d\s)(\d{4,8})(?![\d.,]*\d)(?!\s\d)"
OTP_AFTER_RE = re.compile(rf"(?:{OTP_WORDS})[^\d\n]{{0,40}}?{OTP_DIGITS}", re.I)
OTP_BEFORE_RE = re.compile(rf"{OTP_DIGITS}\s+(?:is|is\s+your|as\s+your|है|आपका)\s+(?:your\s+)?(?:{OTP_WORDS})",
                           re.I)
CVV_RE = re.compile(r"cvv2?\b[^\d\n]{0,15}(\d{3,4})(?!\d)", re.I)
AADHAAR_RE = re.compile(r"(?<![\d])[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?![\d])")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CARD_RE = re.compile(r"(?<![\d])\d(?:[\s-]?\d){12,18}(?![\d])")
ACCOUNT_RE = re.compile(r"(?:a/?c|acct|account|loan|खाता|खाते|கணக்கு)(?:\s*(?:no\.?|number|num|संख्या|#))?[\s:.\-#]*"
                        r"(?<![\dX*])(\d[\d\s-]{4,20}\d)(?![\d])", re.I)
LONG_NUMBER_RE = re.compile(r"(?<![\d])\d{11,18}(?![\d])")

NAME_CUE_EN = r"(?:Dear|Hi|Hello|Hey|Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?|Sri)"
NAME_WORD = r"(?:[A-Z][a-z]+(?:[A-Z][a-z]+)*|[A-Z]\.)"  # Rahul, ManuVashishth, K.
NAME_EN_RE = re.compile(rf"\b{NAME_CUE_EN}\s+({NAME_WORD}(?:\s+{NAME_WORD}){{0,2}})")
NAME_HI_RE = re.compile(r"(?:प्रिय|श्री|श्रीमती|सुश्री)\s+([ऀ-ॿ]+)")
NOT_NAMES = {  # words after "Dear ..." that are not a person's name
    "customer", "customers", "sir", "madam", "user", "users", "member", "parent", "parents", "valued",
    "cardholder", "team", "friend", "friends", "student", "subscriber", "client", "account", "holder",
    "applicant", "investor", "policyholder", "beneficiary", "all", "there", "patron", "guest",
    "sbi", "hdfc", "icici", "axis", "kotak", "amazon", "flipkart", "paytm", "phonepe", "airtel", "jio",
    "vodafone", "bsnl", "google", "bank", "netflix", "uidai", "income", "tax", "lic", "post", "india",
    "consumer", "consumers", "dear", "winner", "employee", "candidate", "partner", "seller", "merchant",
}
ENDS_NAME = {"your", "you", "we", "our", "this", "the", "please", "kindly", "thanks", "thank", "greetings",
             "congratulations", "congrats", "welcome", "a", "an", "is", "has", "it"}
NOT_NAMES_HI = {"ग्राहक", "उपभोक्ता", "सदस्य", "अभिभावक", "खाताधारक", "महोदय", "महोदया", "मित्र", "उपयोगकर्ता",
                "कार्डधारक", "निवेशक", "आवेदक", "लाभार्थी"}


def _luhn(digits):
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total, alt = total + d, not alt
    return total % 10 == 0


def mask_pii(text):
    """Return (masked_text, hidden) where hidden is a list of {"type", "label"} for the UI.
    Never touches links, phone numbers, UPI IDs or e-mail addresses."""
    if not text:
        return text, []
    protected = [m.span() for r in (URL_RE, PHONE_RE, UPI_RE, EMAIL_RE) for m in r.finditer(text)]
    spans = []  # (start, end, replacement, type, label)

    def free(a, b):
        return not any(a < y and x < b for x, y in protected) and not any(a < s[1] and s[0] < b for s in spans)

    def add(a, b, repl, kind, label):
        if free(a, b):
            spans.append((a, b, repl, kind, label))

    for m in PAN_RE.finditer(text):
        add(*m.span(), "[PAN hidden]", "pan", "PAN")
    for m in CVV_RE.finditer(text):
        add(*m.span(1), "[CVV hidden]", "cvv", "CVV")
    for r in (OTP_AFTER_RE, OTP_BEFORE_RE):
        for m in r.finditer(text):
            add(*m.span(1), "[OTP hidden]", "otp", "OTP")
    for m in ACCOUNT_RE.finditer(text):
        d = re.sub(r"\D", "", m.group(1))
        if len(d) >= 6:
            add(*m.span(1), f"[account ending {d[-4:]}]", "account", d[-4:])
    for m in CARD_RE.finditer(text):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 12 and AADHAAR_RE.fullmatch(m.group(0)):
            add(*m.span(), "[Aadhaar hidden]", "aadhaar", "Aadhaar")
        elif _luhn(d) or re.search(r"card|कार्ड", text[max(0, m.start() - 30):m.start()], re.I):
            add(*m.span(), f"[card ending {d[-4:]}]", "card", d[-4:])
    for m in AADHAAR_RE.finditer(text):
        add(*m.span(), "[Aadhaar hidden]", "aadhaar", "Aadhaar")
    for m in LONG_NUMBER_RE.finditer(text):
        add(*m.span(), f"[account ending {m.group(0)[-4:]}]", "account", m.group(0)[-4:])
    for m in NAME_EN_RE.finditer(text):
        words = m.group(1).split()
        keep = []
        for w in words:  # "Dear Rahul Your account..." -> only "Rahul"
            if w.strip(".").lower() in ENDS_NAME:
                break
            keep.append(w)
        if keep and not any(w.strip(".").lower() in NOT_NAMES for w in words):
            name = " ".join(keep)
            add(m.start(1), m.start(1) + len(name), "[name hidden]", "name", "name")
    for m in NAME_HI_RE.finditer(text):
        if m.group(1) not in NOT_NAMES_HI:  # first name only; surnames can't be told from ordinary words
            add(*m.span(1), "[name hidden]", "name", "name")

    out, hidden, last = [], [], 0
    for a, b, repl, kind, label in sorted(spans):
        out.append(text[last:a] + repl)
        last = b
        hidden.append({"type": kind, "label": label})
    out.append(text[last:])
    return "".join(out), hidden


if __name__ == "__main__":  # quick manual check: python privacy.py "Dear Rahul, your OTP is 482913"
    import sys
    print(mask_pii(" ".join(sys.argv[1:])))
