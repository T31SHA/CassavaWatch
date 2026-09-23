"""CassavaWatch FastAPI app."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import inference
from .advisory import get_advice
from .models import Alert, Report, get_session, init_db, utcnow
from .surveillance import cell_bounds, run_surveillance

BASE = Path(__file__).resolve().parent
app = FastAPI(title="CassavaWatch")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

MAX_IMAGES = 8


@app.on_event("startup")
def _startup():
    init_db()


# ---------- schemas ----------
class LeafResult(BaseModel):
    label: str
    probs: List[float]


class Advice(BaseModel):
    name: str
    text: str
    lang: str


class DiagnoseOut(BaseModel):
    report_id: int
    label: str
    top_class: str
    confidence: float
    uncertain: bool
    probs: dict
    n_leaves: int
    leaves: List[LeafResult]
    advice: Advice
    backend: str
    new_alerts: int


class ReportOut(BaseModel):
    id: int
    ts: datetime
    lat: float
    lon: float
    crop: str
    disease: str
    confidence: float
    n_leaves: int
    device_id: Optional[str] = None


class AlertOut(BaseModel):
    id: int
    ts: datetime
    region_cell: str
    disease: str
    observed: int
    expected: float
    ratio: float
    p_value: float
    status: str
    bounds: List[List[float]]


def _alert_out(a: Alert) -> AlertOut:
    return AlertOut(id=a.id, ts=a.ts, region_cell=a.region_cell, disease=a.disease,
                    observed=a.observed, expected=a.expected, ratio=a.ratio,
                    p_value=a.p_value, status=a.status, bounds=cell_bounds(a.region_cell))


# ---------- pages ----------
@app.get("/", response_class=HTMLResponse)
def capture_page(request: Request):
    return templates.TemplateResponse(request, "capture.html")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


# ---------- api ----------
@app.get("/health")
def health():
    return {"status": "ok", "model_backend": inference.backend_name()}


@app.post("/api/diagnose", response_model=DiagnoseOut)
async def diagnose(
    images: List[UploadFile] = File(...),
    lat: float = Form(...),
    lon: float = Form(...),
    lang: str = Form("en"),
    device_id: Optional[str] = Form(None),
    s=Depends(get_session),
):
    if not images or len(images) > MAX_IMAGES:
        raise HTTPException(400, f"send 1-{MAX_IMAGES} images")
    leaves = []
    for up in images:
        try:
            leaves.append(inference.predict(await up.read()))
        except Exception:
            raise HTTPException(400, f"could not read image {up.filename!r}")
    plant = inference.aggregate_plant([l["probs"] for l in leaves])
    rep = Report(ts=utcnow(), lat=lat, lon=lon, crop="cassava", disease=plant["label"],
                 confidence=plant["confidence"], n_leaves=plant["n_leaves"], device_id=device_id)
    s.add(rep)
    s.commit()
    before = s.query(Alert).filter(Alert.status == "active").count()
    after = len(run_surveillance(s))
    return DiagnoseOut(report_id=rep.id, leaves=leaves, advice=get_advice(plant["label"], lang),
                       backend=inference.backend_name(), new_alerts=max(0, after - before),
                       **{k: plant[k] for k in ("label", "top_class", "confidence", "uncertain", "probs", "n_leaves")})


@app.get("/api/reports", response_model=List[ReportOut])
def reports(days: int = 60, s=Depends(get_session)):
    since = utcnow() - timedelta(days=days)
    return s.query(Report).filter(Report.ts >= since).order_by(Report.ts.desc()).all()


@app.get("/api/alerts", response_model=List[AlertOut])
def alerts(status: str = "active", s=Depends(get_session)):
    q = s.query(Alert)
    if status != "all":
        q = q.filter(Alert.status == status)
    return [_alert_out(a) for a in q.order_by(Alert.ratio.desc()).all()]


@app.post("/api/alerts/{alert_id}/review", response_model=AlertOut)
def review_alert(alert_id: int, s=Depends(get_session)):
    a = s.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "alert not found")
    a.status = "reviewed"
    s.commit()
    return _alert_out(a)


@app.post("/api/surveillance/run", response_model=List[AlertOut])
def surveillance_run(s=Depends(get_session)):
    return [_alert_out(a) for a in run_surveillance(s)]


@app.get("/api/summary")
def summary(s=Depends(get_session)):
    since = utcnow() - timedelta(days=7)
    recent = s.query(Report).filter(Report.ts >= since).all()
    counts: dict = {}
    for r in recent:
        if r.disease not in ("healthy", "uncertain"):
            counts[r.disease] = counts.get(r.disease, 0) + 1
    top = max(counts, key=counts.get) if counts else None
    return {"reports_7d": len(recent),
            "active_alerts": s.query(Alert).filter(Alert.status == "active").count(),
            "top_disease": top, "top_disease_count": counts.get(top, 0) if top else 0}
