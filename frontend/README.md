# ModelMesh AI — Frontend

Next.js (App Router, TypeScript, Tailwind CSS) console for the ModelMesh gateway. See the [root README](../README.md) for architecture and roadmap.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

`MODELMESH_API_URL` points at the backend (default `http://localhost:8000`). It is read on the server only: the browser calls this app's Route Handlers (e.g. `/api/chat`), which forward to the backend, so no CORS setup is needed and any port works.

## Run

```bash
npm run dev
```

Open http://localhost:3000. The home page shows the backend's `/v1/health` status.

## Checks

```bash
npm run lint
npm run build
```
