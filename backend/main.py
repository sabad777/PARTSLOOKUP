import asyncio
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import init_db, get_cached, save_results
from brands import brembo, autodoc, trucktec

app = FastAPI(title="Office Parts Lookup", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

init_db()

SUPPORTED = {
    "supersession",
    "febi",
    "brembo",
    "lemforder",
    "vdo",
    "hengst",
    "trucktec",
}

class LookupRequest(BaseModel):
    brand: str = Field(..., examples=["brembo"])
    oems: list[str] = Field(..., min_length=1, max_length=500)
    force_refresh: bool = False


def normalize_oem(value: str):
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


async def live_lookup(brand: str, oem: str):
    # Brembo keeps its fast official-catalogue adapter.
    if brand == "brembo":
        results = await brembo.lookup(oem)
        # Fallback to AUTODOC if the Brembo page parser returns nothing.
        if not results:
            results = await autodoc.lookup_brand(oem, "brembo")
        return results

    # Trucktec has a simple official OE-number page, so use it first.
    if brand == "trucktec":
        results = await trucktec.lookup(oem)
        if not results:
            results = await autodoc.lookup_brand(oem, "trucktec")
        return results

    # Current lightweight fallbacks for these brands use AUTODOC's OEM page.
    if brand in {"febi", "lemforder", "vdo", "hengst"}:
        return await autodoc.lookup_brand(oem, brand)

    # This is intentionally called related OEM rather than guaranteed official supersession.
    if brand == "supersession":
        return await autodoc.related_oem(oem)

    return []


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
        results = await live_lookup(brand, oem)
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


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Office Parts Lookup",
        "version": "0.2.0",
        "brands": sorted(SUPPORTED),
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
            f"Brand '{brand}' is not enabled. Enabled: {', '.join(sorted(SUPPORTED))}"
        )

    clean = []
    seen = set()
    for value in req.oems:
        oem = normalize_oem(value)
        if oem and oem not in seen:
            seen.add(oem)
            clean.append(oem)

    # Modest concurrency protects the source sites while still making batches quick.
    semaphore = asyncio.Semaphore(4)

    async def guarded(oem):
        async with semaphore:
            return await lookup_one(brand, oem, req.force_refresh)

    rows = await asyncio.gather(*(guarded(oem) for oem in clean))
    return {"brand": brand, "count": len(rows), "rows": rows}
