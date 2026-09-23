"""Train a cassava disease classifier (MobileNetV3Small, ImageNet init).

Data priority:
  1. TFDS `cassava` (iCassava 2019, field images from Uganda; 5 classes)
  2. Kaggle 2020 cassava set at ./data/ (train.csv + train_images/)
  3. Synthetic PLACEHOLDER DATA (so the pipeline still runs end to end)

Outputs: models/cassava.keras, models/cassava.tflite (dynamic-range quantized),
models/eval.json (overall + per-class accuracy, confusion matrix).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.inference import CLASSES, IMG_SIZE  # noqa: E402

DATA_DIR = ROOT / "data"
TFDS_DIR = DATA_DIR / "tfds"
MODEL_DIR = ROOT / "models"
MAX_TRAIN = int(os.environ.get("MAX_TRAIN", 3000))
MAX_EVAL = int(os.environ.get("MAX_EVAL", 1000))
EPOCHS_HEAD = int(os.environ.get("EPOCHS_HEAD", 2))
EPOCHS_FT = int(os.environ.get("EPOCHS_FT", 2))
DOWNLOAD_TIMEOUT_S = int(os.environ.get("DOWNLOAD_TIMEOUT_S", 12 * 60))
BATCH = 32
SEED = 42


def _tfds_prepare():
    import tensorflow_datasets as tfds
    b = tfds.builder("cassava", data_dir=str(TFDS_DIR))
    b.download_and_prepare()


def load_tfds(tf):
    import tensorflow_datasets as tfds
    try:
        tfds.builder("cassava", data_dir=str(TFDS_DIR)).info  # noqa: B018
        ready = tfds.builder("cassava", data_dir=str(TFDS_DIR)).is_prepared() if hasattr(
            tfds.core.DatasetBuilder, "is_prepared") else False
    except Exception:
        ready = False
    if not ready:
        print(f"[data] downloading TFDS cassava (timeout {DOWNLOAD_TIMEOUT_S}s)...", flush=True)
        p = mp.get_context("spawn").Process(target=_tfds_prepare)
        p.start()
        p.join(DOWNLOAD_TIMEOUT_S)
        if p.is_alive():
            p.terminate()
            raise TimeoutError("TFDS download timed out")
        if p.exitcode != 0:
            raise RuntimeError(f"TFDS prepare failed (exit {p.exitcode})")
    tr, te = tfds.load("cassava", split=["train", "test"], data_dir=str(TFDS_DIR),
                       as_supervised=True, shuffle_files=True, download=False)
    return tr, te, "tfds:cassava (iCassava 2019)"


def load_kaggle(tf):
    import csv
    csv_path, img_dir = DATA_DIR / "train.csv", DATA_DIR / "train_images"
    if not csv_path.exists() or not img_dir.exists():
        raise FileNotFoundError("no Kaggle cassava set in ./data")
    rows = list(csv.DictReader(open(csv_path)))
    rng = np.random.default_rng(SEED)
    rng.shuffle(rows)
    paths = [str(img_dir / r["image_id"]) for r in rows]
    labels = [int(r["label"]) for r in rows]  # 0 CBB,1 CBSD,2 CGM,3 CMD,4 Healthy == CLASSES order
    n_te = min(MAX_EVAL, len(rows) // 5)

    def mk(p, l):
        ds = tf.data.Dataset.from_tensor_slices((p, l))
        return ds.map(lambda x, y: (tf.io.decode_jpeg(tf.io.read_file(x), channels=3), y),
                      num_parallel_calls=tf.data.AUTOTUNE)
    return mk(paths[n_te:], labels[n_te:]), mk(paths[:n_te], labels[:n_te]), "kaggle-2020 (./data)"


def load_placeholder(tf):
    print("=" * 60 + "\n  PLACEHOLDER DATA — synthetic images, model is NOT meaningful\n" + "=" * 60, flush=True)
    rng = np.random.default_rng(SEED)

    def make(n):
        y = rng.integers(0, len(CLASSES), n)
        base = np.array([[120, 90, 60], [150, 140, 60], [180, 200, 90], [200, 210, 60], [40, 140, 40]])
        x = np.clip(base[y][:, None, None, :] + rng.normal(0, 30, (n, 64, 64, 3)), 0, 255).astype("uint8")
        return tf.data.Dataset.from_tensor_slices((x, y.astype("int64")))
    return make(600), make(200), "PLACEHOLDER DATA (synthetic)"


def build_model(tf):
    keras = tf.keras
    base = keras.applications.MobileNetV3Small(input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False,
                                               weights="imagenet", pooling="avg", include_preprocessing=True)
    base.trainable = False
    inp = keras.Input((IMG_SIZE, IMG_SIZE, 3))
    x = base(inp, training=False)
    x = keras.layers.Dropout(0.2)(x)
    out = keras.layers.Dense(len(CLASSES), activation="softmax")(x)
    return keras.Model(inp, out), base


def main():
    t0 = time.time()
    import tensorflow as tf
    tf.random.set_seed(SEED)
    MODEL_DIR.mkdir(exist_ok=True)

    src = None
    for loader in (load_tfds, load_kaggle, load_placeholder):
        try:
            tr, te, src = loader(tf)
            break
        except Exception as e:
            print(f"[data] {loader.__name__} unavailable: {e}", flush=True)
    print(f"[data] source = {src}", flush=True)

    def resize(x, y):
        return tf.cast(tf.image.resize(x, (IMG_SIZE, IMG_SIZE)), tf.uint8), y

    # subsample + cache as uint8 224px
    tr = tr.map(resize, num_parallel_calls=tf.data.AUTOTUNE).take(MAX_TRAIN).cache()
    te = te.map(resize, num_parallel_calls=tf.data.AUTOTUNE).take(MAX_EVAL).cache()
    y_tr = np.array([int(y) for _, y in tr.as_numpy_iterator()])
    counts = np.bincount(y_tr, minlength=len(CLASSES))
    print(f"[data] train n={len(y_tr)} per-class={dict(zip(CLASSES, counts.tolist()))} "
          f"({time.time() - t0:.0f}s)", flush=True)
    cw = {i: float(min(4.0, len(y_tr) / (len(CLASSES) * max(c, 1)))) for i, c in enumerate(counts)}

    def augment(x, y):
        x = tf.cast(x, tf.float32)
        x = tf.image.random_flip_left_right(x)
        x = tf.image.random_flip_up_down(x)
        x = tf.image.random_brightness(x, 25.0)
        return tf.clip_by_value(x, 0, 255), y

    rot = tf.keras.layers.RandomRotation(0.05)  # small rotation (~±18°)
    train_ds = (tr.shuffle(1000, seed=SEED).map(augment, num_parallel_calls=tf.data.AUTOTUNE)
                .batch(BATCH).map(lambda x, y: (rot(x, training=True), y)).prefetch(tf.data.AUTOTUNE))
    test_ds = te.map(lambda x, y: (tf.cast(x, tf.float32), y)).batch(BATCH).prefetch(tf.data.AUTOTUNE)

    model, base = build_model(tf)
    model.compile(tf.keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_ds, epochs=EPOCHS_HEAD, class_weight=cw, verbose=2)

    # fine-tune top of backbone (keep BatchNorm frozen)
    base.trainable = True
    for layer in base.layers[:-40]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
    model.compile(tf.keras.optimizers.Adam(1e-4), "sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_ds, epochs=EPOCHS_FT, class_weight=cw, verbose=2)

    # evaluate
    y_true, y_pred = [], []
    for x, y in test_ds:
        y_true += y.numpy().tolist()
        y_pred += model(x, training=False).numpy().argmax(1).tolist()
    cm = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    per_class = {c: (float(cm[i, i] / cm[i].sum()) if cm[i].sum() else None) for i, c in enumerate(CLASSES)}
    acc = float(np.trace(cm) / cm.sum())

    # export
    keras_path, tfl_path = MODEL_DIR / "cassava.keras", MODEL_DIR / "cassava.tflite"
    model.save(keras_path)
    try:
        conv = tf.lite.TFLiteConverter.from_keras_model(model)
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
        tfl = conv.convert()
    except Exception as e:
        print(f"[export] from_keras_model failed ({e}); trying SavedModel path", flush=True)
        sm = MODEL_DIR / "saved_model"
        model.export(str(sm))
        conv = tf.lite.TFLiteConverter.from_saved_model(str(sm))
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
        tfl = conv.convert()
    tfl_path.write_bytes(tfl)

    # tflite vs keras agreement on eval set
    interp = tf.lite.Interpreter(model_content=tfl)
    interp.allocate_tensors()
    ii, oo = interp.get_input_details()[0], interp.get_output_details()[0]
    agree = n = 0
    for x, _ in test_ds.unbatch().batch(1).take(100):
        interp.set_tensor(ii["index"], x.numpy())
        interp.invoke()
        agree += int(interp.get_tensor(oo["index"]).argmax() == model(x, training=False).numpy().argmax())
        n += 1

    ev = {
        "data_source": src, "placeholder": src.startswith("PLACEHOLDER"),
        "n_train": int(len(y_tr)), "n_eval": int(cm.sum()), "classes": CLASSES,
        "accuracy": acc, "per_class_accuracy": per_class, "confusion_matrix": cm.tolist(),
        "confusion_matrix_note": "rows=true, cols=predicted",
        "keras_size_mb": round(keras_path.stat().st_size / 1e6, 2),
        "tflite_size_mb": round(tfl_path.stat().st_size / 1e6, 2),
        "tflite_keras_top1_agreement": agree / max(n, 1),
        "train_seconds": round(time.time() - t0),
    }
    (MODEL_DIR / "eval.json").write_text(json.dumps(ev, indent=2))
    print(json.dumps(ev, indent=2))
    print(f"[export] keras={ev['keras_size_mb']} MB  tflite={ev['tflite_size_mb']} MB")


if __name__ == "__main__":
    main()
