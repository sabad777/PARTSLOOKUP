import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .common import get, clean, text

BASE = "https://partsfinder.bilsteingroup.com"
# Official Partsfinder uses q= for its article/text search.
SEARCH = BASE + "/en/search?t=a&q={q}&sortby=rel&sortdir=asc"

async def lookup(oem: str) -> list[dict]:
    oem = clean(oem)
    if not oem:
        return []
    url = SEARCH.format(q=quote(oem))
    r = await get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        m = re.search(r"/article/febi/([^/?#]+)", href, re.I)
        if not m:
            continue
        part = text(m.group(1)).replace("%20", " ")
        part = re.sub(r"\s+", " ", part)
        key = re.sub(r"\W", "", part).upper()
        if not key or key in seen:
            continue
        seen.add(key)
        label = text(a.get_text(" ", strip=True))
        # Prefer a meaningful title from the result link; otherwise keep it simple.
        product = label if label and key not in re.sub(r"\W", "", label).upper() else "febi product"
        out.append({"part_number": part, "product_name": product, "source_url": urljoin(BASE, href)})
    return out[:20]
