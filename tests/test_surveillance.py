from datetime import datetime, timedelta

from app.surveillance import Obs, cell_of, detect, poisson_sf

NOW = datetime(2026, 9, 1, 12, 0)
# cell centres (0.1° grid)
A, B, C = (0.45, 34.15), (0.55, 34.25), (-2.55, 32.95)


def block(center, n, mix, days_ago_range, conf=0.9):
    """Deterministic reports: `mix` = {disease: fraction}, remainder healthy."""
    lat, lon = center
    lo, hi = days_ago_range
    labels = []
    for d, frac in mix.items():
        labels += [d] * int(round(n * frac))
    labels += ["healthy"] * (n - len(labels))
    out = []
    for i, d in enumerate(labels):
        days = lo + (hi - lo) * (i + 0.5) / n
        out.append(Obs(NOW - timedelta(days=days), lat + ((i % 7) - 3) * 0.005,
                       lon + ((i % 5) - 2) * 0.005, d, conf))
    return out


ENDEMIC = {"cmd": 0.25, "cbsd": 0.10, "cgm": 0.05}


def endemic_world():
    obs = []
    for c in (A, B, C):
        obs += block(c, 200, ENDEMIC, (8, 59))   # history
        obs += block(c, 30, ENDEMIC, (0, 6.9))   # last 7 days
    return obs


def test_poisson_sf():
    assert poisson_sf(0, 3.0) == 1.0
    assert abs(poisson_sf(1, 2.0) - (1 - 2.718281828 ** -2)) < 1e-6
    assert poisson_sf(20, 2.0) < 1e-8


def test_injected_spike_gives_exactly_one_alert_in_right_cell():
    obs = endemic_world() + block(B, 15, {"cbsd": 1.0}, (0, 6.9))
    alerts = detect(obs, NOW)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.region_cell == cell_of(*B)
    assert a.disease == "cbsd"
    assert a.observed == 18 and a.ratio >= 2 and a.p_value < 0.01


def test_uniform_endemic_gives_zero_alerts():
    assert detect(endemic_world(), NOW) == []


def test_reporter_bias_high_volume_baseline_consistent_no_alert():
    # A 'field day' cell: 500 reports in the last week (vs ~27/week historically),
    # 30% CMD both before and now. Density clustering would flag this; we must not.
    obs = endemic_world()
    obs += block((0.35, 34.05), 200, {"cmd": 0.30}, (8, 59))
    obs += block((0.35, 34.05), 500, {"cmd": 0.30}, (0, 6.9))
    assert detect(obs, NOW) == []


def test_low_confidence_reports_ignored():
    obs = endemic_world() + block(B, 15, {"cbsd": 1.0}, (0, 6.9), conf=0.40)
    assert detect(obs, NOW) == []
