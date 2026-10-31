"""
clients.py — one place for every external model call.

Bodhan.ai  -> ASR (indic-transcribe), TTS (indic-speak), MT (indic-translate), OCR (indic-ocr)
OpenRouter -> the LLM (agent brain)

Everything else in the project imports from here, so swapping a provider
later means editing this file only.
"""

import base64
import hashlib
import io
import json
import os
import re
import time

import requests
from dotenv import load_dotenv
from openai import OpenAI

from pydub import AudioSegment
from pydub.silence import detect_leading_silence

load_dotenv()

BODHAN_URL = "https://api.bodhan.ai/v1"
TIMEOUT = 120  # seconds

# Bodhan issues one key per model. Each falls back to BODHAN_API_KEY
# in case one key turns out to work for all of them.
_FALLBACK = os.getenv("BODHAN_API_KEY")
KEYS = {
    "translate": os.getenv("BODHAN_TRANSLATE_KEY", _FALLBACK),
    "transcribe": os.getenv("BODHAN_TRANSCRIBE_KEY", _FALLBACK),
    "ocr": os.getenv("BODHAN_OCR_KEY", _FALLBACK),
    "speak": os.getenv("BODHAN_SPEAK_KEY", _FALLBACK),
}

# UI language name -> Bodhan language code
LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Bengali": "bn",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Urdu": "ur",
}

# TTS voices: a native FEMALE voice per language (from the Bodhan Indic-Speak voice list).
# Any voice can read any language. Override for every language with TTS_VOICE in .env
# (e.g. TTS_VOICE=Suhani), and optionally set a delivery style with TTS_STYLE
# (e.g. TTS_STYLE=Customer Care; leave it out for a neutral reading).
VOICES = {
    "hi": "Kavya", "en": "Kavya", "ta": "Anitha", "te": "Sravani", "kn": "Deepika",
    "ml": "Lakshmi", "bn": "Ishita", "mr": "Anagha", "pa": "Kaur", "ur": "Saba",
    "gu": "Dhara", "or": "Itishree", "as": "Prastuti",
}
DEFAULT_VOICE = "Kavya"
TTS_VOICE = os.getenv("TTS_VOICE")  # optional: one voice for everything
TTS_STYLE = os.getenv("TTS_STYLE")  # optional: e.g. "Customer Care", "news"


def _headers(model_key):
    key = KEYS[model_key]
    if not key:
        raise RuntimeError(f"No Bodhan key set for '{model_key}'. Check your .env file.")
    return {"Authorization": f"Bearer {key}"}


def _bodhan_post(path, model_key, **kwargs):
    """POST to Bodhan with retries: 429 (rate limit) and 5xx are retried with backoff."""
    for attempt in range(5):
        resp = requests.post(f"{BODHAN_URL}{path}", headers=_headers(model_key), timeout=TIMEOUT, **kwargs)
        if resp.status_code != 429 and resp.status_code < 500:
            break
        wait = float(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
        print(f"    Bodhan {model_key} returned {resp.status_code}, retrying in {wait:.0f}s")
        time.sleep(wait)
    resp.raise_for_status()
    return resp


def _chat_content(resp):
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------- MT
def translate(text, target_lang):
    """Translate text into target_lang (e.g. 'ta'). Source language is auto-detected."""
    if not text.strip():
        return text
    resp = _bodhan_post(
        "/chat/completions", "translate",
        json={
            "model": "indic-translate",
            "messages": [{"role": "user", "content": text}],
            "target_language_code": target_lang,
            "target_script": "native",
        },
    )
    return _chat_content(resp)


# ---------------------------------------------------------------- OCR
def ocr(image_path):
    """Read all text from an image (screenshot of an SMS / WhatsApp message)."""
    ext = os.path.splitext(image_path)[1].lower().lstrip(".") or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    resp = _bodhan_post(
        "/chat/completions", "ocr",
        json={
            "model": "indic-ocr",
            "messages": [{"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{mime};base64,{b64}"}}
            ]}],
        },
    )
    return _chat_content(resp)


