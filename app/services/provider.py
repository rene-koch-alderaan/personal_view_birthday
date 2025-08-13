from typing import Protocol, List
from datetime import datetime
from app.models.schemas import Planet, GeoLocation, PlanetPosition, Houses

class EphemerisProvider(Protocol):
    def planet_positions(self, when: datetime, loc: GeoLocation, planets: List[Planet]) -> List[PlanetPosition]: ...
    def houses(self, when: datetime, loc: GeoLocation, system: str) -> Houses: ...
