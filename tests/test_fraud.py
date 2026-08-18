from dotenv import load_dotenv
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

sms = "प्रिय ग्राहक, आपका KYC समाप्त हो गया है। तुरंत अपडेट करने के लिए इस लिंक पर क्लिक करें: bit.ly/upd8kyc"

prompt = f"""
You are a financial fraud detection assistant for Indian users.

Analyze this message and respond in exactly this format:
FRAUD: Yes/No
TYPE: (e.g. KYC scam, OTP scam, phishing, legitimate, etc.)
RISK: High/Medium/Low
EXPLANATION: (1-2 simple sentences explaining what this message is trying to do)
ACTION: (1 sentence telling the user exactly what to do)

Message: {sms}
"""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
