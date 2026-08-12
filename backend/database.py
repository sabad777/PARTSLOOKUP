import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).with_name("parts_cache.sqlite3")

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS lookup_cache (
            brand TEXT NOT NULL,
            oem TEXT NOT NULL,
            part_number TEXT,
            product_name TEXT,
            source_url TEXT,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (brand, oem, part_number)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_lookup_brand_oem
        ON lookup_cache (brand, oem)
        """)

def get_cached(brand: str, oem: str):
    with _conn() as conn:
        rows = conn.execute("""
            SELECT brand, oem, part_number, product_name, source_url, status, updated_at
            FROM lookup_cache
            WHERE brand = ? AND oem = ?
            ORDER BY part_number
        """, (brand.lower(), oem.upper())).fetchall()
    return [dict(r) for r in rows]

def save_results(brand: str, oem: str, items: list[dict]):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "DELETE FROM lookup_cache WHERE brand = ? AND oem = ?",
            (brand.lower(), oem.upper())
        )
        if not items:
            conn.execute("""
                INSERT INTO lookup_cache
                (brand,oem,part_number,product_name,source_url,status,updated_at)
                VALUES (?,?,?,?,?,?,?)
            """, (brand.lower(), oem.upper(), "", "", "", "not_found", now))
        else:
            for item in items:
                conn.execute("""
                    INSERT OR REPLACE INTO lookup_cache
                    (brand,oem,part_number,product_name,source_url,status,updated_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    brand.lower(),
                    oem.upper(),
                    item.get("part_number", ""),
                    item.get("product_name", ""),
                    item.get("source_url", ""),
                    "found",
                    now
                ))
