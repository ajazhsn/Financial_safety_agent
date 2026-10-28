"""
clients.py — one place for every external model call.

Bodhan.ai  -> ASR (indic-transcribe), TTS (indic-speak), MT (indic-translate), OCR (indic-ocr)
OpenRouter -> the LLM (agent brain)

Everything else in the project imports from here, so swapping a provider
later means editing this file only.
"""

import base64
import io
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment

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

# TTS voice per language. Only "Amit" (English) is confirmed from the docs —
# check the voice list in console.bodhan.ai and fill these in.
VOICES = {
    "en": "Amit",
}
DEFAULT_VOICE = "Amit"


def _headers(model_key):
    key = KEYS[model_key]
    if not key:
        raise RuntimeError(f"No Bodhan key set for '{model_key}'. Check your .env file.")
    return {"Authorization": f"Bearer {key}"}


def _chat_content(resp):
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------- MT
def translate(text, target_lang):
    """Translate text into target_lang (e.g. 'ta'). Source language is auto-detected."""
    if not text.strip():
        return text
    resp = requests.post(
        f"{BODHAN_URL}/chat/completions",
        headers=_headers("translate"),
        json={
            "model": "indic-translate",
            "messages": [{"role": "user", "content": text}],
            "target_language_code": target_lang,
            "target_script": "native",
        },
        timeout=TIMEOUT,
    )
    return _chat_content(resp)


# ---------------------------------------------------------------- OCR
def ocr(image_path):
    """Read all text from an image (screenshot of an SMS / WhatsApp message)."""
    ext = os.path.splitext(image_path)[1].lower().lstrip(".") or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    resp = requests.post(
        f"{BODHAN_URL}/chat/completions",
        headers=_headers("ocr"),
        json={
            "model": "indic-ocr",
            "messages": [{"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{mime};base64,{b64}"}}
            ]}],
        },
        timeout=TIMEOUT,
    )
    return _chat_content(resp)


# ---------------------------------------------------------------- ASR
ASR_CHUNK_MS = 25_000  # Bodhan accepts at most 30 s per request; stay under it


def _transcribe_bytes(wav_bytes, lang):
    resp = requests.post(
        f"{BODHAN_URL}/audio/transcriptions",
        headers=_headers("transcribe"),
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"model": "indic-transcribe", "language": lang, "vad": True},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
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
def split_for_tts(text, max_len=120):
    """Short chunks — TTS works best on short inputs (kept from v1)."""
    rough = [s.strip() for s in text.replace("।", ".").split(".") if s.strip()]
    chunks = []
    for sentence in rough:
        if len(sentence) <= max_len:
            chunks.append(sentence)
        else:
            chunks.extend(p.strip() for p in sentence.split(",") if p.strip())
    return chunks


def _speak_chunk(text, lang):
    resp = requests.post(
        f"{BODHAN_URL}/audio/speech",
        headers=_headers("speak"),
        json={
            "model": "indic-speak",
            "input": text,
            "voice": VOICES.get(lang, DEFAULT_VOICE),
            "instructions": f'{{"lang": "{lang}"}}',
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return AudioSegment.from_file(io.BytesIO(resp.content))


def speak(text, lang, out_path="response.wav"):
    """Text -> one stitched .wav file. Returns the file path."""
    combined = AudioSegment.empty()
    for chunk in split_for_tts(text):
        combined += _speak_chunk(chunk, lang) + AudioSegment.silent(duration=300)
    combined.export(out_path, format="wav")
    return out_path


# ---------------------------------------------------------------- LLM
_llm = OpenAI(base_url="https://openrouter.ai/api/v1",
              api_key=os.getenv("OPENROUTER_API_KEY"))

# Cheap model while building, strong model for the final eval + demo.
# Check exact model names at openrouter.ai/models before running.
DEV_MODEL = os.getenv("DEV_MODEL", "anthropic/claude-haiku-4.5")
FINAL_MODEL = os.getenv("FINAL_MODEL", "anthropic/claude-sonnet-5")


def llm(messages, model=None, tools=None, json_mode=False, temperature=0):
    """One LLM call through OpenRouter. Returns the full message object
    (so the agent can read .content and .tool_calls)."""
    kwargs = {"model": model or DEV_MODEL, "messages": messages, "temperature": temperature}
    if tools:
        kwargs["tools"] = tools
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _llm.chat.completions.create(**kwargs)
    return resp.choices[0].message
