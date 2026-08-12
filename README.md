# Office Parts Lookup — Brembo-first prototype

Architecture:

GitHub Pages (frontend) -> FastAPI backend -> Brembo public catalogue -> SQLite cache

## What works in this prototype

- Paste up to 500 OEM numbers.
- Select Brembo.
- Backend checks SQLite cache first.
- New numbers are looked up against Brembo's public catalogue search page.
- Only part number, basic product type, and source URL are returned.
- Results can be copied into Excel or downloaded as CSV.
- Repeated successful/not-found lookups are cached.

## Run locally on Windows

1. Install Python 3.11+.
2. Open Command Prompt in the `backend` folder.
3. Run:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn main:app --reload

4. Backend will run at:

    http://127.0.0.1:8000

5. Open `frontend/index.html` in a browser and press Search.

## Put the frontend on GitHub Pages

Upload the `frontend` files to a GitHub repository and enable GitHub Pages.

The frontend is static, so GitHub Pages can host it.

## Put the backend online

The backend cannot run on GitHub Pages. Deploy the `backend` folder to a Python-capable host such as a VPS or application hosting service.

After deployment, replace this value in the webpage:

    http://127.0.0.1:8000

with your backend HTTPS URL.

For production, also replace FastAPI's CORS `allow_origins=["*"]` with your exact GitHub Pages URL.

## Important practical note

Manufacturer catalogue HTML and automated-access policies can change. This prototype uses a lightweight parser and modest concurrency (4 simultaneous lookups). Before office production use, test the adapter against a set of known OEM/Brembo mappings and review the applicable website terms/robots rules.

## Next adapters

The same backend structure can add:

- Febi
- Blue Print
- Textar
- Lemförder

Each gets its own adapter under `backend/brands/`.
