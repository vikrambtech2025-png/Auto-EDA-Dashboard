from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import MAX_UPLOAD_MB, UPLOAD_DIR, ensure_dirs
from .db import create_dataset, get_report, init_db, list_datasets
from .eda import load_dataframe, profile_dataframe

app = FastAPI(
    title="Auto EDA Dashboard",
    description="Full-stack automated exploratory data analysis dashboard.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/datasets")
def datasets() -> dict[str, object]:
    return {"datasets": list_datasets()}


@app.get("/api/datasets/{dataset_id}")
def dataset_report(dataset_id: int) -> dict[str, object]:
    report = get_report(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return report


@app.get("/api/datasets/{dataset_id}/download")
def download_report(dataset_id: int) -> JSONResponse:
    report = get_report(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return JSONResponse(
        report,
        headers={"Content-Disposition": f'attachment; filename="auto-eda-report-{dataset_id}.json"'},
    )


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A dataset file is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".csv", ".xls", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Only CSV, XLS, and XLSX files are supported.")

    ensure_dirs()
    stored_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    bytes_written = 0
    with stored_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_MB * 1024 * 1024:
                output.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Upload limit is {MAX_UPLOAD_MB} MB.")
            output.write(chunk)

    try:
        df = load_dataframe(str(stored_path))
        report = profile_dataframe(df, file.filename)
        dataset_id = create_dataset(
            name=Path(file.filename).stem,
            original_filename=file.filename,
            stored_path=stored_path,
            rows=report["overview"]["rows"],
            columns=report["overview"]["columns"],
            size_bytes=bytes_written,
            quality_score=report["overview"]["quality_score"],
            report=report,
        )
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved = get_report(dataset_id)
    if saved is None:
        raise HTTPException(status_code=500, detail="Report was not saved.")
    return saved


@app.post("/api/demo")
def create_demo_dataset() -> dict[str, object]:
    import numpy as np
    import pandas as pd

    ensure_dirs()
    rng = np.random.default_rng(24)
    rows = 900
    df = pd.DataFrame(
        {
            "customer_id": [f"CUST-{10000 + index}" for index in range(rows)],
            "region": rng.choice(["North", "South", "East", "West"], rows, p=[0.28, 0.21, 0.26, 0.25]),
            "segment": rng.choice(["Consumer", "SMB", "Enterprise"], rows, p=[0.58, 0.31, 0.11]),
            "monthly_spend": rng.normal(520, 140, rows).clip(40),
            "support_tickets": rng.poisson(2.2, rows),
            "tenure_months": rng.integers(1, 72, rows),
            "satisfaction": rng.normal(7.4, 1.3, rows).clip(1, 10),
            "churned": rng.choice([0, 1], rows, p=[0.82, 0.18]),
        }
    )
    missing_idx = rng.choice(df.index, size=70, replace=False)
    df.loc[missing_idx, "satisfaction"] = np.nan
    outlier_idx = rng.choice(df.index, size=8, replace=False)
    df.loc[outlier_idx, "monthly_spend"] *= 3.4

    path = UPLOAD_DIR / f"demo-{uuid.uuid4().hex}.csv"
    df.to_csv(path, index=False)
    report = profile_dataframe(df, "demo-customer-health.csv")
    dataset_id = create_dataset(
        name="Demo Customer Health",
        original_filename="demo-customer-health.csv",
        stored_path=path,
        rows=report["overview"]["rows"],
        columns=report["overview"]["columns"],
        size_bytes=path.stat().st_size,
        quality_score=report["overview"]["quality_score"],
        report=report,
    )
    saved = get_report(dataset_id)
    if saved is None:
        raise HTTPException(status_code=500, detail="Demo report was not saved.")
    return saved


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    path = BASE_DIR / "static" / "favicon.svg"
    return FileResponse(path, media_type="image/svg+xml")
