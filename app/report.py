"""
診断結果をPDFレポート化するモジュール。

reportlabで直接PDFを組み立てる(pure Python、システムライブラリ不要)。
日本語はreportlab組み込みのCIDフォント(HeiseiKakuGo-W5)を使うため、
フォントファイルの同梱や外部インストールも不要。
WeasyPrintはRenderの標準Python環境だとPango/Cairo等が無くて動かないため、
この方式に切り替えている。
"""
import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from app.database import DiagnosisResult

import os

_FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP.ttf")
pdfmetrics.registerFont(TTFont("NotoSansJP", _FONT_PATH))
FONT = "NotoSansJP"
# <b>タグ等で太字指定されても同じフォントにフォールバックさせる(専用の太字フォントは同梱していないため)
pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT, italic=FONT, boldItalic=FONT)

GOLD = colors.HexColor("#A98548")
WARN = colors.HexColor("#B85B4C")
INK = colors.HexColor("#1B1D24")
MUTED = colors.HexColor("#5B5F6B")
LINE = colors.HexColor("#E4E1D8")

SEO_LABELS = {
    "title": "title タグ",
    "meta_description": "meta description",
    "h1": "h1 タグ",
    "images": "画像の alt 属性",
}
SECURITY_LABELS = {
    "https": "HTTPS化",
    "hsts": "Strict-Transport-Security",
    "x_content_type_options": "X-Content-Type-Options",
    "x_frame_options": "X-Frame-Options",
}

styles = {
    "eyebrow": ParagraphStyle("eyebrow", fontName=FONT, fontSize=8, textColor=GOLD, spaceAfter=6),
    "title": ParagraphStyle("title", fontName=FONT, fontSize=20, textColor=INK, spaceAfter=14, leading=26),
    "meta": ParagraphStyle("meta", fontName=FONT, fontSize=9, textColor=MUTED, leading=14),
    "heading": ParagraphStyle("heading", fontName=FONT, fontSize=12, textColor=INK, spaceAfter=8),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.5, textColor=INK, leading=14),
    "note": ParagraphStyle("note", fontName=FONT, fontSize=8, textColor=MUTED, leading=12),
    "footer": ParagraphStyle("footer", fontName=FONT, fontSize=8, textColor=MUTED, leading=12),
}


def render_report_pdf(row: DiagnosisResult, previous: Optional[DiagnosisResult] = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=28 * mm, bottomMargin=22 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )

    details = row.details_json or {}
    seo_details = details.get("seo", {})
    security_details = details.get("security", {})
    checked_at = row.created_at.strftime("%Y年%m月%d日 %H:%M")

    elements = [
        Paragraph("SATOLAB. / SITE CHECK REPORT", styles["eyebrow"]),
        Paragraph("Webサイト診断レポート", styles["title"]),
        Paragraph(f"対象URL: {row.url}<br/>診断日時: {checked_at}", styles["meta"]),
        Spacer(1, 14),
        _score_table(row, previous),
        Spacer(1, 20),
        _findings_columns(seo_details, security_details),
        Spacer(1, 24),
        Paragraph(
            "このレポートは自動診断ツール「Satolab. Site Check」により生成されました。"
            "診断内容は基本項目の簡易チェックであり、詳細な監査を代替するものではありません。",
            styles["footer"],
        ),
    ]

    doc.build(elements)
    return buffer.getvalue()


def _diff(current: Optional[int], previous: Optional[int]) -> Optional[int]:
    if current is None or previous is None:
        return None
    return current - previous


def _diff_text(diff: Optional[int]) -> str:
    if diff is None:
        return "—"
    if diff == 0:
        return "±0"
    return f"▲ {diff}" if diff > 0 else f"▼ {abs(diff)}"


def _score_table(row: DiagnosisResult, previous: Optional[DiagnosisResult]) -> Table:
    rows_data = [
        ("パフォーマンス", row.performance_score, previous.performance_score if previous else None),
        ("SEO", row.seo_score, previous.seo_score if previous else None),
        ("セキュリティ", row.security_score, previous.security_score if previous else None),
    ]
    header = [
        Paragraph("項目", styles["note"]),
        Paragraph("スコア", styles["note"]),
        Paragraph("前回との差", styles["note"]),
    ]
    body = []
    for label, score, prev in rows_data:
        score_text = f"{score} / 100" if score is not None else "未計測"
        body.append([
            Paragraph(label, styles["body"]),
            Paragraph(f"<b>{score_text}</b>", styles["body"]),
            Paragraph(_diff_text(_diff(score, prev)), styles["note"]),
        ])

    table = Table([header] + body, colWidths=[70 * mm, 50 * mm, 50 * mm])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _findings_columns(seo_details: dict, security_details: dict) -> Table:
    left = [Paragraph("SEO", styles["heading"])] + _findings_flowables(SEO_LABELS, seo_details)
    right = [Paragraph("セキュリティ", styles["heading"])] + _findings_flowables(SECURITY_LABELS, security_details)

    table = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    return table


def _findings_flowables(labels: dict, data: dict) -> list:
    flowables = []
    for key, label in labels.items():
        item = data.get(key)
        if not item:
            continue
        mark = "○" if item.get("ok") else "×"
        color = "#A98548" if item.get("ok") else "#B85B4C"
        text = f'<font color="{color}">{mark}</font>&nbsp;&nbsp;{label}'
        flowables.append(Paragraph(text, styles["body"]))
        note = item.get("note")
        if note:
            flowables.append(Paragraph(note, styles["note"]))
        flowables.append(Spacer(1, 6))
    if not flowables:
        flowables.append(Paragraph("項目なし", styles["note"]))
    return flowables
