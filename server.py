"""
server.py — the web app: a FastAPI server + a hand-built page in static/.

Run:   python server.py      then open http://127.0.0.1:8000

Endpoints
  GET  /                 the page
  GET  /api/config       languages + examples
  GET  /api/ui/{lang}    every label on the page in that language
  POST /api/check        runs the agent; streams progress as JSON lines, then the result
  POST /api/localize     re-translates an existing answer into another language (no agent re-run)
"""

import json
import os
import tempfile

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from clients import LANGUAGES
from pydantic import BaseModel

from service import APP_MODEL, OUTPUT_DIR, check_stream, localize_stream, translate_lines
from ui_strings import BUILT_IN, EN, EXAMPLES, LANGUAGE_NAMES

app = FastAPI(title="Financial Safety Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
os.makedirs("ui_cache", exist_ok=True)


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/config")
def config():
    langs = [{"code": c, "name": LANGUAGE_NAMES.get(c, n)} for n, c in LANGUAGES.items()]
    return {"languages": langs, "examples": EXAMPLES}


@app.get("/api/ui/{lang}")
def ui(lang: str):
    """Labels in the chosen language. Non-built-in languages are translated once and cached."""
    if lang in BUILT_IN:
        return BUILT_IN[lang]
    if lang not in LANGUAGES.values():
        return EN
    cache = os.path.join("ui_cache", f"{lang}.json")
    strings = {}
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            strings = json.load(f)
        if set(EN) <= set(strings):
            return strings
    try:  # translate only the labels not cached yet (new labels get added over time)
        keys = [k for k in EN if k not in strings]
        values = translate_lines([EN[k] for k in keys], lang)
        strings.update(dict(zip(keys, values)))
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(strings, f, ensure_ascii=False, indent=1)
        return strings
    except Exception as e:  # if translation fails, the page still works in English
        print(f"UI translation to {lang} failed: {e}")
        return JSONResponse(EN)


def _save_upload(upload, suffix):
    if not upload or not upload.filename:
        return None
    ext = os.path.splitext(upload.filename)[1] or suffix
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(upload.file.read())
    return path


@app.post("/api/check")
def check(mode: str = Form("text"), lang: str = Form("hi"), text: str = Form(""),
          acted: bool = Form(False), image: UploadFile | None = File(None),
          audio: UploadFile | None = File(None)):
    image_path = _save_upload(image, ".png") if mode == "image" else None
    audio_path = _save_upload(audio, ".webm") if mode == "voice" else None

    def events():
        try:
            for event in check_stream(mode, lang, text=text, image_path=image_path,
                                      audio_path=audio_path, already_acted=acted):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            for p in (image_path, audio_path):
                if p and os.path.exists(p):
                    os.remove(p)

    return StreamingResponse(events(), media_type="application/x-ndjson")


class LocalizeRequest(BaseModel):
    lang: str
    en: dict


@app.post("/api/localize")
def localize(req: LocalizeRequest):
    """Re-translate an answer the user already has into a new language (no agent re-run)."""
    def events():
        try:
            for event in localize_stream(req.en, req.lang):
                if "localized" in event:
                    event = {"result": {**event["localized"], "relocalized": True}}
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            print(f"localize failed: {e!r}")
            yield json.dumps({"error": "failed"}) + "\n"
    return StreamingResponse(events(), media_type="application/x-ndjson")


if __name__ == "__main__":
    print(f"App is using LLM: {APP_MODEL}")
    print("Open http://127.0.0.1:8000 in your browser")
    uvicorn.run(app, host="127.0.0.1", port=8000)
