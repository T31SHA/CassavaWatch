"""CassavaWatch FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import inference
from .advisory import get_advice_all
from .config import get_settings
from .llm_advisory import generate_advice
from .models import Alert, Report, SessionLocal, get_session, init_db, utcnow
from .surveillance import cell_bounds, run_surveillance

BASE = Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cassavawatch")


def _seed_if_empty() -> None:
    """SEED_DEMO_DATA=true: on an empty DB (e.g. fresh Render deploy) load synthetic demo reports + alerts."""
    s = SessionLocal()
    try:
        empty = s.query(Report).count() == 0
    finally:
        s.close()
    if empty:
        from scripts import seed_demo
        seed_demo.main()  # seeds reports and runs the surveillance pass


@asynccontextmanager
async def lifespan(_app):
    init_db()
    if get_settings().seed_demo_data:
        _seed_if_empty()
    log.info("model backend=%s advisory mode=%s", inference.backend_name(), get_settings().effective_advisory_mode)
    yield


app = FastAPI(title="CassavaWatch", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

MAX_IMAGES = 8


# ---------- schemas ----------
class LeafResult(BaseModel):
    label: str
    probs: List[float]


class Advice(BaseModel):
    name: str
    text: str
    lang: str
    summary: str
    bullets: List[str]
    source: str = "template"  # "llm" (AI-assisted, Qwen) | "template" (standard guidance)


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
    advice_all: Dict[str, Advice]
    single_leaf_unreliable: bool
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
    model: Optional[str] = Form(None),  # per-request Qwen model override, for demos
    s=Depends(get_session),
):
    if not images or len(images) > MAX_IMAGES:
        raise HTTPException(400, f"Please send between 1 and {MAX_IMAGES} leaf photos.")
    if inference.backend_name() == "none":
        raise HTTPException(503, "Diagnosis is temporarily unavailable: the disease model is not installed "
                                 "on the server. Your report was not saved; please try again later.")
    leaves = []
    for up in images:
        try:
            leaves.append(inference.predict(await up.read()))
        except inference.ModelUnavailable:
            raise HTTPException(503, "Diagnosis is temporarily unavailable: the disease model is not loaded.")
        except Exception:
            raise HTTPException(400, f"'{up.filename}' is not a readable image. "
                                     "Please upload a JPG or PNG photo of a cassava leaf.")
    plant = inference.aggregate_plant([l["probs"] for l in leaves])
    rep = Report(ts=utcnow(), lat=lat, lon=lon, crop="cassava", disease=plant["label"],
                 confidence=plant["confidence"], n_leaves=plant["n_leaves"], device_id=device_id)
    s.add(rep)
    s.commit()
    before = s.query(Alert).filter(Alert.status == "active").count()
    after = len(run_surveillance(s))
    lang = lang if lang in ("en", "sw") else "en"
    advice_all = get_advice_all(plant["label"])
    llm = await run_in_threadpool(generate_advice, plant["label"], plant["confidence"], lang,
                                  plant["n_leaves"], lat, lon, (model or "").strip() or None)
    advice_all[lang] = {**advice_all[lang], "bullets": llm["advice_bullets"], "source": llm["source"]}
    return DiagnoseOut(report_id=rep.id, leaves=leaves, advice=advice_all[lang], advice_all=advice_all,
                       single_leaf_unreliable=plant["n_leaves"] == 1,
                       backend=inference.backend_name(), new_alerts=max(0, after - before),
                       **{k: plant[k] for k in ("label", "top_class", "confidence", "uncertain", "probs", "n_leaves")})


@app.get("/api/config")
def config():
    st = get_settings()
    return {"advisory_mode": st.effective_advisory_mode, "qwen_model": st.qwen_model,
            "qwen_base_url": st.qwen_base_url, "model_backend": inference.backend_name()}


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
