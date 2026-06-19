---
title: Auto EDA Dashboard
emoji: ":bar_chart:"
colorFrom: teal
colorTo: amber
sdk: docker
app_port: 7860
pinned: false
---

# Auto EDA Dashboard

Full-stack automated exploratory data analysis application with a FastAPI backend, SQLite persistence, pandas/numpy profiling, and a modern dependency-free dashboard UI.

## Features

- CSV, XLS, and XLSX upload flow
- Persistent dataset run history
- Automated data quality score
- Missing value analysis
- Duplicate row detection
- Semantic type inference
- Numeric summaries, quantiles, skew, and IQR outlier detection
- Top category summaries
- Pearson correlation ranking
- Canvas-based dashboard charts
- JSON report export
- Docker, Render, and Railway deployment config

## Local Run

From `D:\AI-Projects`:

```powershell
cd auto-eda-dashboard
..\ai-env\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

If you are using a fresh Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker Run

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000`.

## Deployment

### Render

1. Push this folder to a GitHub repository.
2. Create a new Render Blueprint from the repository.
3. Render will read `render.yaml`, build the Docker image, mount persistent storage at `/app/data`, and expose the web service.

### Railway

1. Push this folder to a GitHub repository.
2. Create a Railway project from the repository.
3. Railway will use `railway.json` and the Dockerfile.
4. Add a persistent volume mounted to `/app/data` if you want uploaded files and SQLite history to survive redeploys.

## Notes

SQLite is configured with WAL mode and is efficient for this application profile: report metadata, generated EDA JSON, and upload history. For a multi-user SaaS version, the next database step is PostgreSQL with object storage for uploaded files.
