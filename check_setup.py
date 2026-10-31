"""
check_setup.py — checks that everything is in place before you run the app. It makes NO paid API calls.

  python check_setup.py
"""

import importlib
import os
import shutil
import sys

OK, BAD = "  [ok]  ", "  [!!]  "
problems = 0


def report(good, text, fix=""):
    global problems
    print((OK if good else BAD) + text + ("" if good else f"\n          fix: {fix}"))
    problems += not good


print("Python")
report(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "install Python 3.12")

print("Packages")
for name in ["fastapi", "uvicorn", "multipart", "openai", "requests", "dotenv", "pydub", "chromadb",
             "sentence_transformers", "pandas", "pytest"]:
    try:
        importlib.import_module(name)
        report(True, name)
    except Exception:
        report(False, name, "pip install -r requirements.txt")

print("Tools")
report(bool(shutil.which("ffmpeg")), "ffmpeg on PATH",
       "winget install ffmpeg (Windows) / brew install ffmpeg (macOS) / sudo apt install ffmpeg (Linux), "
       "then open a new terminal")

print("Keys (.env)")
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
report(os.path.exists(".env"), ".env file exists", "copy .env.example to .env and fill in your keys")
report(bool(os.getenv("OPENROUTER_API_KEY")), "OPENROUTER_API_KEY is set", "add it to .env")
fallback = os.getenv("BODHAN_API_KEY")
for k in ["BODHAN_TRANSLATE_KEY", "BODHAN_TRANSCRIBE_KEY", "BODHAN_OCR_KEY", "BODHAN_SPEAK_KEY"]:
    report(bool(os.getenv(k) or fallback), f"{k} (or BODHAN_API_KEY) is set", "add it to .env")

if os.getenv("OPENROUTER_API_KEY"):
    print("OpenRouter credit (free lookup)")
    try:
        import requests
        d = requests.get("https://openrouter.ai/api/v1/key", timeout=15,
                         headers={"Authorization": "Bearer " + os.getenv("OPENROUTER_API_KEY")}).json()["data"]
        left = d.get("limit_remaining")
        report(left is None or left > 0.05, f"key works; credit remaining: "
               f"{'no limit' if left is None else f'${left:.2f}'}", "the key has no credit left")
    except Exception as e:
        report(False, f"could not reach OpenRouter ({type(e).__name__})", "check the key and your internet")

print("Project files")
for f in ["agent.py", "server.py", "rbi_trai_knowledge_base.py", "static/index.html", "heldout_set.jsonl"]:
    report(os.path.exists(f), f, "run this from the project folder (the one with server.py)")
report(True, "knowledge base: " + ("built" if os.path.isdir("fraud_kb_store") else
                                   "not built yet, it is built automatically on the first start"))

print("\nAll good: run  python server.py" if not problems else f"\n{problems} problem(s) above. Fix them, then rerun.")
