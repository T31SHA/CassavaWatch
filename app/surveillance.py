"""Denominator-aware disease-incidence anomaly detection.

Why not density clustering (DBSCAN, KDE hotspots, ...)?

* Reporter bias: raw report density clusters wherever active users live
  (a keen extension officer, a village with good signal). A "hotspot" of
  reports is usually a hotspot of *reporting*, not of disease. We therefore
  work with *proportions*: positives / all reports in the same cell and window.
  The total report count is the denominator that absorbs reporting effort.
* Endemic baseline: CMD and CBSD are endemic across East Africa. A cell that
  always has 30% CMD is not news. We compare each cell's last 7 days against
  its *own* history (days 8-60), so only departures from local normal alert.
* Label noise: the classifier is wrong a fair fraction of the time, so we drop
  low-confidence reports (< MIN_CONFIDENCE) and demand both statistical
  significance (Poisson tail p < 0.01) and a practically meaningful excess
  (observed >= 5 and observed/expected >= 2) before alerting.

Model, per (cell, disease):
    observed      = positives in last 7 days
    baseline_rate = (pos_hist + 1) / (total_hist + 5)     # Laplace-smoothed, days 8-60
    expected      = baseline_rate * total reports in cell, last 7 days
    p             = P(X >= observed),  X ~ Poisson(expected)
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

CELL_DEG = 0.1
RECENT_DAYS = 7
HISTORY_DAYS = 60
MIN_CONFIDENCE = 0.55
MIN_OBSERVED = 5
MAX_P = 0.01
MIN_RATIO = 2.0
DISEASES = ("cbb", "cbsd", "cgm", "cmd")  # "healthy" is never an alert


@dataclass
class Obs:
    ts: datetime
    lat: float
    lon: float
    disease: str
    confidence: float


@dataclass
class Detection:
    region_cell: str
    disease: str
    observed: int
    expected: float
    ratio: float
    p_value: float


def cell_of(lat: float, lon: float) -> str:
    return f"{math.floor(lat / CELL_DEG)}_{math.floor(lon / CELL_DEG)}"


def cell_bounds(cell: str) -> list[list[float]]:
    """[[south, west], [north, east]] for Leaflet."""
    i, j = (int(x) for x in cell.split("_"))
    return [[round(i * CELL_DEG, 4), round(j * CELL_DEG, 4)],
            [round((i + 1) * CELL_DEG, 4), round((j + 1) * CELL_DEG, 4)]]


def poisson_sf(k: int, lam: float) -> float:
    """P(X >= k) for X ~ Poisson(lam)."""
    if k <= 0:
        return 1.0
    if lam <= 0:
        return 0.0
    # 1 - P(X <= k-1)
    term = math.exp(-lam)
    cdf = term
    for i in range(1, k):
        term *= lam / i
        cdf += term
    return max(0.0, 1.0 - cdf)


def detect(reports: Iterable, now: datetime | None = None) -> list[Detection]:
    """Pure detector over any objects with ts/lat/lon/disease/confidence."""
    now = now or datetime.utcnow()
    recent_start = now - timedelta(days=RECENT_DAYS)
    hist_start = now - timedelta(days=HISTORY_DAYS)

    recent_total: dict[str, int] = defaultdict(int)
    hist_total: dict[str, int] = defaultdict(int)
    recent_pos: dict[tuple[str, str], int] = defaultdict(int)
    hist_pos: dict[tuple[str, str], int] = defaultdict(int)

    for r in reports:
        if r.confidence is None or r.confidence < MIN_CONFIDENCE:
            continue
        if r.ts > now or r.ts < hist_start:
            continue
        c = cell_of(r.lat, r.lon)
        if r.ts >= recent_start:
            recent_total[c] += 1
            recent_pos[(c, r.disease)] += 1
        else:
            hist_total[c] += 1
            hist_pos[(c, r.disease)] += 1

    out: list[Detection] = []
    for c, n_recent in recent_total.items():
        for d in DISEASES:
            observed = recent_pos.get((c, d), 0)
            if observed < MIN_OBSERVED:
                continue
            rate = (hist_pos.get((c, d), 0) + 1) / (hist_total.get(c, 0) + 5)
            expected = rate * n_recent
            ratio = observed / expected if expected > 0 else float("inf")
            p = poisson_sf(observed, expected)
            if p < MAX_P and ratio >= MIN_RATIO:
                out.append(Detection(c, d, observed, round(expected, 3),
                                     round(ratio, 3), p))
    return sorted(out, key=lambda x: -x.ratio)


def run_surveillance(session, now: datetime | None = None) -> list:
    """Run detector over the DB and upsert Alerts. Returns active alerts."""
    from .models import Alert, Report

    now = now or datetime.utcnow()
    rows = session.query(Report).filter(
        Report.ts >= now - timedelta(days=HISTORY_DAYS)).all()
    dets = detect(rows, now)
    fired = {(d.region_cell, d.disease): d for d in dets}

    existing = session.query(Alert).filter(Alert.status.in_(["active", "reviewed"])).all()
    seen = set()
    for a in existing:
        key = (a.region_cell, a.disease)
        if key in fired:
            d = fired[key]
            a.observed, a.expected, a.ratio, a.p_value = d.observed, d.expected, d.ratio, d.p_value
            seen.add(key)
        elif a.status == "active":
            a.status = "resolved"
    for key, d in fired.items():
        if key not in seen:
            session.add(Alert(ts=now, region_cell=d.region_cell, disease=d.disease,
                              observed=d.observed, expected=d.expected, ratio=d.ratio,
                              p_value=d.p_value, status="active"))
    session.commit()
    return session.query(Alert).filter(Alert.status == "active").all()
