"""
診断ロジック本体。

- SEO: title / meta description / h1 / img alt をチェック
- セキュリティ: HTTPS化・基本的なセキュリティヘッダーの有無をチェック
- パフォーマンス: Google PageSpeed Insights API（無料・要APIキー）を使用。
  APIキー未設定の場合はNoneを返し、フロント側で「未計測」と表示する。
"""
import os
from typing import Optional

import requests
from bs4 import BeautifulSoup

PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY")
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

REQUEST_TIMEOUT = 10


def run_diagnosis(url: str) -> dict:
    response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "web-diagnostic-tool/0.1"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    seo_score, seo_details = _check_seo(soup)
    security_score, security_details = _check_security(url, response)
    performance_score = _check_performance(url)

    return {
        "scores": {
            "performance": performance_score,
            "seo": seo_score,
            "security": security_score,
        },
        "details": {
            "seo": seo_details,
            "security": security_details,
        },
    }


def _check_seo(soup: BeautifulSoup) -> tuple[int, dict]:
    score = 0
    details = {}

    title_tag = soup.find("title")
    has_title = bool(title_tag and title_tag.text.strip())
    details["title"] = {
        "ok": has_title,
        "value": title_tag.text.strip() if has_title else None,
        "note": "titleタグが見つかりません" if not has_title else None,
    }
    if has_title:
        score += 25

    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_content = meta_desc.get("content", "").strip() if meta_desc else ""
    has_desc = bool(desc_content)
    details["meta_description"] = {
        "ok": has_desc,
        "length": len(desc_content),
        "note": "meta descriptionが見つかりません" if not has_desc else None,
    }
    if has_desc:
        score += 25

    h1_tags = soup.find_all("h1")
    has_one_h1 = len(h1_tags) == 1
    details["h1"] = {
        "ok": has_one_h1,
        "count": len(h1_tags),
        "note": None if has_one_h1 else f"h1タグが{len(h1_tags)}個あります（1個が推奨）",
    }
    if has_one_h1:
        score += 25

    images = soup.find_all("img")
    images_without_alt = [img for img in images if not img.get("alt", "").strip()]
    alt_ratio = 1.0 if not images else 1 - (len(images_without_alt) / len(images))
    details["images"] = {
        "total": len(images),
        "missing_alt": len(images_without_alt),
        "note": (
            f"alt属性のない画像が{len(images_without_alt)}件あります"
            if images_without_alt
            else None
        ),
    }
    score += round(25 * alt_ratio)

    return score, details


def _check_security(url: str, response: requests.Response) -> tuple[int, dict]:
    score = 0
    details = {}

    is_https = url.startswith("https://")
    details["https"] = {"ok": is_https, "note": None if is_https else "HTTPS化されていません"}
    if is_https:
        score += 40

    headers = {k.lower(): v for k, v in response.headers.items()}

    hsts = "strict-transport-security" in headers
    details["hsts"] = {"ok": hsts, "note": None if hsts else "Strict-Transport-Securityヘッダーがありません"}
    if hsts:
        score += 20

    xcto = headers.get("x-content-type-options", "").lower() == "nosniff"
    details["x_content_type_options"] = {
        "ok": xcto,
        "note": None if xcto else "X-Content-Type-Options: nosniff がありません",
    }
    if xcto:
        score += 20

    xfo = "x-frame-options" in headers
    details["x_frame_options"] = {"ok": xfo, "note": None if xfo else "X-Frame-Optionsヘッダーがありません"}
    if xfo:
        score += 20

    return score, details


def _check_performance(url: str) -> Optional[int]:
    if not PAGESPEED_API_KEY:
        return None
    try:
        resp = requests.get(
            PAGESPEED_ENDPOINT,
            params={"url": url, "key": PAGESPEED_API_KEY, "strategy": "mobile"},
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
        score = data["lighthouseResult"]["categories"]["performance"]["score"]
        return round(score * 100)
    except Exception:
        # 取得できなくても他の診断は返したいので、ここは静かに諦める
        return None
