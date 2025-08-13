# app/routers/radix_kerykeion.py
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.config import settings

# Kerykeion: spezialisiertes Astrology+SVG Toolkit
from kerykeion import AstrologicalSubject, KerykeionChartSVG  # type: ignore

router = APIRouter(prefix="/v1/radix", tags=["radix"])

class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    alt_m: float = 0.0

class RadixSVGRequest(BaseModel):
    datetime: datetime          # ISO 8601, gern mit Offset
    location: GeoLocation
    house_system: Optional[str] = None  # z.B. "P"
    tz: Optional[str] = None            # z.B. "Europe/Berlin" (fallback Settings)
    name: Optional[str] = "Radix"

def _make_subject(req: RadixSVGRequest) -> AstrologicalSubject:
    dt = req.datetime
    tz_str = req.tz or settings.tz_default
    # Kerykeion erwartet getrennte Zeitkomponenten + lat/lon + tz_str
    return AstrologicalSubject(
        req.name or "Radix",
        dt.year, dt.month, dt.day, dt.hour, dt.minute,
        lng=float(req.location.lon),
        lat=float(req.location.lat),
        tz_str=tz_str,
    )

def _render_wheel_svg(subject: AstrologicalSubject, house_system: Optional[str]) -> str:
    with TemporaryDirectory() as tmp:
        chart = KerykeionChartSVG(
            subject,
            # chart_type z.B. "Natal" (default). Wheel only spart Text-/Aspekt-Layouts.
            new_output_directory=tmp,
            chart_language="DE",
            remove_css_variables=True,   # bessere Kompatibilität beim Einbetten
        )
        # Optional: Häusersystem setzen (Kerykeion unterstützt diverse Systeme)
        if house_system:
            try:
                chart.house_system = house_system  # abhängig von Version
            except Exception:
                pass
        # Wheel-only erzeugen
        chart.makeWheelOnlySVG()

        # frisch erzeugte .svg-Datei lesen
        svgs = sorted(Path(tmp).glob("*.svg"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not svgs:
            raise RuntimeError("Konnte kein SVG erzeugen.")
        return svgs[0].read_text(encoding="utf-8")

@router.post("/svg-kerykeion")
def radix_svg(req: RadixSVGRequest):
    try:
        subj = _make_subject(req)
        svg = _render_wheel_svg(subj, req.house_system or settings.default_house_system)
        return Response(content=svg, media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SVG generation failed: {e}")

@router.post("/html-kerykeion")
def radix_html(req: RadixSVGRequest):
    try:
        subj = _make_subject(req)
        svg = _render_wheel_svg(subj, req.house_system or settings.default_house_system)
        html = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"/>
<title>Radix</title>
<style>
  body{{font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, "Noto Sans", sans-serif; margin:20px}}
  h1{{margin:0 0 10px 0}}
  .meta td{{padding:2px 6px}}
</style></head>
<body>
  <h1>Radix (SVG)</h1>
  <table class="meta">
    <tr><td><b>Datum/Zeit:</b></td><td>{req.datetime.isoformat()}</td></tr>
    <tr><td><b>Ort:</b></td><td>lat {req.location.lat}, lon {req.location.lon}, alt {req.location.alt_m} m</td></tr>
    <tr><td><b>Häusersystem:</b></td><td>{req.house_system or settings.default_house_system}</td></tr>
  </table>
  <div>{svg}</div>
</body></html>"""
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTML generation failed: {e}")
