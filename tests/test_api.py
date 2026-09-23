import io

from fastapi.testclient import TestClient
from PIL import Image

from app.inference import CLASSES
from app.main import app


def _img(color):
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(buf, "JPEG")
    return buf.getvalue()


def test_health():
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"


def test_diagnose_three_images_valid_schema():
    files = [("images", (f"l{i}.jpg", _img(col), "image/jpeg"))
             for i, col in enumerate([(30, 150, 30), (60, 170, 40), (90, 140, 50)])]
    with TestClient(app) as c:
        r = c.post("/api/diagnose", files=files, data={"lat": "0.46", "lon": "34.11", "lang": "sw"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["n_leaves"] == 3 and len(j["leaves"]) == 3
        assert j["label"] in CLASSES + ["uncertain"]
        assert 0 <= j["confidence"] <= 1
        assert set(j["probs"]) == set(CLASSES)
        assert j["advice"]["lang"] == "sw" and j["advice"]["text"]
        assert isinstance(j["report_id"], int)
        # report persisted and visible
        assert any(x["id"] == j["report_id"] for x in c.get("/api/reports?days=1").json())
        assert c.get("/api/alerts").status_code == 200
        assert c.post("/api/surveillance/run").status_code == 200


def test_diagnose_rejects_non_image():
    with TestClient(app) as c:
        r = c.post("/api/diagnose", files=[("images", ("x.jpg", b"notanimage", "image/jpeg"))],
                   data={"lat": "0", "lon": "0"})
        assert r.status_code == 400


def test_diagnose_single_image_flags_unreliable():
    with TestClient(app) as c:
        r = c.post("/api/diagnose", files=[("images", ("l.jpg", _img((40, 160, 40)), "image/jpeg"))],
                   data={"lat": "0.46", "lon": "34.11"})
        assert r.status_code == 200, r.text
        assert r.json()["single_leaf_unreliable"] is True
        assert set(r.json()["advice_all"]) == {"en", "sw"}


def test_diagnose_non_image_friendly_message():
    with TestClient(app) as c:
        r = c.post("/api/diagnose", files=[("images", ("notes.txt", b"hello", "text/plain"))],
                   data={"lat": "0", "lon": "0"})
        assert r.status_code == 400 and "not a readable image" in r.json()["detail"]


def test_diagnose_model_missing_returns_503(monkeypatch):
    from app import inference
    monkeypatch.setattr(inference, "_backend", ("none", None))
    with TestClient(app) as c:
        assert c.get("/health").json()["model_backend"] == "none"
        r = c.post("/api/diagnose", files=[("images", ("l.jpg", _img((40, 160, 40)), "image/jpeg"))],
                   data={"lat": "0", "lon": "0"})
        assert r.status_code == 503 and "model" in r.json()["detail"]
