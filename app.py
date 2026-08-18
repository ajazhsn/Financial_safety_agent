import base64
import io
import zipfile
import re
from dotenv import load_dotenv
import os
from sarvamai import SarvamAI
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb
from pydub import AudioSegment
import gradio as gr

load_dotenv()
sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
kb_client = chromadb.PersistentClient(path="./fraud_kb_store")
kb_collection = kb_client.get_or_create_collection(name="rbi_trai_fraud_kb")

LANGUAGES = {
    "Hindi": "hi-IN",
    "Punjabi": "pa-IN",
    "Urdu": "ur-IN",
}


def retrieve_relevant_guidance(text, n_results=3):
    query_embedding = embed_model.encode([text]).tolist()
    results = kb_collection.query(
        query_embeddings=query_embedding, n_results=n_results)
    semantic_chunks = results["documents"][0]

    always_include = kb_collection.get(
        ids=["recovery_001", "upi_liability_001"])
    always_chunks = always_include["documents"]

    all_chunks = semantic_chunks + \
        [c for c in always_chunks if c not in semantic_chunks]
    return all_chunks


def split_for_tts(text, max_len=120):
    rough_sentences = [s.strip()
                       for s in text.replace("।", ".").split(".") if s.strip()]
    final_chunks = []
    for sentence in rough_sentences:
        if len(sentence) <= max_len:
            final_chunks.append(sentence)
        else:
            parts = [p.strip() for p in sentence.split(",") if p.strip()]
            final_chunks.extend(parts)
    return final_chunks


def extract_text_from_image(image_path, language_code="hi-IN"):
    job = sarvam.document_intelligence.create_job(
        language=language_code, output_format="html")
    job.upload_file(image_path)
    job.start()
    job.wait_until_complete()
    job.download_output("ocr_output.zip")

    with zipfile.ZipFile("ocr_output.zip", "r") as z:
        z.extractall("ocr_output")
    with open("ocr_output/document.html", "r", encoding="utf-8") as f:
        html = f.read()

    body = re.search(r"<body>(.*?)</body>", html, re.DOTALL).group(1)
    clean_text = re.sub(r"<br\s*/?>", "\n", body)
    clean_text = re.sub(r"<[^>]+>", " ", clean_text)
    clean_text = re.sub(r"\n{2,}", "\n", clean_text)
    clean_text = "\n".join(line.strip()
                           for line in clean_text.split("\n") if line.strip())
    return clean_text