# ---------------------------------------------------------------- ASR
ASR_CHUNK_MS = 25_000  # Bodhan accepts at most 30 s per request; stay under it


def _transcribe_bytes(wav_bytes, lang):
    resp = _bodhan_post(
        "/audio/transcriptions", "transcribe",
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"model": "indic-transcribe", "language": lang, "vad": True},
    )
    return resp.json()["text"]


def transcribe(audio_path, lang):
    """Speech -> text. Audio longer than 25 s is split into chunks automatically."""
    audio = AudioSegment.from_file(audio_path)
    parts = []
    for start in range(0, len(audio), ASR_CHUNK_MS):
        buf = io.BytesIO()
        audio[start:start + ASR_CHUNK_MS].export(buf, format="wav")
        parts.append(_transcribe_bytes(buf.getvalue(), lang))
    return " ".join(p.strip() for p in parts if p.strip())


# ---------------------------------------------------------------- TTS
# Sentence ends in every script we support: । ॥ (Devanagari, Bengali, Gurmukhi), ۔ ؟ (Urdu), . ? !
SENTENCE_END = r"(?<=[।॥۔؟?!])\s*|(?<=[^\d]\.)\s+"
CLAUSE_END = r"(?<=[,،;:])\s+"


def _split_long(text, max_len):
    """Break one over-long sentence: first at commas (incl. Urdu ،), then at the last space before max_len."""
    parts = [p.strip() for p in re.split(CLAUSE_END, text) if p.strip()]
    out = []
    for p in parts:
        while len(p) > max_len:
            cut = p.rfind(" ", 0, max_len)
            cut = cut if cut > max_len // 3 else max_len
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            out.append(p)
    return out


def split_for_tts(text, max_len=120):
    """One sentence per TTS call, like the original (v1) app: natural pauses fall between sentences.
    Very short sentences (e.g. "Step 1.") are joined to the next one; very long ones are split at
    commas, never in the middle of a word."""
    sentences = [x.strip() for x in re.split(SENTENCE_END, text) if x and x.strip()]
    pieces = []
    for sentence in sentences:
        pieces.extend([sentence] if len(sentence) <= max_len else _split_long(sentence, max_len))
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) < 40 and len(cur) + 1 + len(p) <= max_len:
            cur = f"{cur} {p}"  # keep tiny fragments like "Step 1." with their sentence
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def _speak_chunk(text, lang):
    resp = _bodhan_post(
        "/audio/speech", "speak",
        json={
            "model": "indic-speak",
            "input": text,
            "voice": TTS_VOICE or VOICES.get(lang, DEFAULT_VOICE),
            "instructions": json.dumps({"lang": lang, **({"style": TTS_STYLE} if TTS_STYLE else {})}),
        },
    )
    return AudioSegment.from_file(io.BytesIO(resp.content))


MIN_SECONDS_PER_CHAR = 1 / 25  # real speech is ~12-18 chars/s; much faster than 25 means audio was cut off


