import re
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.trucktec.de"
OEM_URL = BASE + "/oe-nummern/{oem}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9,de;q=0.8",
}


def clean_oem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


async def lookup(oem: str) -> list[dict]:
    oem = clean_oem(oem)
    if not oem:
        return []
    url = OEM_URL.format(oem=quote(oem.lower()))
    timeout = httpx.Timeout(12.0, connect=6.0)
    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    lines = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
    results = []
    seen = set()

    for i, line in enumerate(lines):
        m = re.match(r"TRUCKTEC\s+no\s*:\s*(.+)$", line, re.I)
        if not m:
            continue
        part = m.group(1).strip()
        key = re.sub(r"\s+", "", part).upper()
        if key in seen:
            continue
        seen.add(key)

        product = "TRUCKTEC product"
        for j in range(i - 1, max(-1, i - 8), -1):
            candidate = lines[j]
            if not candidate or candidate.lower().startswith(("produkte gefunden", "produkte für", "login", "sign up")):
                continue
            if len(candidate) <= 140:
                product = candidate
                break

        results.append({
            "part_number": part,
            "product_name": product,
            "source_url": url,
        })

    return results[:20]
