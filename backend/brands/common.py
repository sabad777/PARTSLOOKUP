import re
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# One shared connection pool = faster repeated lookups (no new TLS connection each time).
CLIENT = httpx.AsyncClient(
    headers=HEADERS,
    timeout=httpx.Timeout(9.0, connect=4.5),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    http2=True,
)

def clean(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()

def text(v: str) -> str:
    return re.sub(r"\s+", " ", v or "").strip()

async def get(url: str):
    r = await CLIENT.get(url)
    r.raise_for_status()
    return r
