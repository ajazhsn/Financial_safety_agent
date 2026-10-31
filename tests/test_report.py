"""Tests for report.py helpers — run with: python -m pytest tests -q"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402


def row(explanation="", actions=()):
    return {"verdict": {"explanation": explanation, "actions": list(actions)}}


def test_wilson_matches_known_values():
    p, lo, hi = report.wilson(34, 35)
    assert round(p, 3) == 0.971 and 0.85 < lo < 0.86 and 0.98 < hi < 1.0
    assert report.wilson(0, 0) == (0.0, 0.0, 0.0)


def test_sign_test():
    assert report.sign_test(0, 0) == 1.0
    assert report.sign_test(1, 3) > 0.05          # one message either way is not a result
    assert report.sign_test(0, 10) < 0.01


def test_invented_facts_found_and_amounts_ignored():
    msg = "Rs 1500 debited. Call 1800 1234 if not you."
    assert report.invented(row(actions=["Call 1800 1234"]), msg) == []          # in the message
    assert report.invented(row(actions=["Rs 1500 was debited"]), msg) == []     # an amount is not a helpline
    assert report.invented(row(actions=["Call 1800 11 2211 now"]), msg)         # invented number
    assert report.invented(row(actions=["Visit fakebank-help.com"]), msg)       # invented website
    assert report.invented(row(actions=["Do not click the link"]), msg) == []
