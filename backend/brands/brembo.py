import re
from urllib.parse import quote, urljoin
import httpx
from bs4 import BeautifulSoup

BASE = "https://www.bremboparts.com"
SEARCH_URL = BASE + "/europe/en/catalogue/code?code={oem}"

PRODUCT_PATTERNS = {
    "pad": "Brake pad",
    "disc": "Brake disc",
    "drum": "Brake drum",
    "shoe": "Brake shoe",
    "kit": "Brake kit",
    "accessory": "Brake accessory",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/150 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

def _clean_part_from_href(href: str):
    # Expected examples:
    # /europe/en/catalogue/pad/P_85_111
    # /europe/en/catalogue/disc/09-7931-20
    m = re.search(
        r"/catalogue/(pad|disc|drum|shoe|kit|accessory)/([^/?#]+)",
        href,
        re.I,
    )
    if not m:
        return None
    ptype = m.group(1).lower()
    raw = m.group(2)
    # Brembo URLs commonly encode spaces/dots as underscores/hyphens.
    if ptype == "pad":
        part = raw.replace("_", " ")
    elif ptype == "disc":
        # Disc references normally display with dots.
        part = raw.replace("-", ".")
    else:
        part = raw.replace("_", " ")
    return ptype, part

async def lookup(oem: str) -> list[dict]:
    """
    Lightweight public-catalogue lookup.
    This intentionally fetches only the search-result HTML and extracts
    product links/names. It does not download images/specification PDFs.

    Website markup can change. If Brembo changes the catalogue, this adapter
    may need a small parser update.
    """
    oem = re.sub(r"[^A-Za-z0-9]", "", oem).upper()
    if not oem:
        return []

    url = SEARCH_URL.format(oem=quote(oem))

    timeout = httpx.Timeout(12.0, connect=6.0)
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=timeout,
        follow_redirects=True
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        parsed = _clean_part_from_href(href)
        if not parsed:
            continue
        ptype, part = parsed
        source_url = urljoin(BASE, href)
        key = (part, source_url)
        found[key] = {
            "part_number": part,
            "product_name": PRODUCT_PATTERNS.get(ptype, "Brembo product"),
            "source_url": source_url,
        }

    return list(found.values())
