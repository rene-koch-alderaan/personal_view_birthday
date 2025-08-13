# app/services/swisseph_provider.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
import logging

from app.models.schemas import Planet, GeoLocation, PlanetPosition, Houses
from app.services.provider import EphemerisProvider
from app.config import settings

import swisseph as swe

log = logging.getLogger("uvicorn")

# Mapping unserer Planet-Strings auf Swiss Ephemeris Konstanten
_PLANET_MAP: dict[str, int] = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
    "chiron": swe.CHIRON,
    "north_node": swe.MEAN_NODE,   # alternativ: swe.TRUE_NODE
    "south_node": swe.MEAN_NODE,   # wird rechnerisch +180° gebildet
}

def _ensure_ephe_path() -> None:
    """Setzt den Ephemeriden-Pfad, wenn konfiguriert."""
    if settings.se_ephe_path:
        swe.set_ephe_path(settings.se_ephe_path)
        log.info(f"Swiss Ephemeris path set to: {settings.se_ephe_path}")

def _to_julday(dt: datetime) -> float:
    """Swiss Ephemeris erwartet UT."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ut = dt.astimezone(timezone.utc)
    hour_frac = (
        ut.hour
        + ut.minute / 60.0
        + ut.second / 3600.0
        + ut.microsecond / 3_600_000_000.0
    )
    return swe.julday(ut.year, ut.month, ut.day, hour_frac)

def _norm360(x: float) -> float:
    return float(x) % 360.0

class SwissEphemeris(EphemerisProvider):
    """Ephemeriden-Provider via pyswisseph (Swiss Ephemeris)."""

    def __init__(self) -> None:
        _ensure_ephe_path()

    def planet_positions(self, when: datetime, loc: GeoLocation, planets: List[Planet]) -> List[PlanetPosition]:
        jd_ut = _to_julday(when)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED  # Swiss Ephemeris + Geschwindigkeiten

        result: List[PlanetPosition] = []

        for p in planets:
            if p == "south_node":
                xx, _ = swe.calc_ut(jd_ut, _PLANET_MAP["north_node"], flags)
                lon = _norm360(xx[0] + 180.0)
                speed = float(xx[3])
                result.append(
                    PlanetPosition(
                        planet=p,
                        longitude=lon,
                        latitude=0.0,
                        speed_long=speed,
                        retrograde=bool(speed < 0.0),
                    )
                )
                continue

            xx, _retflag = swe.calc_ut(jd_ut, _PLANET_MAP[p], flags)
            lon = _norm360(xx[0])
            lat = float(xx[1])
            lon_speed = float(xx[3])

            result.append(
                PlanetPosition(
                    planet=p,
                    longitude=lon,
                    latitude=lat,
                    speed_long=lon_speed,
                    retrograde=bool(lon_speed < 0.0),
                )
            )

        return result

    def houses(self, when: datetime, loc: GeoLocation, system: str) -> Houses:
        """
        Berechnet Häuserkuspide + AC/MC.
        pyswisseph erwartet den House-Code als *Byte-String* (z. B. b'P').
        Rückgabeverhalten je nach Version:
          - cusps: 12 Elemente (Index 0..11) ODER 13 Elemente mit Dummy an Index 0 (1..12 gültig)
        """
        jd_ut = _to_julday(when)
        hs = (system or settings.default_house_system or "P")

        try:
            hsys = hs[0].upper().encode("ascii")  # genau 1 Byte
        except Exception:
            hsys = b"P"

        cusps, ascmc = swe.houses(jd_ut, float(loc.lat), float(loc.lon), hsys)

        # robust gegen unterschiedliche Längen/Indexierung
        n = len(cusps)
        if n >= 13:
            cusps_list = [_norm360(cusps[i]) for i in range(1, 13)]  # 1..12
        elif n == 12:
            cusps_list = [_norm360(c) for c in cusps]               # 0..11
        else:
            raise RuntimeError(f"Unexpected cusps length from swe.houses(): {n}")

        asc = _norm360(ascmc[0]) if len(ascmc) > 0 else 0.0
        mc  = _norm360(ascmc[1]) if len(ascmc) > 1 else 0.0

        return Houses(cusps=cusps_list, ascendant=asc, mc=mc)
