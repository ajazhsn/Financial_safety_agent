from sarvamai import SarvamAI

client = SarvamAI(api_subscription_key="sk_rzec3iex_zRSsasnS42mibrgTuDxpILty")

# Same message but in proper Devanagari script
sms = "प्रिय ग्राहक, आपका KYC समाप्त हो गया है। तुरंत अपडेट करने के लिए इस लिंक पर क्लिक करें: bit.ly/upd8kyc"

result = client.text.translate(
    input=sms,
    source_language_code="hi-IN",
    target_language_code="en-IN",
)

print("Original SMS:")
print(sms)
print("\nTranslated:")
print(result.translated_text)