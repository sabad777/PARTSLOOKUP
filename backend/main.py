import asyncio
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import init_db, get_cached, save_results
from brands import brembo, febi, lemforder, vdo, hengst, trucktec, supersession

app = FastAPI(title="Office Parts Lookup", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["*"])
init_db()

SUPPORTED = {"supersession","febi","brembo","lemforder","vdo","hengst","trucktec"}

class LookupRequest(BaseModel):
    brand: str
    oems: list[str] = Field(..., min_length=1, max_length=500)
    force_refresh: bool = False

def normalize_oem(v: str):
    return re.sub(r"[^A-Za-z0-9]", "", v or "").upper()

async def live_lookup(brand, oem):
    adapters = {
        "brembo": brembo.lookup,
        "febi": febi.lookup,
        "lemforder": lemforder.lookup,
        "vdo": vdo.lookup,
        "hengst": hengst.lookup,
        "trucktec": trucktec.lookup,
        "supersession": supersession.lookup,
    }
    return await adapters[brand](oem)

async def lookup_one(brand, oem, force_refresh=False):
    oem = normalize_oem(oem)
    if not oem:
        return {"oem":"","status":"invalid","results":[],"cached":False}
    if not force_refresh:
        cached = get_cached(brand, oem)
        if cached:
            if len(cached)==1 and cached[0]["status"]=="not_found":
                return {"oem":oem,"status":"not_found","results":[],"cached":True}
            res=[{"part_number":r["part_number"],"product_name":r["product_name"],"source_url":r["source_url"]} for r in cached if r["status"]=="found"]
            return {"oem":oem,"status":"found","results":res,"cached":True}
    try:
        res = await live_lookup(brand, oem)
    except Exception as exc:
        return {"oem":oem,"status":"error","results":[],"cached":False,"error":str(exc)}
    save_results(brand, oem, res)
    return {"oem":oem,"status":"found" if res else "not_found","results":res,"cached":False}

@app.get("/")
def root(): return {"ok":True,"service":"Office Parts Lookup","version":"0.3.0","brands":sorted(SUPPORTED)}
@app.get("/health")
def health(): return {"ok":True,"version":"0.3.0","brands":sorted(SUPPORTED)}

@app.post("/lookup")
async def lookup(req: LookupRequest):
    brand=req.brand.strip().lower()
    if brand not in SUPPORTED:
        raise HTTPException(400, f"Brand '{brand}' is not enabled")
    clean=[]; seen=set()
    for v in req.oems:
        o=normalize_oem(v)
        if o and o not in seen: seen.add(o); clean.append(o)

    # 8 concurrent lookups is a good speed/traffic balance for a small office.
    sem=asyncio.Semaphore(8)
    async def guarded(o):
        async with sem: return await lookup_one(brand,o,req.force_refresh)
    rows=await asyncio.gather(*(guarded(o) for o in clean))
    return {"brand":brand,"count":len(rows),"rows":rows}
