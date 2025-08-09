# Agentic Forecast MVP (Streamlit + FastAPI)

Minimal two-service scaffold for a 6-agent financial forecasting MVP.  
- **frontend/**: Streamlit UI to start a run and watch progress/results.
- **backend/**: FastAPI with `/runs` (start), `/runs/{id}` (status), `/runs/{id}/events` (n8n callbacks).  
- **n8n/**: example workflow JSON and notes.

## 1) Setup

```bash
git clone <this-zip-unpacked>
cd agentic-forecast-mvp

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env  # edit if needed

# Run FastAPI
uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```bash
# Frontend
python -m venv .venv_frontend && source .venv_frontend/bin/activate
pip install -r frontend/requirements.txt

# Run Streamlit
streamlit run frontend/streamlit_app.py --server.port 8501
```

Visit: http://localhost:8501

## 2) How it works

- Streamlit calls `POST /runs` with symbols & horizon.
- FastAPI either:
  - **Simulates** a 6-step pipeline locally (default), or
  - **Delegates** to n8n if you set `N8N_WEBHOOK_URL` in `.env`.
- n8n (or the simulator) sends progress/results to `POST /runs/{id}/events`.
- Streamlit polls `GET /runs/{id}` to display status.

## 3) Use with n8n (optional)

1. Import `n8n/workflow.example.json` into n8n (as a starting point).
2. Add your nodes (agents). After each stage, send a callback:
   - URL: `{{ $json.callback_url }}`
   - Body (JSON):
     - `{"type":"progress","value":0.45}`
     - `{"type":"log","message":"features done"}`
     - `{"type":"partial_result","agent":"forecast","data":{...}}`
     - or final `{"type":"completed","result":{...}}`
3. If you set `N8N_SHARED_SECRET` in FastAPI, compute HMAC in n8n and send header `X-Signature: sha256=<digest>`.

## 4) Environment

- `BASE_URL` should be where FastAPI is reachable by n8n (default: `http://localhost:8000`).
- `N8N_WEBHOOK_URL` (optional) points to your n8n Webhook trigger.
- `N8N_SHARED_SECRET` (optional) enables signature validation on callbacks.

## 5) Next steps

- Swap the simulator with real agent logic (HTTP calls to model services).
- Persist runs/logs in PostgreSQL.
- Add SSE/WebSockets for live updates instead of polling.
- Add authentication + rate limits.
- Containerize with Docker Compose when ready.

## Task Router (QA vs Strategy)
The UI has a **Task** selector: `Auto | Document Q&A | Forecast+Strategy`. The backend resolves to a `mode` and echoes it in `result.mode`.

When using n8n, import `n8n/router.example.json`. It implements:
- Webhook → Init → **Router (Function)** → **Switch** → QA path or Strategy path
- Each path posts progress/completed events back to FastAPI via `callback_url`.

Shape of the final `result`:
```json
{
  "mode": "qa | strategy | auto",
  "input": {"prompt":"...", "doc_name":"...", "symbols":["..."], "horizon_days":5, "task":"qa"},
  "metrics": {
    "accuracy": {"rmse": 0.0, "mape": 0.0, "directional_accuracy": 0.0},
    "strategy": {"sharpe": 0.0, "max_drawdown": -0.0, "win_rate": 0.0},
    "qa": {"exact_match": 0.0, "f1": 0.0}
  },
  "qa": {...},                    // present if mode=qa or auto
  "series": {...},                // present if mode=strategy or auto
  "signals": [...],
  "equity_curve": {...}
}
```
