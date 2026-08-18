"""
RBI / TRAI / NPCI Financial Fraud Knowledge Base — Expanded
Each entry is a self-contained, embedding-ready chunk.

Sources:
- RBI public advisories (KYC, vishing, phishing, remote access)
- RBI Advisory on Frauds/Cybercrimes via Investment/Part-time Job/Ponzi
  Schemes (reproduced via regulated entities, detailed modus operandi)
- RBI Notification on Prevention of Financial Frauds via Voice Calls
  and SMS, Jan 17 2025
- RBI Master Circular / customer liability framework for unauthorised
  electronic banking transactions (zero/limited liability rules)
- TRAI DLT & URL-whitelisting rules, effective Oct 1 2024
- NPCI — discontinuation of UPI P2P collect requests, effective Oct 2025
- Supreme Court / MHA directions on digital arrest scams, 2025-2026
- National Cyber Crime Reporting Portal (cybercrime.gov.in), 1930 helpline
"""

KNOWLEDGE_BASE = [
    # ---------------- KYC SCAMS ----------------
    {
        "id": "kyc_001",
        "category": "KYC Scam",
        "text": (
            "RBI has repeatedly clarified that it never contacts customers "
            "directly about KYC updates. No genuine bank asks a customer to "
            "update KYC by clicking a link received over SMS or WhatsApp, by "
            "installing a remote-access app, or over a phone call. The "
            "'your KYC will expire in 24 hours, click here to update' message "
            "is one of the most common banking scams in India. Fraudsters "
            "create a false sense of urgency, threatening account freezing or "
            "closure to pressure the customer into acting without thinking."
        ),
    },
    {
        "id": "kyc_002",
        "category": "KYC Scam",
        "text": (
            "A legitimate KYC update is only ever done by logging into the "
            "bank's own secure net banking portal or verified mobile app, or "
            "by visiting a branch in person. It is never initiated by an "
            "unsolicited SMS, email, or WhatsApp link. If a customer receives "
            "a KYC update request, RBI advises contacting the bank directly "
            "using contact details obtained from the bank's official website, "
            "not from the message itself."
        ),
    },

    # ---------------- REMOTE ACCESS / VISHING ----------------
    {
        "id": "remote_access_001",
        "category": "Remote Access Scam",
        "text": (
            "RBI has issued specific warnings against a KYC scam variant "
            "where, after a victim enters credentials on a fake page, a "
            "scammer calls claiming to be a 'KYC officer' and asks the "
            "victim to install a remote-access app such as AnyDesk, "
            "TeamViewer, or QuickSupport to 'complete verification.' No "
            "legitimate bank or RBI process ever asks a customer to install "
            "remote-access software. If this is requested, the call should "
            "be ended immediately."
        ),
    },
    {
        "id": "vishing_001",
        "category": "Vishing (Voice Phishing)",
        "text": (
            "RBI defines vishing as phone calls pretending to be from a "
            "bank, e-wallet provider, or telecom service provider, aimed at "
            "luring customers into sharing confidential details under the "
            "pretext of KYC updation, unblocking an account or SIM card, or "
            "'crediting back' a debited amount. Fraudsters often obtain "
            "customer care numbers by searching online — genuine bank "
            "helpline numbers should only be taken from the back of the "
            "debit/credit card or the bank's official app, never from a "
            "generic web search result."
        ),
    },

    # ---------------- OTP SCAMS ----------------
    {
        "id": "otp_001",
        "category": "OTP Scam",
        "text": (
            "No bank, RBI official, KYC officer, or customer support "
            "representative will ever ask a customer to share an OTP, PIN, "
            "CVV, or password over a call, SMS, or link — not even to "
            "'verify identity' or 'process a refund' or 'cancel a "
            "transaction.' An OTP is meant to be entered only by the "
            "account holder on the bank's own platform. Any request to "
            "read out or forward an OTP is a fraud attempt with no "
            "exceptions."
        ),
    },
    {
        "id": "withdrawal_alert_001",
        "category": "OTP/Withdrawal Scam",
        "text": (
            "A common fraud pattern involves a fake message claiming a "
            "large withdrawal or transaction request has been received on "
            "the recipient's account, asking them to 'share the OTP "
            "immediately if this was not you' to cancel it. This is "
            "designed to create panic so the victim shares the OTP without "
            "verifying independently. In reality, this OTP is often the "
            "one needed to authorize a fraudulent transaction the scammer "
            "is initiating. Genuine banks never ask a customer to share an "
            "OTP to 'stop' a transaction."
        ),
    },

    # ---------------- UPI SCAMS ----------------
    {
        "id": "upi_pin_001",
        "category": "UPI Scam — PIN Misuse",
        "text": (
            "A UPI PIN is required only to SEND money, never to RECEIVE it. "
            "Fraudsters frequently pose as buyers on platforms like OLX, "
            "claiming they are 'sending' payment and asking the victim to "
            "enter their UPI PIN to 'accept' or 'confirm receipt.' Entering "
            "the PIN in this situation actually authorises an outgoing "
            "payment from the victim's account. No legitimate payment "
            "receipt ever requires entering a PIN."
        ),
    },
    {
        "id": "upi_qr_001",
        "category": "UPI Scam — QR Code",
        "text": (
            "In a QR code scam, a fraudster sends a QR code under the "
            "pretext of transferring money to the victim, but scanning it "
            "and completing the flow actually triggers a payment OUT of the "
            "victim's account. Scanning a QR code should only ever be done "
            "when the user is making a payment themselves, never when "
            "someone claims to be sending money — receiving money never "
            "requires scanning anything."
        ),
    },
    {
        "id": "upi_collect_001",
        "category": "UPI Scam — Collect Request",
        "text": (
            "NPCI permanently discontinued peer-to-peer UPI 'collect "
            "requests' from October 2025 specifically because they were "
            "being exploited to trick users into approving fraudulent "
            "outgoing payments disguised as incoming refunds or payments. "
            "Any message today claiming a 'collect request' needs approval "
            "to receive money should be treated as highly suspicious, since "
            "this payment mechanism should no longer be presenting itself "
            "to ordinary UPI users in that form."
        ),
    },
    {
        "id": "upi_liability_001",
        "category": "UPI/Banking — Liability Rules",
        "text": (
            "Under RBI's customer liability framework for unauthorised "
            "electronic transactions, if a fraud occurred with no "
            "negligence on the customer's part and is reported within 3 "
            "working days, the customer's liability is zero and the bank "
            "must refund the full amount. If the fraud involved some "
            "customer action (such as sharing an OTP or PIN) but is "
            "reported within 7 working days, liability is limited to a "
            "capped amount depending on account type. Reporting speed "
            "directly determines how much of the loss can be recovered, "
            "which is why immediate reporting to the bank and 1930 matters "
            "more than anything else after a fraud occurs."
        ),
    },

    # ---------------- INVESTMENT / TASK-BASED SCAMS ----------------
    {
        "id": "investment_001",
        "category": "Investment / Part-time Job Scam",
        "text": (
            "RBI has documented a detailed modus operandi for investment "
            "and part-time-job fraud: victims are lured through 'Earn "
            "Online' or 'Part Time Job' advertisements promising high "
            "commissions or returns such as doubling money quickly. These "
            "ads redirect to a chat on a messaging platform. Once a task is "
            "given, the victim is required to load money through "
            "unauthorised payment gateways via UPI to 'activate' or "
            "'complete' the task, gaining the victim's trust with a small "
            "initial payout before larger amounts are demanded and the "
            "fraudster stops responding."
        ),
    },
    {
        "id": "investment_002",
        "category": "Investment / Part-time Job Scam",
        "text": (
            "In documented task-based investment scams, each victim is "
            "given a personal referral code and communicates with a "
            "fraudster largely over chat, sometimes using Google Translate "
            "to communicate in the victim's language. A call centre may "
            "contact the victim directly if they fail to load funds, "
            "applying additional pressure. Genuine investment platforms "
            "never require a user to 'load funds' via an unauthorised "
            "third-party payment gateway to unlock earnings."
        ),
    },
    {
        "id": "sebi_001",
        "category": "Investment Fraud — Verification",
        "text": (
            "Any investment advice or trading tip received through an "
            "unknown WhatsApp or Telegram group should not be acted upon. "
            "Only SEBI-registered investment advisors and intermediaries "
            "should be trusted, and their registration can be verified "
            "independently before investing. Sharing trading account "
            "credentials with anyone, including a person claiming to be an "
            "advisor, is never required by a legitimate platform."
        ),
    },

    # ---------------- DIGITAL ARREST ----------------
    {
        "id": "digital_arrest_001",
        "category": "Digital Arrest Scam",
        "text": (
            "In a 'digital arrest' scam, fraudsters impersonate law "
            "enforcement officials — police, CBI, ED, customs, or NCB — "
            "over a phone or video call and falsely accuse the victim of "
            "involvement in a crime such as money laundering, drug "
            "trafficking, or an illegal parcel sent in their name. Caller "
            "ID is often spoofed to appear as a genuine Indian number. "
            "There is no legal concept of a 'digital arrest' in Indian law "
            "— a lawful arrest requires physical custody, and no agency "
            "arrests or detains a person over a video call."
        ),
    },
    {
        "id": "digital_arrest_002",
        "category": "Digital Arrest Scam",
        "text": (
            "The digital arrest scam typically escalates by keeping the "
            "victim under constant video surveillance, isolating them from "
            "contacting family or friends, and demanding money be "
            "transferred to a so-called 'RBI escrow account,' 'security "
            "verification account,' or 'safe account' to clear their name. "
            "These accounts are actually mule accounts controlled by the "
            "criminal network. RBI has explicitly stated it never asks "
            "individuals to transfer money, and no regulator freezes "
            "accounts or clears names over a phone or video call."
        ),
    },

    # ---------------- FAKE LOAN APPS ----------------
    {
        "id": "loan_app_001",
        "category": "Fake Loan App Scam",
        "text": (
            "Fraudulent instant-loan apps, often not registered with RBI "
            "or any NBFC, request excessive permissions during installation "
            "— particularly access to contacts, photos, and messages. After "
            "disbursing a small loan, some of these apps use the harvested "
            "contact list to harass the borrower and their contacts with "
            "threats if repayment is not made through unauthorised personal "
            "UPI IDs rather than official channels. Before using any loan "
            "app, its registration should be verified on RBI's official "
            "list of regulated lenders."
        ),
    },

    # ---------------- FAKE CUSTOMER CARE ----------------
    {
        "id": "fake_care_001",
        "category": "Fake Customer Care Scam",
        "text": (
            "Fraudsters list fake customer care numbers online for banks "
            "and payment apps, so that a person searching for help on a "
            "search engine unknowingly calls the scammer instead of the "
            "bank. The fake representative then asks the victim to install "
            "a screen-monitoring or remote-access tool to 'resolve' the "
            "issue, which instead gives the fraudster control of the "
            "victim's device. Genuine customer care numbers should only be "
            "sourced from the back of a bank card, a bank passbook, or the "
            "official banking app — never from a general web search."
        ),
    },

    # ---------------- FRAUD PATTERN SIGNALS ----------------
    {
        "id": "urgency_001",
        "category": "Fraud Pattern — Urgency Tactics",
        "text": (
            "RBI advisories note that fraudulent messages consistently use "
            "urgency and fear as their primary tactic — threatening account "
            "closure, blocking, legal action, or financial loss within a "
            "very short window (often 2 to 24 hours) if the recipient does "
            "not act immediately. This pressure is designed to prevent the "
            "victim from pausing to verify the message through official "
            "channels. A genuine bank communication does not threaten "
            "account closure over SMS with a short deadline."
        ),
    },
    {
        "id": "url_001",
        "category": "Fraud Pattern — Suspicious Links",
        "text": (
            "Since October 1, 2024, TRAI regulations require that all "
            "legitimate commercial SMS in India use full, pre-whitelisted "
            "URLs registered on the DLT (Distributed Ledger Technology) "
            "platform. Shortened links such as bit.ly, tinyurl, or similar "
            "services are not permitted in registered commercial SMS and "
            "are blocked during network filtering. A message from a bank "
            "or financial institution containing a shortened or unfamiliar "
            "link is a strong indicator of fraud, since a genuine registered "
            "sender would not be able to send one."
        ),
    },
    {
        "id": "sender_id_001",
        "category": "Fraud Pattern — Sender Verification",
        "text": (
            "Every legitimate commercial SMS sender in India, including "
            "banks, must register their sender ID (header) on a TRAI-"
            "approved DLT platform. Fraudulent messages often spoof or "
            "closely mimic a bank's name in the sender ID but originate "
            "from unregistered numbers or generic mobile numbers. If a "
            "'bank' message arrives from a regular 10-digit mobile number "
            "rather than an alphanumeric registered header, this is a "
            "strong signal that the message is not genuine."
        ),
    },
    {
        "id": "legitimate_001",
        "category": "Legitimate Communication Markers",
        "text": (
            "A genuine bank SMS or communication will never ask for an "
            "OTP, PIN, password, or full card number; will never contain a "
            "shortened URL; will never threaten immediate account closure "
            "within hours; and will generally come from a registered "
            "alphanumeric sender ID matching the bank's name, not a "
            "regular mobile number. If a message lacks all of these red "
            "flags, it is more likely legitimate, but customers should "
            "still avoid clicking links directly and instead navigate to "
            "the bank's app or website independently."
        ),
    },

    # ---------------- RECOVERY / REPORTING ----------------
    {
        "id": "recovery_001",
        "category": "Recovery Steps",
        "text": (
            "If a person has clicked a fraudulent link, shared an OTP, or "
            "suspects their account is compromised, RBI and the National "
            "Cyber Crime Reporting Portal recommend immediate action: "
            "freeze or block the account through net banking or by calling "
            "the bank, call the national cyber crime helpline 1930, and "
            "file a complaint at cybercrime.gov.in. Reporting a UPI fraud "
            "within 24 hours meaningfully raises the chance of recovering "
            "the lost amount."
        ),
    },
    {
        "id": "recovery_002",
        "category": "Recovery Steps",
        "text": (
            "If a person has installed an unknown app (such as a fake KYC, "
            "loan, or remote-access app) as part of a scam, it is "
            "recommended to back up only essential personal data such as "
            "photos and contacts — never the app itself — and factory "
            "reset the phone, since some fraudulent apps can persist even "
            "after being uninstalled normally. This should be done after "
            "securing bank accounts first."
        ),
    },

    # ---------------- REGULATORY CONTEXT ----------------
    {
        "id": "voice_sms_fraud_001",
        "category": "Regulatory — RBI PFF Notification",
        "text": (
            "RBI's Notification on Prevention of Financial Frauds "
            "Perpetrated Using Voice Calls and SMS (issued January 17, "
            "2025) places responsibility on Principal Entities and Senders "
            "— including banks — to ensure their communications cannot be "
            "misused for fraud, and requires institutional safeguards "
            "against unsolicited commercial communications in the "
            "financial sector. This reflects the scale of voice-call and "
            "SMS-based financial fraud in India and the regulatory push to "
            "make senders accountable for the communications sent in their "
            "name."
        ),
    },
    {
        "id": "mule_account_001",
        "category": "Regulatory — Mule Accounts",
        "text": (
            "RBI has deployed an AI/ML-based solution called 'MuleHunter.AI' "
            "across major banks to detect mule accounts — bank accounts "
            "opened using real or fake identities and used to receive and "
            "layer stolen funds from fraud victims. Fraud proceeds are "
            "typically moved rapidly through multiple mule accounts before "
            "being converted to crypto, gold, or sent abroad, which is why "
            "speed of reporting is critical to any chance of recovery."
        ),
    },
]
