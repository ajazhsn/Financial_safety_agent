import base64
from dotenv import load_dotenv
import os
from sarvamai import SarvamAI
from groq import Groq

load_dotenv()

sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Step 1 — convert fraud SMS to audio
sms = "प्रिय ग्राहक, आपका KYC समाप्त हो गया है। तुरंत अपडेट करने के लिए इस लिंक पर क्लिक करें"

tts_response = sarvam.text_to_speech.convert(
    text=sms,
    language_code="hi-IN",
    model="bulbul:v3",
    speaker="neha",
)

# Save audio
audio_bytes = base64.b64decode(tts_response.audios[0])
with open("test_audio.wav", "wb") as f:
    f.write(audio_bytes)
print("Audio saved as test_audio.wav")

# Step 2 — transcribe back to text
with open("test_audio.wav", "rb") as f:
    stt_response = sarvam.speech_to_text.transcribe(
        file=f,
        language_code="hi-IN",
        model="saaras:v3",
    )

print(f"\nTranscribed text:\n{stt_response.transcript}")
