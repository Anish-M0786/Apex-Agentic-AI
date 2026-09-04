# Apex Workspace

Next.js frontend for the local Apex API.

Copy `.env.local.example` to `.env.local`, then run `npm install` and `npm run dev`.

Commands: `npm run dev`, `npm run build`, `npm run lint`, and `npm test`.

The app expects FastAPI at `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`). Set backend `FRONTEND_ORIGIN=http://localhost:3000` for local CORS. It uses safe SSE activity labels only and never renders model-generated HTML.