def run_fraud_analysis(message_text, language_code):
    guidance_chunks = retrieve_relevant_guidance(message_text, n_results=4)
    guidance_text = "\n\n".join(f"- {chunk}" for chunk in guidance_chunks)

    prompt = f"""
You are a financial fraud detection assistant for Indian users, grounded in
official RBI/TRAI/NPCI guidance. The message below may be in Hindi, Tamil,
Telugu, Urdu, Punjabi or other Indian languages. Understand it directly.

Be conservative: only mark FRAUD as Yes if the message shows a CONCRETE
fraud signal — a request for OTP/PIN/password, a suspicious or shortened
link, a threat of account closure with urgency, a fake refund/collect
request, or impersonation of an official/bank. A vague, incomplete, or
oddly-worded message alone is NOT sufficient evidence of fraud — if
uncertain, mark RISK as Low and say so honestly rather than defaulting
to High.

RELEVANT OFFICIAL GUIDANCE (use this to ground your answer — pull out the
SPECIFIC fact that applies, don't paraphrase generically):
{guidance_text}

Respond in exactly this format in English:
FRAUD: Yes/No
TYPE: (e.g. KYC scam, OTP scam, phishing, legitimate, unclear, etc.)
RISK: High/Medium/Low
EXPLANATION: (1-2 sentences naming the specific fraud pattern, or explain
why this message doesn't show clear fraud signals)
ACTION: (1 sentence with a SPECIFIC actionable detail — a reporting
deadline, liability rule, or helpline — not just "contact your bank")

Message: {message_text}
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    analysis = response.choices[0].message.content

    translated_full = sarvam.text.translate(
        input=analysis,
        source_language_code="en-IN",
        target_language_code=language_code,
        model="sarvam-translate:v1",
    ).translated_text

    risk_level, action_line, type_line, explanation_line = "", "", "", ""
    for line in analysis.split("\n"):
        if line.startswith("RISK:"):
            risk_level = line.replace("RISK:", "").strip()
        if line.startswith("ACTION:"):
            action_line = line.replace("ACTION:", "").strip()
        if line.startswith("TYPE:"):
            type_line = line.replace("TYPE:", "").strip()
        if line.startswith("EXPLANATION:"):
            explanation_line = line.replace("EXPLANATION:", "").strip()

    is_fraud = "FRAUD: Yes" in analysis
    spoken_english = (
        f"Warning. This looks like a {type_line}. {explanation_line} {action_line}"
        if is_fraud else
        "This message appears safe. No fraud indicators were found."
    )

    tts_language = "hi-IN" if language_code == "ur-IN" else language_code
    spoken_translated = sarvam.text.translate(
        input=spoken_english,
        source_language_code="en-IN",
        target_language_code=tts_language,
        model="sarvam-translate:v1",
    ).translated_text

    sentences = split_for_tts(spoken_translated)
    combined = AudioSegment.empty()
    for sentence in sentences:
        tts_response = sarvam.text_to_speech.convert(
            text=sentence, language_code=tts_language, model="bulbul:v3", speaker="neha",
        )
        audio_bytes = base64.b64decode(tts_response.audios[0])
        segment = AudioSegment.from_wav(io.BytesIO(audio_bytes))
        combined += segment + AudioSegment.silent(duration=300)

    audio_path = "ui_response.wav"
    combined.export(audio_path, format="wav")

    verdict = "🔴 FRAUD DETECTED" if is_fraud else "🟢 LOOKS SAFE"
    return verdict, analysis, translated_full, audio_path


def process_text_input(text, language_name):
    language_code = LANGUAGES[language_name]
    return run_fraud_analysis(text, language_code)


def process_voice_input(audio_path, language_name):
    language_code = LANGUAGES[language_name]
    with open(audio_path, "rb") as f:
        stt_response = sarvam.speech_to_text.transcribe(
            file=f, language_code=language_code, model="saaras:v3",
        )
    transcript = stt_response.transcript
    verdict, analysis, translated, audio_out = run_fraud_analysis(
        transcript, language_code)
    return f"Transcribed: {transcript}", verdict, analysis, translated, audio_out


def process_image_input(image_path, language_name):
    language_code = LANGUAGES[language_name]
    extracted = extract_text_from_image(image_path, language_code)
    verdict, analysis, translated, audio_out = run_fraud_analysis(
        extracted, language_code)
    return f"Extracted: {extracted}", verdict, analysis, translated, audio_out


with gr.Blocks(title="Financial Safety Agent") as demo:
    gr.Markdown("# 🛡️ Financial Safety Agent")
    gr.Markdown(
        "Detect fraud in bank SMS, voice messages, or screenshots — grounded in RBI/TRAI guidance, in your own language.")

    language_dropdown = gr.Dropdown(choices=list(
        LANGUAGES.keys()), value="Hindi", label="Your Language")

    with gr.Tabs():
        with gr.Tab("📝 Text Message"):
            text_input = gr.Textbox(
                label="Paste the suspicious message", lines=4)
            text_btn = gr.Button("Analyze", variant="primary")
            text_verdict = gr.Textbox(label="Verdict")
            text_analysis = gr.Textbox(label="Analysis (English)", lines=5)
            text_translated = gr.Textbox(
                label="Response in Your Language", lines=5)
            text_audio = gr.Audio(label="Voice Warning")
            text_btn.click(process_text_input, [text_input, language_dropdown],
                           [text_verdict, text_analysis, text_translated, text_audio])

        with gr.Tab("🎤 Voice Message"):
            voice_input = gr.Audio(
                label="Record or upload voice message", type="filepath")
            voice_btn = gr.Button("Analyze", variant="primary")
            voice_transcript = gr.Textbox(label="Transcript")
            voice_verdict = gr.Textbox(label="Verdict")
            voice_analysis = gr.Textbox(label="Analysis (English)", lines=5)
            voice_translated = gr.Textbox(
                label="Response in Your Language", lines=5)
            voice_audio = gr.Audio(label="Voice Warning")
            voice_btn.click(process_voice_input, [voice_input, language_dropdown],
                            [voice_transcript, voice_verdict, voice_analysis, voice_translated, voice_audio])

        with gr.Tab("📷 Screenshot"):
            image_input = gr.Image(
                label="Upload screenshot of message", type="filepath")
            image_btn = gr.Button("Analyze", variant="primary")
            image_extracted = gr.Textbox(label="Extracted Text")
            image_verdict = gr.Textbox(label="Verdict")
            image_analysis = gr.Textbox(label="Analysis (English)", lines=5)
            image_translated = gr.Textbox(
                label="Response in Your Language", lines=5)
            image_audio = gr.Audio(label="Voice Warning")
            image_btn.click(process_image_input, [image_input, language_dropdown],
                            [image_extracted, image_verdict, image_analysis, image_translated, image_audio])

if __name__ == "__main__":
    demo.launch()
