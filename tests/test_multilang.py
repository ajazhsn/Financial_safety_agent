import base64
from dotenv import load_dotenv
import os
from sarvamai import SarvamAI
from groq import Groq

load_dotenv()
sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_message(sms, language_code, language_name):
    print(f"\n{'='*50}")
    print(f"Testing: {language_name}")
    print(f"Input: {sms}")
    print('='*50)

    # Fraud analysis
    prompt = f"""
You are a financial fraud detection assistant for Indian users.
The message below may be in Urdu, Punjabi, Hindi or other South Asian languages.
Understand it directly and analyze it for fraud.

Respond in exactly this format in English:
FRAUD: Yes/No
TYPE: (e.g. KYC scam, OTP scam, phishing, legitimate, etc.)
RISK: High/Medium/Low
EXPLANATION: (1-2 simple sentences explaining what this message is trying to do)
ACTION: (1 sentence telling the user exactly what to do)

Message: {sms}
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    analysis = response.choices[0].message.content
    print(f"\nFraud Analysis:\n{analysis}")

    # Translate full response
    translated = sarvam.text.translate(
        input=analysis,
        source_language_code="en-IN",
        target_language_code=language_code,
        model="sarvam-translate:v1",
    )
    translated_text = translated.translated_text
    print(f"\nResponse in {language_name}:\n{translated_text}")

    # Extract short spoken version — just ACTION line in English, translate that
    action_line = ""
    for line in analysis.split("\n"):
        if line.startswith("ACTION:"):
            action_line = line.replace("ACTION:", "").strip()
            break

    # Build short spoken message
    fraud_flag = "Yes" if "FRAUD: Yes" in analysis else "No"
    risk_level = ""
    for line in analysis.split("\n"):
        if line.startswith("RISK:"):
            risk_level = line.replace("RISK:", "").strip()
            break

    spoken_english = f"Warning. This message is a fraud. Risk level is {risk_level}. {action_line}"

    # For TTS — use hi-IN for Urdu since spoken Urdu and Hindi are mutually intelligible
    # Punjabi (pa-IN) is supported directly
    tts_language = "hi-IN" if language_code == "ur-IN" else language_code

    # Translate spoken text for all non-English languages
    spoken_for_tts = sarvam.text.translate(
        input=spoken_english,
        source_language_code="en-IN",
        target_language_code=tts_language,
        model="sarvam-translate:v1",
    ).translated_text

    print(f"Text being spoken: {spoken_for_tts}")

    from pydub import AudioSegment
    import io

    # Split into sentences for more reliable TTS
    sentences = [s.strip() for s in spoken_for_tts.replace(
        "।", ".").split(".") if s.strip()]

    combined = AudioSegment.empty()

    for sentence in sentences:
        if not sentence:
            continue
        tts_response = sarvam.text_to_speech.convert(
            text=sentence,
            language_code=tts_language,
            model="bulbul:v3",
            speaker="neha",
        )
        audio_bytes = base64.b64decode(tts_response.audios[0])
        segment = AudioSegment.from_wav(io.BytesIO(audio_bytes))
        combined += segment + AudioSegment.silent(duration=300)

    audio_filename = f"response_{language_name.lower()}.wav"
    combined.export(audio_filename, format="wav")
    print(f"✅ Audio saved as {audio_filename}")


# Urdu test
urdu_sms = "محترم گاہک، آپ کا KYC ختم ہو گیا ہے۔ فوری اپ ڈیٹ کے لیے اس لنک پر کلک کریں: bit.ly/upd8kyc"
analyze_message(urdu_sms, "ur-IN", "Urdu")

# Punjabi test
punjabi_sms = "ਪਿਆਰੇ ਗਾਹਕ, ਤੁਹਾਡਾ KYC ਖਤਮ ਹੋ ਗਿਆ ਹੈ। ਤੁਰੰਤ ਅਪਡੇਟ ਕਰਨ ਲਈ ਇਸ ਲਿੰਕ 'ਤੇ ਕਲਿੱਕ ਕਰੋ: bit.ly/upd8kyc"
analyze_message(punjabi_sms, "pa-IN", "Punjabi")
