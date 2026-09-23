# CassavaWatch

Mobile-first web app for cassava disease diagnosis and denominator-aware disease surveillance.

- **Farmers / extension officers** (`/`) photograph 3–6 leaves of **one plant**. They get a plant-level
  diagnosis (CBB, CBSD, CGM, CMD or healthy) with treatment advice in **English or Swahili**. If the
  model is unsure they get "uncertain, ask an extension officer" instead. Reports are geotagged. If the
  phone is offline, reports are queued in `localStorage` and synced when it reconnects.
- **Extension officers** (`/dashboard`) see a Leaflet map of reports coloured by disease, red rectangles
  for **anomaly alerts** on a 0.1° grid, and a table of active alerts with a *Mark reviewed* button.

## Quick start

```bash
make setup      # uv venv (Python 3.11) + pip install -r requirements.txt
make test       # pytest
make train      # data fetch + train + export .keras/.tflite + models/eval.json
make seed       # ~400 synthetic reports around Busia (KE) and Mwanza (TZ) + one injected CBSD spike
make run        # http://localhost:8000/  (farmer)   http://localhost:8000/dashboard  (officer)
```

On a slow link, fetch the training subsample first with `python ml/fetch_icassava.py 300 100`
(see "Data" below). Geolocation in mobile browsers needs HTTPS or `localhost`. When neither is
available, the app falls back to a manual district picker.

## Surveillance: why not hotspot clustering

`app/surveillance.py`. Clustering raw report density (DBSCAN/KDE) mostly finds places where there are
many *reporters*, not places with more disease. Instead, for every (0.1° cell, disease):

| quantity | definition |
|---|---|
| observed | positive reports, last 7 days |
| baseline rate | (positives + 1) / (total reports + 5) in the same cell, days 8–60 (Laplace-smoothed) |
| expected | baseline rate × total reports in the cell, last 7 days |
| alert if | observed ≥ 5 **and** Poisson P(X ≥ observed \| expected) < 0.01 **and** observed/expected ≥ 2 |

Reports with confidence < 0.55 are ignored. Because the denominator is the cell's own report volume, a
"field day" that produces 10× the usual number of reports at the usual disease mix does **not** alert.
`tests/test_surveillance.py` has a regression test for this, and the seeded demo includes such a
village near Mwanza. Endemic CMD/CBSD is absorbed by each cell's own baseline. The detector runs after
every new report and on `POST /api/surveillance/run`.

## API

| method | path | |
|---|---|---|
| POST | `/api/diagnose` | multipart: `images` (1–8), `lat`, `lon`, `lang` (en/sw), `device_id` |
| GET | `/api/reports?days=60` | reports |
| GET | `/api/alerts?status=active` | alerts (`active`/`reviewed`/`resolved`/`all`) with Leaflet bounds |
| POST | `/api/alerts/{id}/review` | mark reviewed |
| POST | `/api/surveillance/run` | rerun detector |
| GET | `/api/summary` | dashboard summary strip |
| GET | `/health` | status + which model backend is loaded |

## Model

`ml/train.py`: MobileNetV3Small (ImageNet weights, built-in preprocessing, 224 px). It trains the head
with the backbone frozen, then fine-tunes the top 40 backbone layers with BatchNorm kept frozen.
Augmentation: flips, brightness, small rotation. Class weights are capped at 4×. Exports
`models/cassava.keras` and `models/cassava.tflite` (dynamic-range quantized). It also checks that
TFLite and Keras agree on top-1 and writes per-class accuracy plus a confusion matrix to
`models/eval.json`.

**Data** (PlantVillage is deliberately *not* used: it has no cassava and is lab-biased). iCassava 2019
(TFDS `cassava`, field images from Uganda, 5 classes). The full archive is 1.35 GB. On the slow link
used to build this, `ml/fetch_icassava.py` reads the zip's central directory with HTTP Range requests
and pulls only a class-balanced subsample (default 300 train + 100 test per class, about 240 MB)
from the **same archive TFDS builds from**. `train.py` tries these sources in order: local subsample
→ TFDS (12-minute download timeout) → Kaggle 2020 set in `./data/` → synthetic data, which is logged
loudly as `PLACEHOLDER DATA`.

The app loads `cassava.tflite` if it exists, otherwise `cassava.keras`, otherwise a clearly labelled
colour-heuristic **stub** (`backend: "stub"` in responses) so that the UI still works before training.

### Metrics

METRICS_PLACEHOLDER

## Known limits

- **Single-leaf diagnosis is unreliable.** Published field accuracy for single cassava leaves ranges
  from about 20% to 60%. The UI pushes for 3–6 leaves from top, middle and bottom, averages their
  probabilities, and returns "uncertain" when the top probability is below 0.55.
- **CBSD is often cryptic.** Leaf symptoms can be faint or absent while roots rot. A "healthy" leaf
  result does not rule CBSD out, so root inspection is still needed.
- **Inference is server-side in this MVP.** The quantized `.tflite` export is the path to real
  on-device inference (TFLite / TF.js / Android). Offline mode currently queues reports; it does
  not diagnose offline.
- **Small training subsample** (at most 3,000 images, a few epochs on CPU), and the test set comes from
  the same Ugandan source as training. Expect worse results on other regions, phones and lighting.
- **The dashboard seed data is synthetic** (`scripts/seed_demo.py`). The alert shown is an injected
  CBSD spike, not a real outbreak.
- No auth, no rate limiting, SQLite only, Leaflet/OSM tiles fetched from a CDN.
