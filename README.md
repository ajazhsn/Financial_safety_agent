# 🛡️ Financial Safety Agent

A multilingual, multi-modal fraud detection agent that reads bank SMS, voice messages, and message screenshots — flags financial fraud grounded in real RBI/TRAI/NPCI guidance — and explains the verdict back to the user by voice, in their own language.

Built as the course project for **DA7016: Recent Advances in GenAI** (Prof. Mitesh Khapra, IIT Madras).

---

## Why this project

Banking fraud in India overwhelmingly succeeds because of a language and literacy barrier. A fraudulent SMS in English, full of banking jargon, is impossible for a large fraction of users to evaluate for themselves. This project builds a vernacular-first safety layer: a user forwards a suspicious message (text, voice note, or screenshot) in Hindi, Urdu, or Punjabi, and gets back a clear, spoken verdict — grounded in actual RBI/TRAI regulation, not just an LLM's best guess.

---

## What it does

1. **Accepts input in three forms** — typed/pasted text, a voice recording, or a screenshot of a message.
2. **Understands it directly** in the user's language (Hindi, Urdu, Punjabi tested) without a lossy translation step first.
3. **Retrieves relevant official guidance** from a curated knowledge base of RBI, TRAI, and NPCI advisories before making a judgment.
4. **Analyzes the message for fraud** using an LLM prompted to cite specific regulatory facts — a reporting deadline, a liability rule, a helpline — rather than generic advice.
5. **Responds back in the user's language**, both as text and as a clean spoken voice warning.

---

## Architecture

```
                         ┌─────────────────────────┐
                         │        INPUT LAYER       │
                         │  Text | Voice | Screenshot│
                         └────────────┬──────────────┘
                                      │
                    Sarvam ASR / OCR (multilingual)
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     RETRIEVAL LAYER      │
                         │  SentenceTransformer      │
                         │  embeddings → ChromaDB    │
                         │  (25 RBI/TRAI/NPCI facts)│
                         └────────────┬──────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │    REASONING LAYER       │
                         │  Groq — LLaMA 3.3 70B     │
                         │  grounded fraud verdict  │
                         └────────────┬──────────────┘
                                      │
                    Sarvam Translate + TTS (chunked)
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       OUTPUT LAYER       │
                         │  Text verdict + Voice     │
                         │  warning, user's language │
                         └─────────────────────────┘
```

---

## Tech stack

| Layer | Tool |
|---|---|
| Speech-to-Text | Sarvam AI `saaras:v3` |
| OCR / Document Intelligence | Sarvam AI Document Intelligence |
| Translation | Sarvam AI `sarvam-translate:v1` |
| Text-to-Speech | Sarvam AI `bulbul:v3` |
| Reasoning / fraud analysis | Groq — LLaMA 3.3 70B Versatile |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector store | ChromaDB (local, persistent) |
| Audio stitching | `pydub` + FFmpeg |
| UI | Gradio |
| Env / secrets | `python-dotenv` |

---

## Knowledge base

Fraud verdicts are grounded in a **curated set of 25 real RBI/TRAI/NPCI advisories**, hand-sourced from official publications (not scraped indiscriminately), covering the fraud categories that catch the most ordinary users:

- KYC scams and remote-access app fraud
- Vishing (voice phishing) and fake customer care numbers
- OTP scams and withdrawal-alert scams
- UPI PIN misuse, QR code scams, and collect-request fraud
- Investment / part-time-job scams (RBI-documented modus operandi)
- Digital arrest scams
- Fake loan app harassment
- Regulatory facts: TRAI's Oct 2024 URL-whitelisting rule, RBI's 3-day/7-day liability framework, NPCI's Oct 2025 discontinuation of P2P collect requests, RBI's MuleHunter.AI initiative

Each entry is embedded and retrieved via semantic search; two core entries (reporting steps and liability rules) are **always included** regardless of similarity score, since "what to do next" is universally relevant to every fraud type.

---

## Project structure

```
financial-safety-agent/
├── app.py                       # Gradio UI — main entry point
├── full_pipeline.py             # Voice-in → voice-out pipeline (standalone/testing)
├── pipeline.py                  # Text-in → text-out pipeline (early version)
├── rbi_trai_knowledge_base.py   # 25 curated fraud advisories
├── build_vectorstore.py         # Embeds KB into ChromaDB
├── fraud_kb_store/              # Persisted ChromaDB vector store
├── tests/
│   ├── test_translate.py
│   ├── test_fraud.py
│   └── test_voice.py
├── test_multilang.py            # Urdu / Punjabi verification tests
├── test_ocr.py                  # Screenshot → fraud pipeline test
├── .env                         # API keys (not committed)
├── .gitignore
└── requirements.txt
```

---

## Setup

```bash
git clone <repo-url>
cd financial-safety-agent
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file:

```
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key
```

Build the knowledge base vector store (one-time):

```bash
python build_vectorstore.py
```

Run the app:

```bash
python app.py
```

Open the local URL Gradio prints (typically `http://127.0.0.1:7860`).

**Note:** FFmpeg must be installed and on PATH for audio stitching to work (`winget install ffmpeg` on Windows).

---

## Design decisions worth noting

**No translation-first pipeline.** An early version translated Hindi input to English before fraud analysis — this introduced meaning-inverting translation errors (e.g. "KYC expired" mistranslated as "KYC completed"). The fix: LLaMA 3.3 70B understands Hindi/Urdu/Punjabi directly, so the original text is analyzed as-is, and only the *output* is translated.

**Forced retrieval for reporting guidance.** Semantic search alone under-retrieves the liability/reporting rules for message types that don't textually resemble them (e.g. a KYC scam's embedding doesn't naturally match liability-rule text). Two core advisories are force-included in every retrieval, guaranteeing the model always has access to concrete next-step guidance.

**Calibrated fraud detection.** Early prompts over-flagged ambiguous, incomplete messages as high-risk fraud. The prompt was tightened to require concrete fraud signals (OTP/PIN requests, suspicious links, urgency + threat combinations, impersonation) before returning a positive verdict, and explicitly permits "unclear" as an honest answer.

**Sentence-chunked TTS.** Sarvam's TTS reliably truncates long single-call inputs. Responses are split into sub-120-character chunks (further split on commas if needed), synthesized individually, and stitched together with `pydub`/FFmpeg with natural pauses between them.

---

## Known limitations

- Urdu audio output is spoken in Hindi (Sarvam TTS doesn't support Urdu synthesis); spoken Hindi and Urdu are mutually intelligible, so this is a practical workaround, not a true gap in coverage.
- Knowledge base is a curated snapshot, not a live-updating scrape of RBI/TRAI publications.
- Tested on Hindi, Urdu, and Punjabi; broader Indic language coverage (Tamil, Telugu, Bengali, etc.) is implemented in the pipeline but not personally verified for translation/transcription quality.
- No quantified accuracy/precision metrics yet — a small manual evaluation set is a natural next step.

---

## Possible next steps

- Manual evaluation across a labeled test set (real fraud examples + legitimate messages) to report precision/recall
- Expand language coverage and verify against native speakers
- Move knowledge base to a lightweight scheduled scrape of RBI/TRAI press releases for freshness
- Add a lightweight fraud-type classifier as a first-pass filter before the LLM call, to reduce cost/latency
