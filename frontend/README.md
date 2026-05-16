# ChainPilot Frontend

Vite + React + TypeScript + Tailwind dashboard for the ChainPilot supply-chain simulation backend.

## Local/Brev Development

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://localhost:5173
```

On Brev, expose/open the secure link for port `5173`.

## Environment

Create `frontend/.env` from `.env.example`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

For hosted frontend deployments, set `VITE_API_BASE_URL` to the deployed backend URL.

## Build

```bash
npm run build
```

The static output is written to `frontend/dist/`.