def _speak_checked(text, lang, depth=0):
    """Speak one chunk and check it was not truncated. If the audio is far too short
    for the amount of text, split the chunk in half and speak each half."""
    audio = _speak_chunk(text, lang)
    too_short = len(audio) / 1000 < len(text) * MIN_SECONDS_PER_CHAR
    if too_short and len(text) > 30 and depth < 2:
        print(f"    TTS looked truncated ({len(audio) / 1000:.1f}s for {len(text)} chars), splitting")
        parts = _split_long(text, max(30, len(text) // 2 + 10))  # at commas / word boundaries
        audio = AudioSegment.empty()
        for i, part in enumerate(parts):
            if i:
                time.sleep(0.5)
            audio += _speak_checked(part, lang, depth + 1)
    return audio


TTS_GAP_S = 0.4  # short gap between requests: Bodhan rate-limits bursts (429)
PAUSE_MS = 250  # the same short pause between every sentence
TTS_CACHE_DIR = os.path.join("outputs", "tts_cache")  # sentences that repeat (e.g. the headline) are spoken once


def _trim(seg, threshold=-45, keep_ms=40):
    """Cut the silence Bodhan puts at the start and end of each clip, so the joins sound even."""
    start = max(0, detect_leading_silence(seg, silence_threshold=threshold) - keep_ms)
    end = max(0, detect_leading_silence(seg.reverse(), silence_threshold=threshold) - keep_ms)
    out = seg[start:len(seg) - end]
    return out if len(out) > 200 else seg


def _speak_cached(text, lang):
    """One sentence -> trimmed audio. Returns (audio, came_from_cache)."""
    voice = TTS_VOICE or VOICES.get(lang, DEFAULT_VOICE)
    key = hashlib.sha1(f"{lang}|{voice}|{TTS_STYLE}|{text}".encode("utf-8")).hexdigest()
    path = os.path.join(TTS_CACHE_DIR, f"{key}.wav")
    if os.path.exists(path):
        return AudioSegment.from_file(path), True
    audio = _trim(_speak_checked(text, lang))
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    audio.export(path, format="wav")
    return audio, False


def speak_parts(chunks, lang):
    """Yield the audio of each chunk, in order, as soon as it is ready, so the app can start
    playing the first sentence while the rest are still being made."""
    asked = False
    for chunk in chunks:
        if asked:
            time.sleep(TTS_GAP_S)
        audio, cached = _speak_cached(chunk, lang)
        asked = not cached
        yield audio


def speak(text, lang, out_path="response.wav"):
    """Text -> one stitched .wav file with even pauses between sentences. Returns the path."""
    chunks = split_for_tts(text)
    if not chunks:
        raise ValueError("nothing to speak")
    combined = AudioSegment.empty()
    for i, part in enumerate(speak_parts(chunks, lang)):
        if i:
            combined += AudioSegment.silent(duration=PAUSE_MS, frame_rate=part.frame_rate)
        combined += part
    combined.export(out_path, format="wav")
    return out_path


# ---------------------------------------------------------------- LLM
_llm = OpenAI(base_url="https://openrouter.ai/api/v1",
              api_key=os.getenv("OPENROUTER_API_KEY"))

# Cheap model while building, strong model for the final eval + demo.
# Check exact model names at openrouter.ai/models before running.
DEV_MODEL = os.getenv("DEV_MODEL", "anthropic/claude-haiku-4.5")
FINAL_MODEL = os.getenv("FINAL_MODEL", "anthropic/claude-sonnet-5")


# Running totals, so the eval can report LLM calls and tokens per message.
USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def reset_usage():
    for k in USAGE:
        USAGE[k] = 0


def llm(messages, model=None, tools=None, temperature=0, max_tokens=1200):
    """One LLM call through OpenRouter. Returns the full message object
    (so the agent can read .content and .tool_calls)."""
    kwargs = {"model": model or DEV_MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens}
    if tools:
        kwargs["tools"] = tools
    # Retry transient failures (rate limits, provider hiccups) with backoff.
    for attempt in range(4):
        try:
            resp = _llm.chat.completions.create(**kwargs)
            if not resp.choices:
                raise RuntimeError(f"Empty response from OpenRouter: {resp}")
            break
        except Exception as e:
            if attempt == 3:
                raise
            wait = 2 ** (attempt + 1)
            print(f"    LLM call failed ({type(e).__name__}: {str(e)[:120]}), retrying in {wait}s")
            time.sleep(wait)
    USAGE["calls"] += 1
    if resp.usage:
        USAGE["prompt_tokens"] += resp.usage.prompt_tokens or 0
        USAGE["completion_tokens"] += resp.usage.completion_tokens or 0
    return resp.choices[0].message
