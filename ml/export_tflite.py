"""Convert models/cassava.keras -> models/cassava.tflite (dynamic-range quantization).

Separate process on purpose: with Keras 3 + TF 2.16, TFLiteConverter.from_keras_model
can hard-abort (LLVM error), so we go through a SavedModel export instead.
"""
import sys
from pathlib import Path

import tensorflow as tf

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def main():
    model = tf.keras.models.load_model(MODEL_DIR / "cassava.keras")
    sm = MODEL_DIR / "saved_model"
    model.export(str(sm))
    conv = tf.lite.TFLiteConverter.from_saved_model(str(sm))
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    out = MODEL_DIR / "cassava.tflite"
    out.write_bytes(conv.convert())
    print(f"[export] tflite={out.stat().st_size / 1e6:.2f} MB", flush=True)


if __name__ == "__main__":
    sys.exit(main())
