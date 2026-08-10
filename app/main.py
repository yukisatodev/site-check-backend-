"""
Web診断ツール — FastAPI backend

Endpoints:
  POST /api/diagnose      URLを診断し、結果をDBに保存して返す（前回との差分つき）
  GET  /api/history/{url} 指定URLの過去の診断結果一覧を返す

Run locally:
  pip install -r requirements.txt
  uvicorn app.main:app --reload
"""
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl

from app.database import SessionLocal, init_db, DiagnosisResult
from app.diagnostics import run_diagnosis
from app.report import render_report_pdf

app = FastAPI(title="Web診断ツール API")

# フロントエンド(別オリジン)から叩けるようにCORSを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番では自分のフロントのドメインに絞る
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


class DiagnoseRequest(BaseModel):
    url: HttpUrl


class ScoreBlock(BaseModel):
    performance: Optional[int] = None
    seo: int
    security: int


class DiagnoseResponse(BaseModel):
    id: int
    url: str
    checked_at: datetime
    scores: ScoreBlock
    details: dict
    previous: Optional[ScoreBlock] = None
    diff: Optional[dict] = None


@app.post("/api/diagnose", response_model=DiagnoseResponse)
def diagnose(payload: DiagnoseRequest):
    url = str(payload.url)

    try:
        result = run_diagnosis(url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"診断に失敗しました: {e}")

    db = SessionLocal()
    try:
        # 同じURLの直近の結果を取得（差分表示用）
        previous_row = (
            db.query(DiagnosisResult)
            .filter(DiagnosisResult.url == url)
            .order_by(DiagnosisResult.created_at.desc())
            .first()
        )

        row = DiagnosisResult(
            url=url,
            created_at=datetime.utcnow(),
            performance_score=result["scores"]["performance"],
            seo_score=result["scores"]["seo"],
            security_score=result["scores"]["security"],
            details_json=result["details"],
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        previous = None
        diff = None
        if previous_row:
            previous = {
                "performance": previous_row.performance_score,
                "seo": previous_row.seo_score,
                "security": previous_row.security_score,
            }
            diff = {
                "performance": _safe_diff(result["scores"]["performance"], previous_row.performance_score),
                "seo": result["scores"]["seo"] - previous_row.seo_score,
                "security": result["scores"]["security"] - previous_row.security_score,
            }

        return DiagnoseResponse(
            id=row.id,
            url=url,
            checked_at=row.created_at,
            scores=result["scores"],
            details=result["details"],
            previous=previous,
            diff=diff,
        )
    finally:
        db.close()


@app.get("/api/report/{result_id}")
def report(result_id: int):
    db = SessionLocal()
    try:
        row = db.query(DiagnosisResult).filter(DiagnosisResult.id == result_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="診断結果が見つかりません")

        # 同じURLの前回結果があれば、レポートにも差分を載せる
        previous_row = (
            db.query(DiagnosisResult)
            .filter(DiagnosisResult.url == row.url, DiagnosisResult.id < row.id)
            .order_by(DiagnosisResult.created_at.desc())
            .first()
        )

        pdf_bytes = render_report_pdf(row, previous_row)
        filename = f"site-check-report-{row.id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        db.close()


@app.get("/api/history/{url:path}")
def history(url: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(DiagnosisResult)
            .filter(DiagnosisResult.url == url)
            .order_by(DiagnosisResult.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "checked_at": r.created_at,
                "performance": r.performance_score,
                "seo": r.seo_score,
                "security": r.security_score,
            }
            for r in rows
        ]
    finally:
        db.close()


def _safe_diff(current: Optional[int], previous: Optional[int]) -> Optional[int]:
    if current is None or previous is None:
        return None
    return current - previous
