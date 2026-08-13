import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .common import get, clean, text

BASE = "https://aftermarket.zf.com"
SEARCH = BASE + "/en/catalog/search/?country=GB&sort=relevance&term={q}"

async def lookup(oem: str) -> list[dict]:
    oem = clean(oem)
    if not oem:
        return []
    url = SEARCH.format(q=quote(oem))
    r = await get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()

    # ZF result cards link to /catalog/products/<article>/ and include the brand in visible text.
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        m = re.search(r"/catalog/products/([^/?#]+)/?", href, re.I)
        if not m:
            continue
        article = text(m.group(1))
        container = a.find_parent(["li", "article", "div"]) or a.parent
        block = text(container.get_text(" ", strip=True) if container else a.get_text(" ", strip=True))
        if "LEMF" not in block.upper():
            continue
        key = clean(article)
        if not key or key in seen:
            continue
        seen.add(key)
        # remove brand/article from label where possible
        label = text(a.get_text(" ", strip=True))
        product = re.sub(r"(?i)lemf[oö]rder", "", label)
        product = product.replace(article, "").strip(" -|") or "LEMFÖRDER product"
        out.append({"part_number": article, "product_name": product, "source_url": urljoin(BASE, href)})
    return out[:20]

async def replacements(term: str) -> list[dict]:
    """ZF explicitly labels some catalogue articles as 'Replaced by'. This returns only those explicit relations."""
    q = clean(term)
    if not q:
        return []
    url = SEARCH.format(q=quote(q))
    r = await get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    txt = text(soup.get_text(" ", strip=True))
    out, seen = [], set()
    for m in re.finditer(r"(?i)Replaced\s+by\s+([A-Z0-9][A-Z0-9 ._/-]{3,30})", txt):
        raw = text(m.group(1)).split(" Find ")[0].strip(" .,-")
        c = clean(raw)
        if c and c != q and c not in seen:
            seen.add(c)
            out.append({"part_number": raw, "product_name": "Explicitly shown as Replaced by in ZF catalogue", "source_url": url})
    return out[:10]
