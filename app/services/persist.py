from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from datetime import date, time
from psycopg.rows import dict_row
from app.db import pool

def house_of(longitude: float, cusps: List[float]) -> int:
    """Hausnummer anhand 12 Kuspiden (0..360), robust bzgl. Wrap."""
    if not cusps or len(cusps) != 12:
        raise ValueError("cusps must be a list of 12 floats")
    base = cusps[0] % 360.0
    p = (longitude - base) % 360.0
    for i in range(11):
        start = (cusps[i]   - base) % 360.0
        end   = (cusps[i+1] - base) % 360.0
        if end <= start:
            end += 360.0
        if start <= p < end:
            return i + 1
    return 12

def insert_person(
    name_pseudonym: Optional[str],
    birth_date: date,
    birth_time: time,
    birth_place: str,
    timezone: str,
    gender: Optional[str],
) -> UUID:
    sql = """
    INSERT INTO public.person (name_pseudonym, birth_date, birth_time, birth_place, timezone, gender)
    VALUES (%(name)s, %(bdate)s, %(btime)s, %(place)s, %(tz)s, %(gender)s)
    RETURNING id;
    """
    params = dict(name=name_pseudonym, bdate=birth_date, btime=birth_time, place=birth_place, tz=timezone, gender=gender)
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row["id"]

def upsert_position(person_id: UUID, planet: str, house: int, retrograde: bool, longitude: float) -> None:
    sql = """
    INSERT INTO public.planet_position (person_id, planet, house, retrograde, longitude)
    VALUES (%(pid)s, %(planet)s::planet_enum, %(house)s, %(retro)s, %(lon)s)
    ON CONFLICT (person_id, planet) DO UPDATE
      SET house = EXCLUDED.house,
          retrograde = EXCLUDED.retrograde,
          longitude = EXCLUDED.longitude;
    """
    params = dict(pid=person_id, planet=planet, house=house, retro=retrograde, lon=longitude)
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
