import base64
from dotenv import load_dotenv
import os
from sarvamai import SarvamAI
from groq import Groq

load_dotenv()

sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_message(sms, source_language="hi-IN"):

    # Step 1 — fraud analysis directly on original text (no translation needed)
    prompt = f"""
You are a financial fraud detection assistant for Indian users.
The message below may be in Hindi, Tamil, Telugu, or other Indian languages.
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
    print(f"[Fraud analysis]:\n{analysis}\n")

    # Step 2 — translate response to user's language
    translated_back = sarvam.text.translate(
        input=analysis,
        source_language_code="en-IN",
        target_language_code=source_language,
    )
    print(f"[Response in user's language]:\n{translated_back.translated_text}")


# Test it
sms = "प्रिय ग्राहक, आपका KYC समाप्त हो गया है। तुरंत अपडेट करने के लिए इस लिंक पर क्लिक करें: bit.ly/upd8kyc"
analyze_message(sms, source_language="hi-IN")
