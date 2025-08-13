from app.config import settings
from app.services.provider import EphemerisProvider
from app.services.swisseph_provider import SwissEphemeris

_provider: EphemerisProvider | None = None
def get_provider() -> EphemerisProvider:
    global _provider
    if _provider is None:
        if settings.astro_backend != "swisseph":
            raise RuntimeError("Only 'swisseph' wired in minimal build.")
        _provider = SwissEphemeris()
    return _provider
