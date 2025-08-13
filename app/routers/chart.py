from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.deps import get_provider
from app.services.provider import EphemerisProvider
from app.models.schemas import PersistRequest, CalcResponse
from app.services.persist import insert_person, upsert_position, house_of

router = APIRouter(prefix="/v1/chart", tags=["chart"])

@router.post("/persist")
def compute_and_persist(payload: PersistRequest, ephem: EphemerisProvider = Depends(get_provider)):
    # 1) Berechnen
    pos = ephem.planet_positions(payload.calc.datetime, payload.calc.location, payload.calc.planets)
    houses = ephem.houses(payload.calc.datetime, payload.calc.location, payload.calc.house_system)
    if not houses or len(houses.cusps) != 12:
        raise HTTPException(status_code=500, detail="Failed to compute houses (cusps missing)")

    # 2) Person ermitteln/erzeugen
    person_id: UUID
    if payload.person_id:
        person_id = payload.person_id
    else:
        p = payload.person
        person_id = insert_person(
            name_pseudonym=p.name_pseudonym,
            birth_date=p.birth_date,
            birth_time=p.birth_time,
            birth_place=p.birth_place,
            timezone=p.timezone,
            gender=p.gender,
        )

    # 3) Häuser zuordnen & persistieren
    for pp in pos:
        h = house_of(pp.longitude, houses.cusps)
        upsert_position(person_id, pp.planet, h, pp.retrograde, pp.longitude)

    # 4) Ergebnis zurückgeben (wie /positions, plus person_id)
    return {
        "person_id": str(person_id),
        "result": CalcResponse(positions=pos, houses=houses).model_dump()
    }
