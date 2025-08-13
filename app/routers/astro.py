from fastapi import APIRouter, Depends
from app.deps import get_provider
from app.services.provider import EphemerisProvider
from app.models.schemas import CalcRequest, CalcResponse

router = APIRouter(prefix="/v1/astro", tags=["astro"])

@router.post("/positions", response_model=CalcResponse)
def positions(req: CalcRequest, ephem: EphemerisProvider = Depends(get_provider)):
    pos = ephem.planet_positions(req.datetime, req.location, req.planets)
    houses = ephem.houses(req.datetime, req.location, req.house_system) if req.house_system else None
    return CalcResponse(positions=pos, houses=houses)

@router.get("/health")
def health():
    return {"status": "ok"}
