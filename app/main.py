from fastapi import FastAPI
from app.routers import astro
from app.routers import radix  # NEU
from app.routers import radix_kerykeion

app = FastAPI(title="Astro API", version="0.3.0")
app.include_router(astro.router)
app.include_router(radix.router)
app.include_router(radix_kerykeion.router)

@app.get("/")
def root():
    return {"name": "Astro API", "version": "0.3.0"}
