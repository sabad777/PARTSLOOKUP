import re
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.autodoc.co.uk"
OEM_URL = BASE + "/car-parts/oem/{oem}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

# AUTODOC manufacturer wording can differ slightly from our dropdown labels.
BRAND_ALIASES = {
    "febi": {"FEBI BILSTEIN", "FEBI"},
    "lemforder": {"LEMFÖRDER", "LEMFORDER"},
    "vdo": {"VDO", "CONTINENTAL/VDO", "CONTINENTAL VDO"},
    "hengst": {"HENGST FILTER", "HENGST"},
    "trucktec": {"TRUCKTEC AUTOMOTIVE", "TRUCKTEC"},
    "brembo": {"BREMBO"},
}


def clean_oem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalise_brand(value: str) -> str:
    return _clean_line(value).upper().replace("Ö", "O")


def _title_candidate(lines: list[str], article_idx: int) -> str:
    """Pick a short product title immediately before an Article number line."""
    skip_prefixes = (
        "£", "€", "Reviews", "Submit a review", "Image:", "Details", "In stock",
        "Article number", "Item number", "Manufacturer", "EAN number", "Condition",
        "Reference number OEM", "Show OEM", "Buy", "Sold by", "Add to comparison",
    )
    for j in range(article_idx - 1, max(-1, article_idx - 10), -1):
        s = _clean_line(lines[j])
        if not s or s.startswith(skip_prefixes):
            continue
        if len(s) > 180:
            continue
        # Product titles usually include the product type + maker + OEM.
        return s
    return "Aftermarket product"


async def _fetch(oem: str) -> tuple[str, str]:
    oem = clean_oem(oem)
    url = OEM_URL.format(oem=quote(oem.lower()))
    timeout = httpx.Timeout(14.0, connect=7.0)
    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
    return r.text, url


async def lookup_brand(oem: str, brand: str) -> list[dict]:
    """
    Lightweight fallback lookup using AUTODOC's public OEM result page.
    Returns only part number + product title + source URL for the requested manufacturer.
    """
    html, url = await _fetch(oem)
    soup = BeautifulSoup(html, "html.parser")
    lines = [_clean_line(x) for x in soup.stripped_strings]
    wanted = {_normalise_brand(x) for x in BRAND_ALIASES.get(brand, {brand})}

    results = []
    seen = set()

    for i, line in enumerate(lines):
        if not line.lower().startswith("article number:"):
            continue

        part = _clean_line(line.split(":", 1)[1])
        if not part and i + 1 < len(lines):
            part = _clean_line(lines[i + 1])
        if not part:
            continue

        manufacturer = ""
        reference_oem = ""
        # Relevant product metadata normally follows the article number.
        for j in range(i + 1, min(len(lines), i + 45)):
            s = lines[j]
            if s.lower().startswith("manufacturer:"):
                manufacturer = _clean_line(s.split(":", 1)[1])
            elif s.lower().startswith("reference number oem:"):
                reference_oem = _clean_line(s.split(":", 1)[1])
            elif j > i + 2 and s.lower().startswith("article number:"):
                break

        if not manufacturer:
            continue

        norm_maker = _normalise_brand(manufacturer)
        if norm_maker not in wanted:
            continue

        # If AUTODOC exposes a reference OEM, make sure it corresponds to the query.
        if reference_oem and clean_oem(reference_oem) != clean_oem(oem):
            continue

        key = re.sub(r"\s+", "", part).upper()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "part_number": part,
            "product_name": _title_candidate(lines, i),
            "source_url": url,
        })

    return results[:20]


async def related_oem(oem: str) -> list[dict]:
    """
    Returns related OEM references shown by AUTODOC.
    IMPORTANT: these are cross-reference/related OE numbers and are NOT guaranteed
    to be an official manufacturer supersession chain. The UI labels them clearly.
    """
    html, url = await _fetch(oem)
    soup = BeautifulSoup(html, "html.parser")
    lines = [_clean_line(x) for x in soup.stripped_strings]
    query = clean_oem(oem)

    start = None
    for i, line in enumerate(lines):
        if line.lower() == "oem reference numbers":
            start = i + 1
            break

    if start is None:
        return []

    found = []
    seen = set()
    stop_phrases = ("find cheap deals", "auto parts for your car", "about autodoc")
    for line in lines[start:start + 100]:
        low = line.lower()
        if any(low.startswith(p) for p in stop_phrases):
            break
        # OEM references are normally compact alpha-numeric strings with optional spaces/dashes.
        compact = clean_oem(line)
        if compact == query or not (5 <= len(compact) <= 20):
            continue
        if not re.search(r"[A-Z]", compact) or not re.search(r"\d", compact):
            continue
        if compact in seen:
            continue
        seen.add(compact)
        found.append({
            "part_number": _clean_line(line).strip(" ,"),
            "product_name": "Related OEM reference — verify official supersession",
            "source_url": url,
        })

    return found[:25]
