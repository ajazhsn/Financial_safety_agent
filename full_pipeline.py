import base64
import io
from dotenv import load_dotenv
import os
from sarvamai import SarvamAI
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb
from pydub import AudioSegment

load_dotenv()
sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
kb_client = chromadb.PersistentClient(path="./fraud_kb_store")
kb_collection = kb_client.get_or_create_collection(name="rbi_trai_fraud_kb")


def retrieve_relevant_guidance(text, n_results=3):
    query_embedding = embed_model.encode([text]).tolist()
    results = kb_collection.query(
        query_embeddings=query_embedding, n_results=n_results
    )
    semantic_chunks = results["documents"][0]

    # Always include the core recovery/reporting guidance —
    # it's universally actionable regardless of fraud type
    always_include = kb_collection.get(
        ids=["recovery_001", "upi_liability_001"])
    always_chunks = always_include["documents"]

    all_chunks = semantic_chunks + \
        [c for c in always_chunks if c not in semantic_chunks]
    return all_chunks


def split_for_tts(text, max_len=120):
    # First split on sentence-ending punctuation
    rough_sentences = [s.strip()
                       for s in text.replace("।", ".").split(".") if s.strip()]

    final_chunks = []
    for sentence in rough_sentences:
        if len(sentence) <= max_len:
            final_chunks.append(sentence)
        else:
            # Too long — split further on commas
            parts = [p.strip() for p in sentence.split(",") if p.strip()]
            final_chunks.extend(parts)
    return final_chunks


def analyze_voice_message(audio_file_path, language_code="hi-IN"):

    # Step 1 — transcribe voice to text
    print("🎤 Transcribing audio...")
    with open(audio_file_path, "rb") as f:
        stt_response = sarvam.speech_to_text.transcribe(
            file=f,
            language_code=language_code,
            model="saaras:v3",
        )
    transcript = stt_response.transcript
    print(f"Transcript: {transcript}\n")

    # Step 2 — retrieve relevant RBI/TRAI guidance
    print("📚 Retrieving relevant guidance...")
    guidance_chunks = retrieve_relevant_guidance(transcript, n_results=4)
    guidance_text = "\n\n".join(f"- {chunk}" for chunk in guidance_chunks)
    print(f"Retrieved {len(guidance_chunks)} relevant guidance entries\n")

    # Step 3 — fraud analysis grounded in retrieved guidance
    print("🔍 Analyzing for fraud...")
    prompt = f"""
You are a financial fraud detection assistant for Indian users, grounded in
official RBI/TRAI/NPCI guidance. The message below may be in Hindi, Tamil,
Telugu, Urdu, Punjabi or other Indian languages. Understand it directly.

RELEVANT OFFICIAL GUIDANCE (use this to ground your answer — do not just
paraphrase generically, pull out the SPECIFIC fact that applies):
{guidance_text}

Respond in exactly this format in English:
FRAUD: Yes/No
TYPE: (e.g. KYC scam, OTP scam, phishing, legitimate, etc.)
RISK: High/Medium/Low
EXPLANATION: (1-2 sentences — name the specific fraud pattern using the
guidance above, e.g. reference the exact regulation, rule, or modus
operandi described, not a vague summary)
ACTION: (1 sentence — include a SPECIFIC actionable detail from the
guidance if one exists, such as an exact reporting deadline, a liability
rule, or a helpline number. Do not just say "contact your bank" if the
guidance gives something more concrete.)

Message: {transcript}
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    analysis = response.choices[0].message.content
    print(f"Analysis:\n{analysis}\n")

    # Step 4 — translate full analysis to user's language (for display)
    print("🌐 Translating response...")
    translated_full = sarvam.text.translate(
        input=analysis,
        source_language_code="en-IN",
        target_language_code=language_code,
        model="sarvam-translate:v1",
    ).translated_text
    print(f"Response in user's language:\n{translated_full}\n")

    # Step 5 — build a short spoken summary
    risk_level = ""
    action_line = ""
    for line in analysis.split("\n"):
        if line.startswith("RISK:"):
            risk_level = line.replace("RISK:", "").strip()
        if line.startswith("ACTION:"):
            action_line = line.replace("ACTION:", "").strip()

    is_fraud = "FRAUD: Yes" in analysis
    if is_fraud:
        spoken_english = f"Warning. This message is a fraud. Risk level is {risk_level}. {action_line}"
    else:
        spoken_english = "This message appears safe. No fraud indicators were found."

    # Sarvam TTS doesn't support Urdu directly — speak it in Hindi instead
    tts_language = "hi-IN" if language_code == "ur-IN" else language_code

    spoken_translated = sarvam.text.translate(
        input=spoken_english,
        source_language_code="en-IN",
        target_language_code=tts_language,
        model="sarvam-translate:v1",
    ).translated_text

    print(f"🔊 Text being spoken: {spoken_translated}\n")

    # Step 6 — split into safe-length chunks and generate audio
    sentences = split_for_tts(spoken_translated)
    combined = AudioSegment.empty()

    for sentence in sentences:
        tts_response = sarvam.text_to_speech.convert(
            text=sentence,
            language_code=tts_language,
            model="bulbul:v3",
            speaker="neha",
        )
        audio_bytes = base64.b64decode(tts_response.audios[0])
        segment = AudioSegment.from_wav(io.BytesIO(audio_bytes))
        combined += segment + AudioSegment.silent(duration=300)

    combined.export("response_audio.wav", format="wav")
    print("✅ Voice response saved as response_audio.wav")


if __name__ == "__main__":
    analyze_voice_message("test_audio.wav", language_code="hi-IN")
