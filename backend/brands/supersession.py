import asyncio
from .common import clean
from . import lemforder, febi, hengst

async def lookup(oem: str) -> list[dict]:
    """
    Conservative mode: only official catalogues. We do not call Google/AUTODOC.
    ZF explicit 'Replaced by' relationships are returned as confirmed catalogue replacements.
    Other official-source results are labelled related/cross-reference candidates, not guaranteed OEM supersessions.
    """
    q = clean(oem)
    if not q:
        return []

    # Run sources in parallel to reduce waiting time.
    zf_task = lemforder.replacements(q)
    febi_task = febi.lookup(q)
    hengst_task = hengst.lookup(q)
    zf, fb, hg = await asyncio.gather(zf_task, febi_task, hengst_task, return_exceptions=True)

    out, seen = [], set()
    if isinstance(zf, list):
        for x in zf:
            k = clean(x.get("part_number", ""))
            if k and k != q and k not in seen:
                seen.add(k); out.append(x)

    # These are aftermarket cross references, useful when no explicit supersession exists.
    for source_name, rows in (("febi", fb), ("Hengst", hg)):
        if not isinstance(rows, list):
            continue
        for x in rows[:5]:
            k = clean(x.get("part_number", ""))
            if k and k != q and k not in seen:
                seen.add(k)
                out.append({
                    "part_number": x.get("part_number", ""),
                    "product_name": f"Related cross-reference from official {source_name} catalogue — not guaranteed OEM supersession",
                    "source_url": x.get("source_url", ""),
                })
    return out[:15]
