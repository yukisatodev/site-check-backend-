"""
診断結果をPDFレポート化するモジュール。

WeasyPrintでHTML文字列をそのままPDFに変換する。
テンプレートエンジンは使わず、f-stringで組み立てる（依存を増やさないため）。
"""
from datetime import datetime
from typing import Optional

from weasyprint import HTML

from app.database import DiagnosisResult

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


def render_report_pdf(row: DiagnosisResult, previous: Optional[DiagnosisResult] = None) -> bytes:
    html = _build_html(row, previous)
    return HTML(string=html).write_pdf()


def _build_html(row: DiagnosisResult, previous: Optional[DiagnosisResult]) -> str:
    details = row.details_json or {}
    seo_details = details.get("seo", {})
    security_details = details.get("security", {})

    checked_at = row.created_at.strftime("%Y年%m月%d日 %H:%M")

    scores_html = "".join(
        _score_row(label, score, _diff(score, prev))
        for label, score, prev in [
            ("パフォーマンス", row.performance_score, previous.performance_score if previous else None),
            ("SEO", row.seo_score, previous.seo_score if previous else None),
            ("セキュリティ", row.security_score, previous.security_score if previous else None),
        ]
    )

    seo_rows = "".join(_finding_row(SEO_LABELS[k], seo_details.get(k)) for k in SEO_LABELS if seo_details.get(k))
    security_rows = "".join(
        _finding_row(SECURITY_LABELS[k], security_details.get(k)) for k in SECURITY_LABELS if security_details.get(k)
    )

    return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 28mm 20mm;
    @bottom-center {{
      content: "Satolab. Site Check Report";
      font-family: 'Noto Sans JP', sans-serif;
      font-size: 8pt;
      color: #9CA0AC;
    }}
  }}
  body {{
    font-family: 'Noto Sans JP', sans-serif;
    color: #1B1D24;
    font-size: 10.5pt;
    line-height: 1.7;
  }}
  h1 {{
    font-size: 20pt;
    margin: 0 0 6pt;
    color: #1B1D24;
  }}
  .eyebrow {{
    font-family: monospace;
    font-size: 8pt;
    letter-spacing: 0.1em;
    color: #C9A15A;
    margin-bottom: 6pt;
  }}
  .meta {{
    font-size: 9pt;
    color: #5B5F6B;
    margin-bottom: 26pt;
    border-bottom: 1pt solid #E4E1D8;
    padding-bottom: 14pt;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 26pt;
  }}
  th {{
    text-align: left;
    font-size: 8pt;
    letter-spacing: 0.06em;
    color: #5B5F6B;
    border-bottom: 1pt solid #1B1D24;
    padding-bottom: 6pt;
    text-transform: uppercase;
  }}
  td {{
    padding: 9pt 0;
    border-bottom: 0.5pt solid #E4E1D8;
    font-size: 10.5pt;
  }}
  .score-value {{ font-weight: 700; font-size: 13pt; }}
  .diff-up {{ color: #A98548; }}
  .diff-down {{ color: #B85B4C; }}
  .diff-flat {{ color: #9CA0AC; }}
  h2 {{
    font-size: 12pt;
    margin: 0 0 10pt;
    padding-top: 4pt;
    color: #1B1D24;
  }}
  .finding {{
    display: flex;
    padding: 7pt 0;
    border-bottom: 0.5pt solid #EFEDE6;
    font-size: 9.5pt;
  }}
  .finding .ok {{ color: #A98548; font-weight: 700; margin-right: 8pt; }}
  .finding .warn {{ color: #B85B4C; font-weight: 700; margin-right: 8pt; }}
  .finding .label {{ font-weight: 500; }}
  .finding .note {{ color: #5B5F6B; display: block; font-size: 8.5pt; margin-top: 2pt; }}
  .columns {{
    display: flex;
    gap: 24pt;
  }}
  .column {{ flex: 1; }}
  footer.note {{
    margin-top: 30pt;
    font-size: 8pt;
    color: #9CA0AC;
  }}
</style>
</head>
<body>
  <div class="eyebrow">SATOLAB. / SITE CHECK REPORT</div>
  <h1>Webサイト診断レポート</h1>
  <div class="meta">
    対象URL: {row.url}<br>
    診断日時: {checked_at}
  </div>

  <table>
    <thead>
      <tr><th>項目</th><th>スコア</th><th>前回との差</th></tr>
    </thead>
    <tbody>
      {scores_html}
    </tbody>
  </table>

  <div class="columns">
    <div class="column">
      <h2>SEO</h2>
      {seo_rows or '<p style="color:#9CA0AC; font-size:9pt;">項目なし</p>'}
    </div>
    <div class="column">
      <h2>セキュリティ</h2>
      {security_rows or '<p style="color:#9CA0AC; font-size:9pt;">項目なし</p>'}
    </div>
  </div>

  <footer class="note">
    このレポートは自動診断ツール「Satolab. Site Check」により生成されました。診断内容は基本項目の簡易チェックであり、詳細な監査を代替するものではありません。
  </footer>
</body>
</html>
"""


def _score_row(label: str, score: Optional[int], diff: Optional[int]) -> str:
    score_text = f"{score} / 100" if score is not None else "未計測"
    diff_html = _diff_html(diff)
    return f"<tr><td>{label}</td><td class='score-value'>{score_text}</td><td>{diff_html}</td></tr>"


def _diff(current: Optional[int], previous: Optional[int]) -> Optional[int]:
    if current is None or previous is None:
        return None
    return current - previous


def _diff_html(diff: Optional[int]) -> str:
    if diff is None:
        return "<span style='color:#9CA0AC;'>—</span>"
    if diff == 0:
        return "<span class='diff-flat'>±0</span>"
    if diff > 0:
        return f"<span class='diff-up'>▲ {diff}</span>"
    return f"<span class='diff-down'>▼ {abs(diff)}</span>"


def _finding_row(label: str, item: Optional[dict]) -> str:
    if not item:
        return ""
    icon_class = "ok" if item.get("ok") else "warn"
    icon = "✓" if item.get("ok") else "!"
    note = item.get("note")
    note_html = f"<span class='note'>{note}</span>" if note else ""
    return (
        f"<div class='finding'><span class='{icon_class}'>{icon}</span>"
        f"<span><span class='label'>{label}</span>{note_html}</span></div>"
    )
