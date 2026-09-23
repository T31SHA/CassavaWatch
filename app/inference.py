"""Model loading + per-leaf prediction + per-plant aggregation.

Backend preference: models/cassava.tflite -> models/cassava.keras -> heuristic stub.
The stub exists only so the app stays runnable before training finishes; it is
reported as backend="stub" in API responses.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np
from PIL import Image

CLASSES = ["cbb", "cbsd", "cgm", "cmd", "healthy"]  # TFDS `cassava` label order
IMG_SIZE = 224
UNCERTAIN_THRESHOLD = 0.55
MODEL_DIR = Path(os.environ.get("CASSAVAWATCH_MODEL_DIR", Path(__file__).resolve().parent.parent / "models"))

_backend = None  # (kind, callable)


def preprocess(image_bytes: bytes) -> np.ndarray:
    """Bytes -> float32 [1,224,224,3] in 0..255 (MobileNetV3 rescales internally)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    return np.asarray(img, dtype=np.float32)[None, ...]


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _stub_predict(x: np.ndarray) -> np.ndarray:
    # Deterministic colour heuristic: NOT a real classifier.
    m = x[0].reshape(-1, 3).mean(0) / 255.0
    r, g, b = m
    logits = np.array([r - g, (r + g) / 2 - b, g - r * 0.5, (g - b) * 0.8, g - r], dtype=np.float32)
    return _softmax(logits * 3)


def _load():
    global _backend
    if _backend is not None:
        return _backend
    tfl, ker = MODEL_DIR / "cassava.tflite", MODEL_DIR / "cassava.keras"
    if os.environ.get("CASSAVAWATCH_STUB") != "1" and (tfl.exists() or ker.exists()):
        try:
            import tensorflow as tf
            if tfl.exists():
                interp = tf.lite.Interpreter(model_path=str(tfl))
                interp.allocate_tensors()
                inp, out = interp.get_input_details()[0], interp.get_output_details()[0]

                def f(x):
                    interp.set_tensor(inp["index"], x.astype(inp["dtype"]))
                    interp.invoke()
                    return interp.get_tensor(out["index"])[0]
                _backend = ("tflite", f)
            else:
                model = tf.keras.models.load_model(str(ker))
                _backend = ("keras", lambda x: model(x, training=False).numpy()[0])
            return _backend
        except Exception as e:  # pragma: no cover
            print(f"[inference] model load failed ({e}); using stub")
    _backend = ("stub", _stub_predict)
    return _backend


def backend_name() -> str:
    return _load()[0]


def predict(image_bytes: bytes) -> dict:
    _, f = _load()
    probs = np.asarray(f(preprocess(image_bytes)), dtype=np.float64)
    probs = probs / probs.sum()
    return {"label": CLASSES[int(probs.argmax())], "probs": probs.tolist()}


def aggregate_plant(list_of_probs: list[list[float]]) -> dict:
    """Mean the per-leaf probability vectors; 'uncertain' if top prob < threshold."""
    if not list_of_probs:
        raise ValueError("no leaf predictions")
    mean = np.mean(np.asarray(list_of_probs, dtype=np.float64), axis=0)
    top = int(mean.argmax())
    conf = float(mean[top])
    return {
        "label": CLASSES[top] if conf >= UNCERTAIN_THRESHOLD else "uncertain",
        "top_class": CLASSES[top],
        "confidence": conf,
        "probs": {c: float(p) for c, p in zip(CLASSES, mean)},
        "n_leaves": len(list_of_probs),
        "uncertain": conf < UNCERTAIN_THRESHOLD,
    }
