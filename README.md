# Clinic Booking

A small clinic booking system: a FastAPI + SQLite API and a React dashboard.

```
backend/    FastAPI + SQLite API, deployed to Pxxl with its Dockerfile
frontend/   React + Vite dashboard, deployed to Vercel
```

The two are deployed separately. The frontend calls the API at the URL in `VITE_API_URL`.

## Run it locally

Backend (needs [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
cp .env.example .env          # set API_KEY
uv run uvicorn app.main:app --reload
```

The API is on http://localhost:8000 and its docs on http://localhost:8000/docs.
An empty database is filled with random doctors, slots and bookings on first start.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. In development it talks to `http://localhost:8000`
without any setup. The dashboard password is the backend's `API_KEY`.

## Deploy the backend to Pxxl

1. Create a project from this repo and set **Base directory** to `backend`.
   Pxxl builds `backend/Dockerfile` and reads `backend/pxxl.toml`.
2. In **Secrets** add:
   - `API_KEY`: required, also the dashboard password
   - `CORS_ORIGINS`: your Vercel URL, e.g. `https://clinic-booking.vercel.app`
   - `DATABASE_PATH`: `/data/clinic.db`
3. In **Compute & Scaling** add a volume mounted at `/data`. SQLite lives
   there; without it every deploy wipes the data.

Your API docs are then at `https://<your-app>.pxxl.pro/docs`.

## Deploy the frontend to Vercel

1. Import the repo and set **Root Directory** to `frontend`. `vercel.json` handles
   the rest (build command, output folder, single-page routing).
2. Add the environment variable `VITE_API_URL` = your Pxxl URL, with no trailing
   slash. Vite reads it at build time, so redeploy after changing it.

## Using the dashboard

- **Pick a slot**: filter by doctor with the select, choose a day, choose a time.
- **Book**: enter a name and email, then confirm.
- **Find bookings**: search by patient email or by booking ID.
- **View details**: click any booking in the list to see its ID, doctor, date and
  time, patient, email and when it was booked. You can cancel from there too.
- **Sample data**: "Replace with new sample data" regenerates everything.
  This wipes all bookings.

## API

Every endpoint needs an `X-API-Key` header. Errors always look like `{"error": "<message>"}`.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/slots` | List slots with availability |
| POST | `/bookings` | Book a slot. Send `Idempotency-Key` to make retries safe |
| GET | `/bookings?email=&cursor=&limit=` | A patient's bookings, cursor paginated |
| GET | `/bookings/{id}` | One booking |
| DELETE | `/bookings/{id}` | Cancel a booking and free the slot |
| POST | `/reset` | Replace slots (for tests) |
| POST | `/seed` | Replace everything with random demo data |

A slot can only have one confirmed booking, even under concurrent requests
(enforced by a partial unique index). More than 5 booking attempts per email in a
minute returns `429` with a `Retry-After` header.

## Checks

```bash
cd backend  && uv run ruff format --check . && uv run ruff check . && uv run pytest
cd frontend && npx tsc --noEmit && npm run build
```
