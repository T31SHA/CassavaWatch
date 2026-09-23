"""Seed SQLite with ~400 synthetic reports around Busia (KE) and Mwanza (TZ).

Endemic CMD/CBSD background over 60 days, a high-volume 'field day' village
(tests reporter-bias robustness), plus ONE injected CBSD spike in a single
0.1° cell near Busia in the last 7 days.  SYNTHETIC DATA — for demo only.
"""
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Alert, Report, SessionLocal, init_db, utcnow  # noqa: E402
from app.surveillance import run_surveillance  # noqa: E402

SEED = 7
VILLAGES = {
    "busia": [(0.462, 34.112), (0.552, 34.205), (0.381, 34.028)],
    "mwanza": [(-2.518, 32.902), (-2.605, 33.018), (-2.448, 32.815)],
}
ENDEMIC = {
    "busia": {"healthy": 0.45, "cmd": 0.30, "cbsd": 0.12, "cgm": 0.08, "cbb": 0.05},
    "mwanza": {"healthy": 0.40, "cmd": 0.20, "cbsd": 0.25, "cgm": 0.10, "cbb": 0.05},
}
SPIKE_CELL_CENTRE = (0.45, 34.15)  # cell 4_341 (lat 0.4–0.5, lon 34.1–34.2)
FIELD_DAY_VILLAGE = (-2.448, 32.815)


def _conf(rng):
    # ~10% low-confidence noise below the 0.55 surveillance cut-off
    return round(rng.uniform(0.30, 0.54), 3) if rng.random() < 0.10 else round(rng.uniform(0.58, 0.98), 3)


def _pick(rng, mix):
    return rng.choices(list(mix), weights=list(mix.values()))[0]


def make_reports(now=None, seed=SEED):
    rng = random.Random(seed)
    now = now or utcnow()
    out = []

    def add(lat, lon, disease, days_ago, dev):
        out.append(Report(ts=now - timedelta(days=days_ago, minutes=rng.randint(0, 600)),
                          lat=round(lat, 5), lon=round(lon, 5), crop="cassava", disease=disease,
                          confidence=_conf(rng), n_leaves=rng.randint(3, 6), device_id=dev))

    # endemic background: 300 reports over 60 days
    for i in range(300):
        region = "busia" if i % 2 == 0 else "mwanza"
        vlat, vlon = rng.choice(VILLAGES[region])
        add(vlat + rng.gauss(0, 0.025), vlon + rng.gauss(0, 0.025),
            _pick(rng, ENDEMIC[region]), rng.uniform(0, 59.5), f"dev-{region}-{rng.randint(1, 25)}")

    # field day: 70 extra reports in last 7 days, baseline-consistent -> must NOT alert
    for _ in range(70):
        add(FIELD_DAY_VILLAGE[0] + rng.uniform(-0.03, 0.03), FIELD_DAY_VILLAGE[1] + rng.uniform(-0.03, 0.03),
            _pick(rng, ENDEMIC["mwanza"]), rng.uniform(0, 6.5), "dev-fieldday")

    # injected CBSD spike: 30 reports in one cell, last 7 days
    for _ in range(30):
        add(SPIKE_CELL_CENTRE[0] + rng.uniform(-0.04, 0.04), SPIKE_CELL_CENTRE[1] + rng.uniform(-0.04, 0.04),
            "cbsd" if rng.random() < 0.8 else _pick(rng, ENDEMIC["busia"]), rng.uniform(0, 6.5),
            f"dev-busia-{rng.randint(1, 25)}")
    return out


def main():
    init_db()
    s = SessionLocal()
    s.query(Alert).delete()
    s.query(Report).delete()
    s.commit()
    reps = make_reports()
    s.add_all(reps)
    s.commit()
    alerts = run_surveillance(s)
    print(f"Seeded {len(reps)} synthetic reports (SYNTHETIC DEMO DATA).")
    print(f"Alerts raised: {len(alerts)}")
    for a in alerts:
        print(f"  cell {a.region_cell} {a.disease}: observed={a.observed} expected={a.expected:.2f} "
              f"ratio={a.ratio:.1f} p={a.p_value:.2e}")
    s.close()


if __name__ == "__main__":
    main()
