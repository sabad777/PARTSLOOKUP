# Office Parts Lookup V3

V3 removes AUTODOC and uses official/public catalogue sources where possible:

- Brembo -> Brembo Parts
- Febi -> bilstein group Partsfinder
- Lemförder -> ZF Aftermarket Catalog
- VDO -> Continental/VDO TecAlliance-hosted catalogue (best-effort public routes)
- Hengst -> Hengst Online Catalogue (best-effort public cross-reference form routes)
- Trucktec -> Trucktec official OE pages
- Supersession / Related OEM -> official-source-only conservative mode

## Speed improvements

- Browser localStorage cache: repeated searches on the same office browser are instant.
- SQLite server cache remains enabled.
- Shared HTTP connection pool reduces repeated TLS connection time.
- Up to 8 different OEM numbers are looked up concurrently.
- Shorter network timeouts prevent one blocked catalogue from holding the whole batch for too long.

## Render

Keep Root Directory: `backend`
Build command: `pip install -r requirements.txt`
Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
Python version environment variable can remain `PYTHON_VERSION=3.13.5`.

## Important

Manufacturer sites can change markup or block cloud-hosted requests. Brembo is already proven in the current deployment. Febi and ZF official public search URL structures were confirmed while V3 was prepared. Hengst and VDO may need a small parser/request adjustment after the first Render test because their catalogues are more dynamic.
