from dotenv import load_dotenv
import os
import zipfile
import re
from sarvamai import SarvamAI
from groq import Groq

load_dotenv()
sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_text_from_image(image_path, language_code="hi-IN"):
    print(f"Processing image: {image_path}")

    job = sarvam.document_intelligence.create_job(
        language=language_code,
        output_format="html"
    )
    job.upload_file(image_path)
    job.start()
    job.wait_until_complete()
    job.download_output("ocr_output.zip")

    with zipfile.ZipFile("ocr_output.zip", "r") as z:
        z.extractall("ocr_output")

    with open("ocr_output/document.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Strip HTML tags to get clean text
    body = re.search(r"<body>(.*?)</body>", html, re.DOTALL).group(1)
    clean_text = re.sub(r"<br\s*/?>", "\n", body)
    clean_text = re.sub(r"<[^>]+>", " ", clean_text)
    clean_text = re.sub(r"\n{2,}", "\n", clean_text)
    clean_text = "\n".join(line.strip()
                           for line in clean_text.split("\n") if line.strip())

    print(f"\nExtracted clean text:\n{clean_text}")
    return clean_text


def analyze_for_fraud(text):
    prompt = f"""
You are a financial fraud detection assistant for Indian users.
This text was extracted from a screenshot of an SMS or message.
It may contain OCR artifacts like timestamps or app UI text — ignore those, focus on the actual message content.

Respond in exactly this format in English:
FRAUD: Yes/No
TYPE: (e.g. KYC scam, OTP scam, phishing, legitimate, etc.)
RISK: High/Medium/Low
EXPLANATION: (1-2 simple sentences explaining what this message is trying to do)
ACTION: (1 sentence telling the user exactly what to do)

Extracted text: {text}
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# Full test
extracted = extract_text_from_image("test_sms.png", language_code="hi-IN")
print("\n" + "="*50)
print("Running fraud analysis on extracted text...")
print("="*50)
analysis = analyze_for_fraud(extracted)
print(f"\n{analysis}")
