"""
service.py — the app's core logic, independent of any UI.

check_stream() runs the whole pipeline and yields progress events, then the result:
  read the input (OCR / ASR)  ->  agent (triage, investigate, verify)
  ->  translate everything the user sees (one Bodhan call)  ->  voice reply (TTS)
"""

import json
import os
import re
import time
import uuid

import clients
from agent import INCIDENT_MARKER, run
from clients import LANGUAGES, PAUSE_MS, ocr, speak_parts, split_for_tts, transcribe, translate
from pydub import AudioSegment

APP_MODEL = os.getenv("APP_MODEL", clients.DEV_MODEL)  # Haiku by default: fast and cheap
APP_CONFIG = os.getenv("APP_CONFIG", "cascade")  # "full" = always run the whole agent
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

STAMP = {  # verdict -> (kind, stamp word, English headline)
    "yes": ("fraud", "Scam", "Warning. This message is a fraud. Do not act on it."),
    "no": ("genuine", "Looks genuine", "This message looks genuine."),
    "unclear": ("unsure", "Not sure", "I am not sure about this message. Please be careful."),
}

TAG_RE = re.compile(r"\s*[\(\[]\s*(?:kb|tool)\s*:[^\)\]]*[\)\]]", re.I)


def clean(text):
    """Remove internal source tags like '(kb:recovery_001)' from user-facing text."""
    return TAG_RE.sub("", str(text or "")).replace("\n", " ").strip()


def rules_cited(verdict, limit=3):
    """Up to 3 official rules the verdict relied on (evidence sourced only from the knowledge base)."""
    rules = []
    for e in verdict.get("evidence", []):
        src = str(e.get("source", ""))
        if "kb:" in src and "tool:" not in src and e.get("claim"):
            rules.append(clean(e["claim"]))
    return rules[:limit]


def translate_lines(lines, lang):
    """Translate several short lines with ONE Bodhan call; fall back to one call per line
    if the line count does not survive translation."""
    if lang == "en" or not lines:
        return list(lines)
    out = [p.strip() for p in translate("\n".join(lines), lang).split("\n") if p.strip()]
    if len(out) == len(lines):
        return out
    return [translate(line, lang) for line in lines]


def timeline(out):
    """The agent's decisions as a list of steps for the 'How the agent decided' panel."""
    steps = []
    for s in out["log"]:
        name = s["step"]
        if name == "fast_check":
            steps.append({"kind": "fast", "detail": f"answer: {s.get('fraud')}"})
        elif name == "escalate":
            steps.append({"kind": "escalate", "note": s.get("reason", "")})
        elif name == "triage":
            steps.append({"kind": "triage", "detail": f"mode: {s.get('mode')}, difficulty: {s.get('difficulty')}",
                          "note": s.get("reason", "")})
        elif name == "investigate":
            steps.append({"kind": "investigate", "detail": f"budget: {s.get('budget')}"})
        elif name == "verify":
            steps.append({"kind": "verify", "ok": bool(s.get("approved")), "note": s.get("note", "")})
        elif name == "re-investigate":
            steps.append({"kind": "reinvestigate", "note": s.get("feedback", "")})
        elif name == "re-investigate-failed":
            steps.append({"kind": "reinvestigate", "note": "failed; kept the first verdict"})
        elif name == "incident_plan":
            steps.append({"kind": "incident"})
        elif name == "guard":  # the deterministic contact guard rewrote unsafe advice
            steps.append({"kind": "guard", "note": "; ".join(str(x)[:80] for x in s.get("removed", []))[:240]})
    tools = [{"tool": t["tool"], "args": json.dumps(t["args"], ensure_ascii=False)[:140]} for t in out["trace"]]
    evidence = [{"claim": e.get("claim", ""), "source": e.get("source", "")}
                for e in out["verdict"].get("evidence", [])]
    return {"steps": steps, "tools": tools, "evidence": evidence}


