import io

from PIL import Image

from app.advisory import ADVICE
from app.inference import CLASSES, UNCERTAIN_THRESHOLD, aggregate_plant, predict


def test_classes_match_advisory_keys():
    assert set(CLASSES) == set(ADVICE)
    for c in CLASSES:
        assert ADVICE[c]["en"] and ADVICE[c]["sw"]


def test_aggregate_uncertain_below_threshold():
    leaves = [[0.40, 0.30, 0.10, 0.10, 0.10], [0.45, 0.25, 0.10, 0.10, 0.10]]
    r = aggregate_plant(leaves)
    assert r["confidence"] < UNCERTAIN_THRESHOLD
    assert r["label"] == "uncertain" and r["uncertain"] and r["top_class"] == "cbb"


def test_aggregate_confident_uses_mean():
    leaves = [[0, 0, 0, 0.9, 0.1], [0, 0, 0, 0.7, 0.3], [0, 0, 0.2, 0.6, 0.2]]
    r = aggregate_plant(leaves)
    assert r["label"] == "cmd" and not r["uncertain"] and r["n_leaves"] == 3
    assert abs(r["confidence"] - (0.9 + 0.7 + 0.6) / 3) < 1e-9


def test_predict_returns_distribution():
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (40, 160, 40)).save(buf, "JPEG")
    out = predict(buf.getvalue())
    assert out["label"] in CLASSES and len(out["probs"]) == len(CLASSES)
    assert abs(sum(out["probs"]) - 1) < 1e-4
