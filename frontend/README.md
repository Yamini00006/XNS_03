# Customer Data Platform — Frontend (Member 1)

React + Vite + Tailwind CSS frontend for the Customer Data Platform. Consumes
the existing Django REST API built by Member 2 (`backend/`). This app does
not reimplement any backend logic — it is a thin client over the real API.

## Ownership

Owned by **Member 1 — Frontend Developer**, branch `feature/frontend`.
Only files under `frontend/` are part of this scope. Backend, data
processing, database, and infrastructure are owned by other members and
were not modified.

## Requirements

- Node.js 18+ and npm

## Setup

```bash
cd frontend
npm install
cp .env.example .env      # then edit VITE_API_BASE_URL if the backend
                           # isn't running at http://localhost:8000
npm run dev
```

The app runs at `http://localhost:5173` by default and expects the Django
backend (see `../backend/`) to be running and reachable at
`VITE_API_BASE_URL`.

### Build

```bash
npm run build     # outputs to frontend/dist/
npm run preview   # serve the production build locally
```

## Configuration

All backend communication is configured through a single environment
variable, read at build/dev time by Vite:

| Variable            | Default                 | Purpose                     |
|---------------------|--------------------------|------------------------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the Django API   |

No API URLs are hardcoded elsewhere in the source — every request goes
through `src/services/api.js`.

## Project structure

```
frontend/
├── public/
├── src/
│   ├── components/     # Reusable UI pieces (Navbar, DataTable, FileUpload, ...)
│   ├── pages/           # Route-level views (Login, Dashboard, Upload, ...)
│   ├── services/        # One file per backend app; all HTTP calls live here
│   ├── hooks/            # useAuth, useFetch, usePolling
│   ├── context/          # AuthContext (JWT session state)
│   ├── utils/            # constants, formatters, localStorage helpers
│   ├── App.jsx           # Route table
│   └── main.jsx          # Entry point
├── package.json
├── vite.config.js
├── tailwind.config.js
└── .env.example
```

## How this maps to the actual backend API

Inspected directly from `backend/apps/*/views.py` and `backend/config/urls.py`
before implementing each service — nothing here was invented.

| Frontend service          | Backend endpoint(s)                                              |
|----------------------------|-------------------------------------------------------------------|
| `authService`             | `POST /api/auth/login/`, `/refresh/`, `/logout/`, `GET /api/users/me/` |
| `fileService`              | `POST /api/files/upload/`, `GET /api/files/`, `GET/DELETE /api/files/{id}/` |
| `processingService`        | `POST /api/processing/{file_id}/start/`, `GET /api/processing/`, `/{id}/`, `/{id}/errors/` |
| `dataService`               | `GET /api/data/` (search/sort/filter/paginate), `/{id}/`, `/{id}/raw/` |
| `dashboardService`          | `GET /api/dashboard/metrics/` |
| `exportService`             | `GET /api/exports/csv/`, `/xlsx/`, `/json/` (optional `?ids=`) |
| `chatbotService`            | `POST /api/chatbot/query/` |

Response shapes consumed by the UI (e.g. dashboard metrics fields, the
`{count, page, page_size, total_pages, results}` pagination envelope, the
`{error: {code, message}}` error envelope) match the actual backend code
as of the version in this repository. If the backend contract changes,
update the corresponding file in `src/services/` — components never talk
to `axios`/`fetch` directly.

## Auth flow

- JWT access + refresh tokens are stored in `localStorage` (`src/utils/storage.js`).
- Every request automatically attaches `Authorization: Bearer <access>` via
  an axios interceptor (`src/services/api.js`).
- On a `401`, the client automatically attempts a silent refresh once; if
  that also fails, tokens are cleared and the user is redirected to
  `/login`.
- All routes except `/login` are wrapped in `ProtectedRoute` and redirect
  unauthenticated users to `/login`, preserving the page they were trying
  to reach.

## Validation & UX conventions used throughout

- Every form validates on the client before calling the API (required
  fields, non-whitespace search text, file type/size sanity checks) and
  shows the error next to the relevant field.
- Submit buttons disable themselves while a request is in flight to
  prevent duplicate submissions (upload, processing start, export,
  chatbot send, filter apply).
- Pagination and sort options are driven by what the backend actually
  supports — no invented page sizes or sort fields.
- Processing status polling (`usePolling`) automatically stops once a job
  reaches `Completed` or `Failed`, so the UI never polls unnecessarily.
- `BackButton` uses React Router's history (`navigate(-1)`) with a
  sensible fallback route, used on standalone detail pages (Customer
  Details, Processing Job Detail) where there's no other way back.

## Known limitations (hackathon scope)

- The chatbot is intentionally simple (calls the backend's rule-based
  `/api/chatbot/query/`); there's no streaming or conversation memory.
- No dedicated frontend automated test suite was added — verification was
  manual (dev server, build, and a walk-through of every page/flow) per
  the project's hackathon-appropriate scope. `npm run build` should be
  run locally to confirm the production build succeeds, since no
  Node/npm runtime was available in the environment this was authored in.
