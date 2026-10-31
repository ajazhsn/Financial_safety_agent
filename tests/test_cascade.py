"""Tests for the cascade routing in agent.py, with a fake LLM (no API calls, no cost).
Run with:  python -m pytest tests -q"""
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Lightweight stand-ins for the vector store, the embedding model and the API client,
# so this test runs offline in a second.
_chroma = types.ModuleType("chromadb")
_st = types.ModuleType("sentence_transformers")
_clients = types.ModuleType("clients")


class _KB:
    def __init__(self, **kw): pass
    def get_collection(self, name): return self
    def query(self, **kw): return {"ids": [["recovery_001", "upi_liability_001"]], "documents": [["a", "b"]]}


class _Embed:
    def __init__(self, *a): pass
    def encode(self, texts):
        class _V:
            def tolist(self): return [[0.0]]
        return _V()


_chroma.PersistentClient = _KB
_st.SentenceTransformer = _Embed
CALLS = []
FAST_ANSWER = {"fraud": "yes"}


class _Msg:
    def __init__(self, content): self.content, self.tool_calls = content, None


def _fake_llm(messages, model=None, **kw):
    text = json.dumps(messages, ensure_ascii=False)
    if "Classify this message" in text:
        CALLS.append("triage")
        mode = "incident" if "I have ALREADY clicked the link" in text else "check"
        return _Msg(json.dumps({"mode": mode, "difficulty": "ambiguous", "reason": "x"}))
    if "reviewer checking a fraud verdict" in text:
        CALLS.append("verify")
        return _Msg('{"approved": true, "note": ""}')
    if "has ALREADY acted" in text:
        CALLS.append("incident")
        return _Msg('{"fraud": "yes", "fraud_type": "x", "risk": "high", "evidence": [], '
                    '"explanation": "Act now.", "actions": ["Call 1930"]}')
    if "fraud investigator" in text:
        CALLS.append("investigate")
        return _Msg('{"fraud": "no", "fraud_type": "alert", "risk": "low", "evidence": [], '
                    '"explanation": "Looks genuine.", "actions": []}')
    CALLS.append("fast")
    return _Msg(json.dumps({**FAST_ANSWER, "fraud_type": "x", "risk": "low", "evidence": [],
                            "explanation": "e", "actions": ["Report on 1930"]}))


_clients.llm = _fake_llm
_saved = {n: sys.modules.get(n) for n in ("chromadb", "sentence_transformers", "clients", "agent")}
sys.modules.update({"chromadb": _chroma, "sentence_transformers": _st, "clients": _clients})
sys.modules.pop("agent", None)
import agent  # noqa: E402

# Put the real modules back so the stand-ins never leak into other test files.
for _name, _mod in _saved.items():
    if _mod is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _mod

agent.llm = _fake_llm


def run(msg, fast):
    CALLS.clear()
    FAST_ANSWER["fraud"] = fast
    return agent.run(msg, config="cascade")


def test_confident_fast_answer_is_not_escalated():
    out = run("Your KYC expired, click http://sbi-kyc.xyz", "yes")
    assert CALLS == ["fast"]
    assert out["verdict"]["fraud"] == "yes"
    assert [s["step"] for s in out["log"]] == ["fast_check"]
    assert out["trace"][0]["tool"] == "search_guidance"


def test_unclear_fast_answer_goes_to_the_full_agent():
    out = run("Rs 500 debited from A/c XX1234. Not you? Call 1800 1234", "unclear")
    assert CALLS == ["fast", "triage", "investigate", "verify"]
    assert out["verdict"]["fraud"] == "no"
    assert [s["step"] for s in out["log"]][:2] == ["fast_check", "escalate"]


def test_user_who_already_acted_gets_the_emergency_plan_directly():
    out = run("I paid Rs 5000 to this number\n\n" + agent.INCIDENT_MARKER, "no")
    assert "fast" not in CALLS and CALLS[-1] == "incident"
    assert out["log"][0]["step"] == "escalate"


def test_privacy_masking_happens_before_the_fast_check():
    out = run("Dear Rahul Sharma, your OTP is 482913", "no")
    assert "482913" not in out["masked_message"] and {h["type"] for h in out["hidden"]} == {"name", "otp"}
