# app/models/schemas.py
from __future__ import annotations
from typing import Literal, List, Optional
from datetime import datetime, date, time
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

Planet = Literal[
    "sun","moon","mercury","venus","mars","jupiter","saturn",
    "uranus","neptune","pluto","chiron","north_node","south_node"
]

class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    alt_m: float = 0.0

class CalcRequest(BaseModel):
    datetime: datetime
    location: GeoLocation
    house_system: Optional[str] = None
    planets: List[Planet] = [
        "sun","moon","mercury","venus","mars","jupiter","saturn"
    ]

class PlanetPosition(BaseModel):
    planet: Planet
    longitude: float = Field(..., ge=0.0, lt=360.0)
    latitude: Optional[float] = None
    speed_long: Optional[float] = None
    retrograde: bool

class Houses(BaseModel):
    cusps: List[float]  # 12 Werte 0..360
    ascendant: float
    mc: float

class CalcResponse(BaseModel):
    positions: List[PlanetPosition]
    houses: Optional[Houses] = None

# -------- Persist-Models --------

class PersonIn(BaseModel):
    name_pseudonym: Optional[str] = None
    birth_date: date
    birth_time: time
    birth_place: str
    timezone: str
    gender: Optional[str] = None

class PersistRequest(BaseModel):
    calc: CalcRequest
    person_id: Optional[UUID] = None    # Variante A: schon vorhanden
    person: Optional[PersonIn] = None   # Variante B: neu anlegen

    @model_validator(mode="after")
    def _check_person_or_id(self) -> "PersistRequest":
        """Genau eine der beiden Angaben muss gesetzt sein."""
        has_id = self.person_id is not None
        has_person = self.person is not None
        if has_id == has_person:
            # Beide gesetzt ODER beide leer → Fehler
            raise ValueError("Provide exactly one of: person_id OR person.")
        return self