def localize_stream(bundle, lang):
    """Translate an English answer bundle into `lang`, send it, THEN record its voice.
    Yields {"localized": ...} as soon as the text is ready (the page shows it at once) and
    {"voice": {...}} when the audio is ready. Used after a check AND when the user switches
    language on an answer they already have."""
    if lang not in LANGUAGES.values():
        lang = "en"
    yield {"stage": "writing"}
    t1 = time.time()
    steps_en, rules_en = bundle["steps"], bundle["rules"]
    local = translate_lines([bundle["stamp"], bundle["headline"], bundle["explanation"]] + steps_en + rules_en, lang)
    stamp, head, explanation = local[0], local[1], local[2]
    steps = local[3:3 + len(steps_en)]
    rules = local[3 + len(steps_en):]
    t_translate = time.time() - t1
    yield {"localized": {"kind": bundle["kind"], "lang": lang, "stamp": stamp, "headline": head,
                         "explanation": explanation, "steps": steps, "rules": rules, "audio_url": None,
                         "voice_pending": True, "timing": {"translate": round(t_translate, 1)}}}

    t2 = time.time()
    # The voice reads EVERYTHING the user needs (many users cannot read). Written in English as full
    # sentences ("Step 1. ... .") and translated as ONE passage, so sentence endings survive and the
    # voice breaks at natural pauses.
    spoken = [bundle["headline"], bundle["explanation"].rstrip(".") + "."]
    spoken += [f"Step {i}. {a.rstrip('.')}." for i, a in enumerate(steps_en, 1)]
    spoken_en = " ".join(spoken)
    audio_url = None
    try:
        script = spoken_en if lang == "en" else translate(spoken_en, lang)
        chunks = split_for_tts(script)
        uid = uuid.uuid4().hex[:10]
        combined = AudioSegment.empty()
        for i, part in enumerate(speak_parts(chunks, lang)):
            name = f"reply_{uid}_{i}.wav"
            part.export(os.path.join(OUTPUT_DIR, name), format="wav")
            # each sentence goes to the page as soon as it is ready: the voice starts within seconds
            yield {"voice_part": {"url": f"/outputs/{name}", "index": i, "total": len(chunks), "lang": lang}}
            if i:
                combined += AudioSegment.silent(duration=PAUSE_MS, frame_rate=part.frame_rate)
            combined += part
        name = f"reply_{uid}.wav"
        combined.export(os.path.join(OUTPUT_DIR, name), format="wav")
        audio_url = f"/outputs/{name}"  # the whole answer, for replay
    except Exception as e:  # never lose the answer just because the voice failed
        print(f"TTS failed: {e}")
    yield {"voice": {"audio_url": audio_url, "lang": lang, "seconds": round(time.time() - t2, 1)}}


def check_stream(mode, lang, text=None, image_path=None, audio_path=None, already_acted=False):
    """Yields {"stage": ...} events, then {"result": {...}} or {"error": ...}."""
    if lang not in LANGUAGES.values():
        lang = "en"
    try:
        # 1. read the input
        yield {"stage": "reading"}
        if mode == "image":
            if not image_path:
                yield {"error": "need_image"}; return
            message = ocr(image_path)
        elif mode == "voice":
            if not audio_path:
                yield {"error": "need_voice"}; return
            message = transcribe(audio_path, lang)
        else:
            if not text or not text.strip():
                yield {"error": "need_text"}; return
            message = text.strip()
        agent_input = message + ("\n\n" + INCIDENT_MARKER if already_acted else "")

        # 2. the agent
        yield {"stage": "investigating"}
        t0 = time.time()
        clients.reset_usage()
        out = run(agent_input, config=APP_CONFIG, model=APP_MODEL)
        t_agent, calls = time.time() - t0, clients.USAGE["calls"]
        v = out["verdict"]
        kind, stamp_en, head_en = STAMP.get(str(v.get("fraud", "unclear")).lower(), STAMP["unclear"])

        # 3 + 4. translate everything the user sees and record the voice answer
        bundle = {"kind": kind, "stamp": stamp_en, "headline": head_en,
                  "explanation": clean(v.get("explanation", "")) or head_en,
                  "steps": [clean(a) for a in v.get("actions", []) if clean(a)],
                  "rules": rules_cited(v)}
        for event in localize_stream(bundle, lang):
            if "localized" not in event:
                if "voice" in event:
                    print(f"⏱ voice {event['voice']['seconds']}s")
                yield event  # stages, then the voice when it is ready
                continue
            local = event["localized"]
            timing = {"agent": round(t_agent, 1), "calls": calls, **local.pop("timing"), "model": APP_MODEL,
                      "config": APP_CONFIG}
            print(f"⏱ {timing}")
            yield {"result": {
                **local, "read_text": out["masked_message"].split("\n\n" + INCIDENT_MARKER)[0], "en": bundle,
                "hidden": out["hidden"],
                "english": {"type": v.get("fraud_type", ""), "risk": v.get("risk", ""),
                            "explanation": bundle["explanation"], "steps": bundle["steps"]},
                "agent": timeline(out), "timing": timing,
            }}
    except Exception as e:
        print(f"check failed: {e!r}")
        yield {"error": "failed", "detail": str(e)[:300]}
