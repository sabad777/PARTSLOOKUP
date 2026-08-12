import asyncio
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import init_db, get_cached, save_results
from brands import brembo

app = FastAPI(title="Office Parts Lookup", version="0.1.0")

# For first deployment this is permissive.
# Later replace "*" with your exact GitHub Pages URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

init_db()

SUPPORTED = {"brembo"}

class LookupRequest(BaseModel):
    brand: str = Field(..., examples=["brembo"])
    oems: list[str] = Field(..., min_length=1, max_length=500)
    force_refresh: bool = False

def normalize_oem(value: str):
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()

async def lookup_one(brand: str, oem: str, force_refresh: bool):
    oem = normalize_oem(oem)
    if not oem:
        return {"oem": "", "status": "invalid", "results": [], "cached": False}

    if not force_refresh:
        cached = get_cached(brand, oem)
        if cached:
            if len(cached) == 1 and cached[0]["status"] == "not_found":
                return {"oem": oem, "status": "not_found", "results": [], "cached": True}
            results = [
                {
                    "part_number": r["part_number"],
                    "product_name": r["product_name"],
                    "source_url": r["source_url"],
                }
                for r in cached if r["status"] == "found"
            ]
            return {"oem": oem, "status": "found", "results": results, "cached": True}

    try:
        if brand == "brembo":
            results = await brembo.lookup(oem)
        else:
            results = []
    except Exception as exc:
        return {
            "oem": oem,
            "status": "error",
            "results": [],
            "cached": False,
            "error": str(exc),
        }

    save_results(brand, oem, results)
    return {
        "oem": oem,
        "status": "found" if results else "not_found",
        "results": results,
        "cached": False,
    }

@app.get("/health")
def health():
    return {"ok": True, "brands": sorted(SUPPORTED)}

@app.post("/lookup")
async def lookup(req: LookupRequest):
    brand = req.brand.strip().lower()
    if brand not in SUPPORTED:
        raise HTTPException(
            400,
            f"Brand '{brand}' is not enabled yet. Enabled: {', '.join(sorted(SUPPORTED))}"
        )

    # Deduplicate while preserving order.
    clean = []
    seen = set()
    for value in req.oems:
        oem = normalize_oem(value)
        if oem and oem not in seen:
            seen.add(oem)
            clean.append(oem)

    # Keep concurrency modest so the catalogue is not hammered.
    semaphore = asyncio.Semaphore(4)

    async def guarded(oem):
        async with semaphore:
            return await lookup_one(brand, oem, req.force_refresh)

    rows = await asyncio.gather(*(guarded(oem) for oem in clean))
    return {"brand": brand, "count": len(rows), "rows": rows}
