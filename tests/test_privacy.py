"""Unit tests for privacy.mask_pii — run with:  python -m pytest tests -q"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from privacy import mask_pii  # noqa: E402


def types(text):
    return [h["type"] for h in mask_pii(text)[1]]


def test_otp_english_both_orders():
    assert mask_pii("Your OTP for login to SBI YONO is 482913. Do not share.")[0] == \
        "Your OTP for login to SBI YONO is [OTP hidden]. Do not share."
    assert mask_pii("482913 is your OTP for Paytm")[0].startswith("[OTP hidden]")


def test_otp_hindi_and_tamil():
    assert "739201" not in mask_pii("आपका OTP 739201 है। इसे किसी के साथ साझा न करें।")[0]
    assert "551902" not in mask_pii("உங்கள் ஓடிபி 551902. யாரிடமும் பகிர வேண்டாம்.")[0]


def test_helplines_links_upi_and_phones_are_kept():
    msg = ("Never share OTP. Call 1800 1234 or 1800 425 1234 or +91 9876543210. Pay to fraud@okaxis "
           "at http://sbi-kyc.xyz/verify or mail help@sbi-care.com")
    masked, hidden = mask_pii(msg)
    assert masked == msg and hidden == []


def test_card_cvv_and_name():
    masked, hidden = mask_pii("Dear Rahul Sharma, your card 4111 1111 1111 1111 is blocked. Share CVV 123.")
    assert masked == "Dear [name hidden], your card [card ending 1111] is blocked. Share CVV [CVV hidden]."
    assert [h["type"] for h in hidden] == ["name", "card", "cvv"]


def test_account_aadhaar_pan():
    masked, _ = mask_pii("Account no: 123456789012 PAN ABCDE1234F Aadhaar 2345 6789 0123")
    assert masked == "Account no: [account ending 9012] PAN [PAN hidden] Aadhaar [Aadhaar hidden]"
    assert "1234567890123" not in mask_pii("आपके खाते 1234567890123 से ₹1,200 डेबिट।")[0]


def test_already_masked_and_ordinary_numbers_untouched():
    for msg in ["Rs 2,500.00 debited from A/c XX4321 on 27-10-26. Avl Bal Rs 61,230.55",
                "Your order #405-1234567 ships Friday", "pin code 560001", "EMI of Rs 8,420 due on 05-11-2026"]:
        assert mask_pii(msg) == (msg, [])


def test_generic_greetings_and_brands_not_masked_as_names():
    for msg in ["Dear Customer, your bill is due", "Dear Amazon Customer, order shipped", "Hello Sir, kindly pay",
                "Hi, I reached home safely", "प्रिय ग्राहक, आपका बिल देय है"]:
        assert "name" not in types(msg)
    assert types("प्रिय राहुल, आपका बिल देय है") == ["name"]
    assert types("Mr. Gupta, received cash Rs 5700") == ["name"]
    assert mask_pii("Dear ManuVashishth, click here")[0] == "Dear [name hidden], click here"
    assert mask_pii("Dear Ravi Your account is blocked")[0] == "Dear [name hidden] Your account is blocked"
    assert "name" not in types("Dear Consumer Your power will be disconnected")


def test_otp_before_the_word_otp():
    assert mask_pii("482913 is the OTP for your transaction of Rs 2,499.00")[0].startswith("[OTP hidden] is the OTP")
