import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .common import get, clean, text

# Continental/VDO's official catalogue is hosted by TecAlliance.
BASE = "https://web.tecalliance.net"
HOME = BASE + "/continental/en/home"

async def lookup(oem: str) -> list[dict]:
    oem = clean(oem)
    if not oem:
        return []

    # TecAlliance catalogue URLs can change. Try lightweight public search routes only;
    # no login/API credentials are required by this code.
    urls = [
        BASE + "/continental/en/parts?query=" + quote(oem),
        BASE + "/continental/en/search?query=" + quote(oem),
        BASE + "/continental/en/parts/search?query=" + quote(oem),
    ]
    out, seen = [], set()
    for url in urls:
        try:
            r = await get(url)
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            # Known public detail pattern: /continental/en/parts/<id>/<part>/detail
            m = re.search(r"/continental/en/parts/\d+/([^/?#]+)/detail", href, re.I)
            if not m:
                continue
            part = text(m.group(1)).replace("%20", " ")
            key = clean(part)
            if not key or key in seen:
                continue
            seen.add(key)
            label = text(a.get_text(" ", strip=True)) or "VDO / Continental product"
            out.append({"part_number": part, "product_name": label, "source_url": urljoin(BASE, href)})
        if out:
            break
    return out[:20]
