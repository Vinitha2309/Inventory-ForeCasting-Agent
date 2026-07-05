# StockWatch — Inventory Reorder Reasoning Agent

An AI agent that goes beyond predicting inventory demand: it reasons about
**how much to trust its own forecast**, and turns that reasoning into a
concrete reorder decision with plain-English justification — instead of
just plotting a line and leaving the interpretation to you.

## Why this is different from a standard forecasting tool

Most inventory forecasters output a single predicted number. StockWatch
instead:

1. **Quantifies its own uncertainty.** Every forecast carries a confidence
   band computed from real demand volatility, and low-confidence SKUs are
   flagged explicitly rather than presented with false precision.
2. **Reacts to external signals.** SKUs affected by real-world events
   (e.g. an incoming storm boosting poncho demand) get wider uncertainty
   and the agent names the signal in its explanation.
3. **Makes a judgment call, not just a chart.** The agent outputs an
   urgency level, a suggested reorder quantity, and a short reasoning
   paragraph — grounded strictly in pre-computed facts, never invented by
   the LLM.

## Architecture

```
┌─────────────┐      HTTP/JSON      ┌──────────────┐      Motor       ┌─────────┐
│   React +   │  ───────────────►   │   FastAPI     │  ─────────────► │ MongoDB │
│  TypeScript │  ◄───────────────   │   backend     │  ◄───────────── │         │
└─────────────┘                     └──────┬───────┘                  └─────────┘
                                            │
                                            │ structured facts only
                                            ▼
                                     ┌──────────────┐
                                     │   Groq LLM   │
                                     │ (reasoning)  │
                                     └──────────────┘
```

**Key design decision:** the numeric forecast (`forecasting.py`) is pure,
deterministic statistics — no LLM involved. The LLM (`reasoning.py`) only
ever receives a JSON object of already-computed facts and is constrained to
explain and justify them, never to compute or invent numbers. This keeps
the agent's decisions auditable and prevents hallucinated figures from
reaching the user.

## How each requirement is satisfied

| Requirement | Implementation |
|---|---|
| Unique topic | Confidence-aware inventory reorder reasoning agent |
| Programming language | Python (backend), TypeScript (frontend) |
| Prompt engineering | See `backend/app/reasoning.py` — role constraint, grounding via structured JSON input, few-shot examples, enforced JSON output schema, low temperature |
| LLM API | Groq (`llama-3.3-70b-versatile`) |
| Database | MongoDB (SKUs, sales history, cached reorder reports) |
| Web framework | FastAPI (backend) + React (frontend) |
| Frontend | React + TypeScript, Vite |
| Deployment | Docker + docker-compose (backend, frontend, MongoDB as three services) |

## Prompt engineering details

The system prompt in `reasoning.py` applies five principles:

1. **Role + scope constraint** — the model is explicitly told it may only
   narrate and judge given facts, never invent or recompute numbers.
2. **Grounding via structured input** — the model receives a single JSON
   object of pre-computed facts; there is no way for it to hallucinate a
   stock level or demand figure because it's never given room to.
3. **Few-shot examples** — two worked examples in the prompt show the
   desired tone, sentence count, and how the explanation should change when
   confidence is low or an external signal is present.
4. **Output-format enforcement** — the model must return
   `{"reasoning": "..."}` as strict JSON (via Groq's `response_format`), so
   the backend parses it reliably without regex.
5. **Low temperature (0.2)** — operational reasoning should be consistent
   run to run, not creative.

If the Groq API call fails for any reason (rate limit, network, missing
key), the backend falls back to a deterministic template
(`_fallback_reasoning`) so the demo never breaks mid-presentation.

## Running locally with Docker (recommended)

1. Copy the env template and add your Groq API key:
   ```bash
   cp .env.example .env
   # edit .env and set GROQ_API_KEY
   ```
   Get a free key at https://console.groq.com

2. Build and start everything:
   ```bash
   docker compose up --build
   ```

3. Open the app:
   - Frontend: http://localhost
   - Backend API docs: http://localhost:8000/docs

The backend automatically seeds MongoDB with a demo catalog of 7 SKUs and
60 days of synthetic sales history on first startup, so there's nothing
else to configure.

## Running locally without Docker

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY, and a local Mongo URI
# make sure MongoDB is running locally (e.g. `mongod` or a local Docker container)
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173 — Vite proxies `/api` calls to `localhost:8000`.

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/skus` | List all SKUs with cached urgency/reasoning, sorted by urgency |
| GET | `/api/skus/{sku_id}` | Full detail: SKU, sales history, forecast, reorder report |
| POST | `/api/skus/{sku_id}/refresh` | Force a fresh LLM call, bypassing the cache |

## Demo script (suggested)

1. Open the dashboard — point out the SKUs are already sorted by urgency.
2. Click the Rain Poncho SKU — it's flagged **critical** with **low
   confidence** because of an incoming storm signal. Read the agent's
   reasoning aloud.
3. Click **"Re-run reasoning"** to show the LLM call happening live (the
   badge shows "LLM" vs "FALLBACK" so you can prove it's a real API call,
   not a canned string).
4. Click a healthy SKU (e.g. the power bank) to contrast a calm, high-
   confidence explanation.
5. Mention the architecture: deterministic math computes the numbers, the
   LLM only explains and judges them — this is why the agent can be trusted
   in an operational setting.

## Deploying to the cloud (Render example)

1. Push this repo to GitHub.
2. **Database:** create a free MongoDB Atlas cluster, allow network access
   from anywhere, and copy the connection string.
3. **Backend:** on Render, create a new **Web Service** from this repo with
   root directory `backend` (Docker runtime, auto-detected from
   `backend/Dockerfile`). Set environment variables `MONGO_URI`,
   `MONGO_DB_NAME`, `GROQ_API_KEY`, `GROQ_MODEL`, `CORS_ORIGINS`.
4. **Frontend:** create a new **Static Site** from this repo with root
   directory `frontend`, build command `npm install && npm run build`,
   publish directory `dist`. Set environment variable `VITE_API_URL` to
   your backend's public URL plus `/api`
   (e.g. `https://stockwatch-backend.onrender.com/api`).
5. Once both are deployed, update the backend's `CORS_ORIGINS` env var to
   include your frontend's actual Render URL instead of `["*"]`.

The same pattern (build from `backend/Dockerfile`, static-build the
frontend with `VITE_API_URL` pointed at the backend) works equivalently on
Railway, AWS App Runner, or Azure Container Apps.

## Project structure

```
stockwatch/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── config.py        # env-based settings
│   │   ├── database.py      # MongoDB connection (motor)
│   │   ├── schemas.py       # Pydantic models
│   │   ├── forecasting.py   # deterministic forecasting engine
│   │   ├── reasoning.py     # Groq LLM prompt + call
│   │   └── seed.py          # synthetic demo data generator
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # main dashboard UI
│   │   ├── api.ts           # typed API client
│   │   └── main.tsx
│   ├── package.json
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```
