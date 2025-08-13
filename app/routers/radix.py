from __future__ import annotations
import math
from typing import Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, HTMLResponse
from app.deps import get_provider
from app.services.provider import EphemerisProvider
from app.models.schemas import CalcRequest
from app.config import settings
import swisseph as swe
from app.config import settings

if settings.se_ephe_path:
    swe.set_ephe_path(settings.se_ephe_path)

router = APIRouter(prefix="/v1/radix", tags=["radix"])

ZODIAC = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
ZGLYPH = ["\u2648","\u2649","\u264A","\u264B","\u264C","\u264D","\u264E","\u264F","\u2650","\u2651","\u2652","\u2653"]
PLAN_ABBR = {
    "sun":"Su","moon":"Mo","mercury":"Me","venus":"Ve","mars":"Ma","jupiter":"Ju","saturn":"Sa",
    "uranus":"Ur","neptune":"Ne","pluto":"Pl","chiron":"Ch","north_node":"NN","south_node":"SN"
}
PLAN_GLYPH = {
    "sun":"\u2609","moon":"\u263D","mercury":"\u263F","venus":"\u2640","mars":"\u2642",
    "jupiter":"\u2643","saturn":"\u2644","uranus":"\u2645","neptune":"\u2646","pluto":"\u2647",
    "chiron":"\u26B7","north_node":"\u260A","south_node":"\u260B"
}

def _angle_deg(longitude: float, asc: float) -> float:
    """
    Mapping ekliptische Länge -> Bildschirmwinkel (Grad):
    - Ascendant liegt bei 180° (links, 9-Uhr-Position)
    - MC liegt oben (90°), DC rechts (0°), IC unten (270°)
    """
    return (180.0 - (longitude - asc)) % 360.0

