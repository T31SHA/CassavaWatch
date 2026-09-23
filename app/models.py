"""SQLAlchemy models + session helpers (SQLite)."""
import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.environ.get("CASSAVAWATCH_DB", "sqlite:///./cassavawatch.db")

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=utcnow, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    crop = Column(String, default="cassava")
    disease = Column(String, index=True)  # one of CLASSES, or "uncertain"
    confidence = Column(Float)
    n_leaves = Column(Integer, default=1)
    device_id = Column(String, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=utcnow)
    region_cell = Column(String, index=True)  # "lat_idx_lon_idx" on a 0.1° grid
    disease = Column(String)
    observed = Column(Integer)
    expected = Column(Float)
    ratio = Column(Float)
    p_value = Column(Float)
    status = Column(String, default="active")  # active | reviewed | resolved


engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(eng=None) -> None:
    Base.metadata.create_all(eng or engine)


def get_session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
