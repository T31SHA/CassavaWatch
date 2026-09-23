"""Download the TFLite model into models/ from $MODEL_URL (e.g. a GitHub Release asset).

Skips if the model is already present. If MODEL_URL is unset and there is no model,
exits 0 anyway: the app still boots, the surveillance dashboard works and
/api/diagnose returns 503 until a model is installed.
"""
import os
import sys
import urllib.request
from pathlib import Path

MODEL_DIR = Path(os.environ.get("CASSAVAWATCH_MODEL_DIR", Path(__file__).resolve().parent.parent / "models"))
TARGET = MODEL_DIR / "cassava.tflite"


def main() -> int:
    if TARGET.exists() and TARGET.stat().st_size > 0:
        print(f"[fetch_model] {TARGET} present ({TARGET.stat().st_size / 1e6:.1f} MB); skipping.")
        return 0
    url = os.environ.get("MODEL_URL", "").strip()
    if not url:
        print("[fetch_model] MODEL_URL not set and no model found; app will boot with /api/diagnose -> 503.")
        return 0
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TARGET.with_suffix(".part")
    print(f"[fetch_model] downloading {url} -> {TARGET}")
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        tmp.replace(TARGET)
    except Exception as e:  # don't fail the build: dashboard should still deploy
        tmp.unlink(missing_ok=True)
        print(f"[fetch_model] download failed ({e}); app will boot with /api/diagnose -> 503.")
        return 0
    print(f"[fetch_model] done ({TARGET.stat().st_size / 1e6:.1f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
