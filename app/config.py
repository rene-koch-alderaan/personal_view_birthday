from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

HouseSystem = Literal["P","K","W","R","C","B","M","O","X"]  # Placidus, Koch, Whole Sign, ...

class Settings(BaseSettings):
    # <<< WICHTIG: Extra-ENV-Variablen ignorieren, .env laden >>>
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # Konfiguration für dein Astro-Backend
    astro_backend: Literal["swisseph","skyfield"] = "swisseph"
    se_ephe_path: str | None = None            # z.B. /opt/ephe (im Container)
    default_house_system: HouseSystem = "P"
    tz_default: str = "Europe/Berlin"

    @field_validator("se_ephe_path")
    @classmethod
    def strip_empty(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None

settings = Settings()
