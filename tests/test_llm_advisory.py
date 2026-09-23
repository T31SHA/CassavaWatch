from types import SimpleNamespace

import pytest

from app import llm_advisory
from app.advisory import get_advice
from app.config import Settings


class FakeClient:
    def __init__(self, content=None, exc=None):
        self.calls = []
        self.content, self.exc = content, exc
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


@pytest.fixture
def use(monkeypatch):
    def _use(key="sk-test", client=None):
        monkeypatch.setattr(llm_advisory, "get_settings", lambda: Settings(qwen_api_key=key, _env_file=None))
        monkeypatch.setattr(llm_advisory, "_cache", {})
        monkeypatch.setattr(llm_advisory, "_get_client", lambda: client)
        return client
    return _use


def test_blank_key_uses_template(use):
    client = use(key="", client=FakeClient(content="- should not be used"))
    out = llm_advisory.generate_advice("cmd", 0.9, "en", 3, 0.46, 34.11)
    assert out == {"advice_bullets": get_advice("cmd", "en")["bullets"], "source": "template"}
    assert client.calls == []


def test_exception_falls_back_to_template(use):
    use(client=FakeClient(exc=TimeoutError("timed out")))
    out = llm_advisory.generate_advice("cbsd", 0.8, "sw", 3, 0.46, 34.11)
    assert out["source"] == "template"
    assert out["advice_bullets"] == get_advice("cbsd", "sw")["bullets"]


def test_success_uses_llm_and_caps_bullets(use):
    client = use(client=FakeClient(content="Here you go:\n- Uproot sick plants.\n- Burn them.\n"
                                           "- Use certified clean cuttings.\n- Weed.\n- Extra fifth point."))
    out = llm_advisory.generate_advice("cmd", 0.9, "en", 3, 0.46, 34.11)
    assert out["source"] == "llm"
    assert 1 <= len(out["advice_bullets"]) <= 4
    msgs = client.calls[0]["messages"]
    assert "English only" in msgs[0]["content"]
    assert get_advice("cmd", "en")["bullets"][0] in msgs[1]["content"]  # template passed as grounding
    # cached: second call does not hit the API
    llm_advisory.generate_advice("cmd", 0.92, "en", 4, 0.5, 34.2)
    assert len(client.calls) == 1


def test_diagnose_reports_advice_source(use):
    import io

    from fastapi.testclient import TestClient
    from PIL import Image

    from app.main import app

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (40, 160, 40)).save(buf, "JPEG")
    client = use(client=FakeClient(content="- One.\n- Two.\n- Three."))
    with TestClient(app) as c:
        r = c.post("/api/diagnose", files=[("images", ("l.jpg", buf.getvalue(), "image/jpeg"))],
                   data={"lat": "0.46", "lon": "34.11", "model": "Qwen-Ambassador/Qwen3.8-plus"})
        assert r.status_code == 200, r.text
        assert r.json()["advice"]["source"] == "llm"
        assert r.json()["advice"]["bullets"] == ["One.", "Two.", "Three."]
        assert client.calls[0]["model"] == "Qwen-Ambassador/Qwen3.8-plus"
        assert c.get("/api/config").json()["qwen_model"]
