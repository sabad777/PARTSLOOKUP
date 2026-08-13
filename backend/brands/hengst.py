import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .common import get, clean, text

BASE = "https://catalog.hengst.com"
SEARCH = BASE + "/en/online-catalog/search/?catalog=ae"

async def lookup(oem: str) -> list[dict]:
    """
    Hengst's official catalogue has a cross-reference search. Its form is TYPO3-driven,
    so this adapter tries the public GET form variants used by the catalogue and parses
    resulting product links. No AUTODOC is used.
    """
    oem = clean(oem)
    if not oem:
        return []
    candidates = [
        SEARCH + "&q=" + quote(oem),
        SEARCH + "&search=" + quote(oem),
        SEARCH + "&crossReference=" + quote(oem),
        SEARCH + "&tx_uihengst_uihengst%5Bsearch%5D=" + quote(oem),
    ]
    out, seen = [], set()
    last_url = candidates[0]
    for url in candidates:
        last_url = url
        try:
            r = await get(url)
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/online-catalog/product/" not in href:
                continue
            label = text(a.get_text(" ", strip=True))
            # Hengst product names/codes usually include at least one letter and digit.
            m = re.search(r"\b([A-Z]{1,5}[A-Z0-9-]*(?:\s+D\d+)?)\b", label.upper())
            if not m:
                continue
            part = text(m.group(1))
            key = clean(part)
            if len(key) < 3 or key in seen:
                continue
            seen.add(key)
            out.append({"part_number": part, "product_name": "Hengst filter", "source_url": urljoin(BASE, href)})
        if out:
            break
    return out[:20]
