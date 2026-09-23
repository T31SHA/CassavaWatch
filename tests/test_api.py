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