def _pol2cart(cx: float, cy: float, r: float, angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    x = cx + r * math.cos(rad)
    y = cy - r * math.sin(rad)  # SVG: y-Achse nach unten -> minus
    return x, y

def _sign_of(longitude: float) -> Tuple[str, int, float]:
    """Gibt (SignName, SignIndex 0..11, Grad-im-Zeichen) zurück."""
    idx = int(math.floor(longitude / 30.0)) % 12
    deg_in_sign = longitude % 30.0
    return ZODIAC[idx], idx, deg_in_sign

def _fmt_deg(d: float, places: int = 2) -> str:
    return f"{d:.{places}f}°"

def _build_svg(positions, houses, width=800, height=800, use_glyphs=True) -> str:
    cx, cy = width/2, height/2
    R_outer = min(width, height)*0.42    # äußere Kreislinie (Zodiac)
    R_inner = R_outer - 30               # innerer Kreis (Zodiac-Ring)
    R_house = R_inner - 25               # Häuserring
    R_plan  = (R_inner + R_house)/2      # Planeten-Plot-Radius
    asc = float(houses.ascendant)

    # SVG-Header
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        '<defs>',
        '<style><![CDATA['
        'text{font-family: system-ui, "Noto Sans", "Segoe UI", Arial, sans-serif; font-size:12px; dominant-baseline:middle; text-anchor:middle;}'
        '.small{font-size:10px} .label{font-size:14px;font-weight:600}'
        '.tick{stroke:#999;stroke-width:1} .ring{stroke:#000;stroke-width:2;fill:none}'
        '.house{stroke:#555;stroke-width:1.2} .planet{stroke:#111;fill:#111}'
        ']]></style>',
        '</defs>'
    ]

    # Ringe
    svg += [
        f'<circle class="ring" cx="{cx}" cy="{cy}" r="{R_outer}"/>',
        f'<circle class="ring" cx="{cx}" cy="{cy}" r="{R_inner}"/>',
        f'<circle class="ring" cx="{cx}" cy="{cy}" r="{R_house}"/>'
    ]

    # Zodiac-Segmente (jede 30°) relativ zur realen Ausrichtung (ASC)
    for k in range(12):
        # Segment-Mitte (Beschriftung)
        seg_mid_long = (k*30.0 + 15.0) % 360.0
        ang_mid = _angle_deg(seg_mid_long, asc)
        tx, ty = _pol2cart(cx, cy, (R_outer + R_inner)/2, ang_mid)
        label = ZGLYPH[k] if use_glyphs else ZODIAC[k][:3]
        svg.append(f'<text class="label" x="{tx:.1f}" y="{ty:.1f}">{label}</text>')

        # Segmentlinie (Grenze)
        seg_edge_long = (k*30.0) % 360.0
        ang_edge = _angle_deg(seg_edge_long, asc)
        x1, y1 = _pol2cart(cx, cy, R_outer, ang_edge)
        x2, y2 = _pol2cart(cx, cy, R_inner, ang_edge)
        svg.append(f'<line class="tick" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

    # Häuserlinien
    for i, cusp in enumerate(houses.cusps, start=1):
        ang = _angle_deg(float(cusp), asc)
        x1, y1 = _pol2cart(cx, cy, R_outer, ang)
        x2, y2 = _pol2cart(cx, cy, R_house, ang)
        svg.append(f'<line class="house" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

    # ASC / MC Markierungen
    for name, lon in [("ASC", asc), ("MC", float(houses.mc))]:
        ang = _angle_deg(lon, asc)
        x, y = _pol2cart(cx, cy, R_outer + 18, ang)
        svg.append(f'<text class="label" x="{x:.1f}" y="{y:.1f}">{name}</text>')

    # Planeten plotten
    for pp in positions:
        L = float(pp.longitude)
        ang = _angle_deg(L, asc)
        x, y = _pol2cart(cx, cy, R_plan, ang)
        g = PLAN_GLYPH.get(pp.planet) if use_glyphs else PLAN_ABBR.get(pp.planet, pp.planet[:2].title())
        svg.append(f'<circle class="planet" cx="{x:.1f}" cy="{y:.1f}" r="3"/>')
        # Label leicht nach außen
        lx, ly = _pol2cart(cx, cy, R_plan + 14, ang)
        svg.append(f'<text class="small" x="{lx:.1f}" y="{ly:.1f}">{g}</text>')

    svg.append('</svg>')
    return "\n".join(svg)

def _build_html(calc: CalcRequest, positions, houses, use_glyphs=True) -> str:
    # Tabelle der Planetenpositionen
    rows = []
    for pp in positions:
        sign_name, sign_idx, deg_in_sign = _sign_of(float(pp.longitude))
        retro = "R" if pp.retrograde else ""
        rows.append(f"<tr><td>{pp.planet.title()}</td><td>{sign_name}</td><td style='text-align:right'>{deg_in_sign:05.2f}°</td><td>{retro}</td></tr>")
    rows_html = "\n".join(rows)

    svg = _build_svg(positions, houses, width=800, height=800, use_glyphs=use_glyphs)
    dt_iso = calc.datetime.isoformat()
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<title>Radix</title>
<style>
  body{{font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, "Noto Sans", sans-serif; margin:20px; color:#111}}
  h1,h2{{margin:0 0 8px 0}}
  .grid{{display:grid; grid-template-columns: 820px 1fr; gap:24px}}
  table{{border-collapse: collapse; width:100%}}
  th,td{{border-bottom:1px solid #ddd; padding:6px 8px; font-size:14px}}
  th{{background:#f6f6f6; text-align:left}}
  .meta td{{border:none; padding:2px 0}}
  .small{{font-size:12px; color:#555}}
</style>
</head>
<body>
  <h1>Radix</h1>
  <table class="meta">
    <tr><td><b>Datum/Zeit:</b></td><td>{dt_iso}</td></tr>
    <tr><td><b>Ort:</b></td><td>lat {calc.location.lat}, lon {calc.location.lon}, alt {calc.location.alt_m} m</td></tr>
    <tr><td><b>Häusersystem:</b></td><td>{calc.house_system or settings.default_house_system}</td></tr>
  </table>
  <div class="grid">
    <div>{svg}</div>
    <div>
      <h2>Planetenpositionen</h2>
      <table>
        <thead><tr><th>Planet</th><th>Zeichen</th><th>Grad</th><th></th></tr></thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
      <p class="small">ASC: {_fmt_deg(float(houses.ascendant))} &nbsp; MC: {_fmt_deg(float(houses.mc))}</p>
    </div>
  </div>
</body>
</html>"""

@router.post("/svg")
def render_svg(req: CalcRequest, ephem: EphemerisProvider = Depends(get_provider), use_glyphs: bool = True):
    system = req.house_system or settings.default_house_system
    positions = ephem.planet_positions(req.datetime, req.location, req.planets)
    houses = ephem.houses(req.datetime, req.location, system)
    if not houses or not houses.cusps or len(houses.cusps) != 12:
        raise HTTPException(status_code=500, detail="Failed to compute houses")
    svg = _build_svg(positions, houses, width=800, height=800, use_glyphs=use_glyphs)
    return Response(content=svg, media_type="image/svg+xml")

@router.post("/html")
def render_html(req: CalcRequest, ephem: EphemerisProvider = Depends(get_provider), use_glyphs: bool = True):
    system = req.house_system or settings.default_house_system
    positions = ephem.planet_positions(req.datetime, req.location, req.planets)
    houses = ephem.houses(req.datetime, req.location, system)
    if not houses or not houses.cusps or len(houses.cusps) != 12:
        raise HTTPException(status_code=500, detail="Failed to compute houses")
    html = _build_html(req, positions, houses, use_glyphs=use_glyphs)
    return HTMLResponse(content=html)
