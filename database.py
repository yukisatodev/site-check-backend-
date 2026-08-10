"""
DB定義。まずはローカルSQLiteで動かす想定。
クラウドに載せる際はDATABASE_URLをTurso/Postgres等に差し替えればよい構成にしてある。
"""
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./diagnostics.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DiagnosisResult(Base):
    __tablename__ = "diagnosis_results"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    performance_score = Column(Integer, nullable=True)
    seo_score = Column(Integer, nullable=False)
    security_score = Column(Integer, nullable=False)

    details_json = Column(JSON, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)
