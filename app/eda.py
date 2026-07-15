from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .config import SAMPLE_ROWS


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return round(result, 6)


def _jsonable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _safe_float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _infer_semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        unique_ratio = series.nunique(dropna=True) / max(len(series.dropna()), 1)
        if series.nunique(dropna=True) <= 12 and unique_ratio < 0.2:
            return "numeric category"
        return "numeric"
    if series.nunique(dropna=True) <= 25:
        return "category"
    return "text"


def _try_dates(df: pd.DataFrame) -> pd.DataFrame:
    converted = df.copy()
    for column in converted.columns:
        series = converted[column]
        if pd.api.types.is_object_dtype(series):
            sample = series.dropna().astype(str).head(80)
            if sample.empty:
                continue
            parsed = pd.to_datetime(sample, errors="coerce", utc=False)
            if parsed.notna().mean() >= 0.8:
                converted[column] = pd.to_datetime(series, errors="coerce", utc=False)
    return converted


def load_dataframe(path: str) -> pd.DataFrame:
    suffix = path.lower().rsplit(".", 1)[-1]
    if suffix == "csv":
        return pd.read_csv(path)
    if suffix in {"xlsx", "xls"}:
        return pd.read_excel(path)
    raise ValueError("Only CSV, XLS, and XLSX files are supported.")


def profile_dataframe(df: pd.DataFrame, filename: str) -> dict[str, Any]:
    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    if len(df) > SAMPLE_ROWS:
        sampled = df.sample(SAMPLE_ROWS, random_state=42)
        sample_note = f"Charts and heavy statistics use a deterministic sample of {SAMPLE_ROWS:,} rows."
    else:
        sampled = df
        sample_note = "Full dataset used for all statistics."

    profiled = _try_dates(sampled)
    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    missing_pct = missing_cells / max(total_cells, 1)
    duplicate_pct = duplicate_rows / max(len(df), 1)

    columns: list[dict[str, Any]] = []
    numeric_columns: list[str] = []
    category_columns: list[str] = []
    alerts: list[dict[str, str]] = []

    for column in profiled.columns:
        series = profiled[column]
        non_null = series.dropna()
        semantic_type = _infer_semantic_type(series)
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        record: dict[str, Any] = {
            "name": str(column),
            "dtype": str(series.dtype),
            "semantic_type": semantic_type,
            "missing": missing,
            "missing_pct": round(missing / max(len(series), 1) * 100, 2),
            "unique": unique,
            "unique_pct": round(unique / max(len(non_null), 1) * 100, 2),
        }

        if pd.api.types.is_numeric_dtype(series):
            numeric_columns.append(column)
            quantiles = series.quantile([0.25, 0.5, 0.75]).to_dict()
            q1 = quantiles.get(0.25)
            q3 = quantiles.get(0.75)
            iqr = None if pd.isna(q1) or pd.isna(q3) else q3 - q1
            outliers = 0
            if iqr and iqr > 0:
                outliers = int(
                    ((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum()
                )
            record.update(
                {
                    "mean": _safe_float(series.mean()),
                    "std": _safe_float(series.std()),
                    "min": _safe_float(series.min()),
                    "q1": _safe_float(q1),
                    "median": _safe_float(quantiles.get(0.5)),
                    "q3": _safe_float(q3),
                    "max": _safe_float(series.max()),
                    "skew": _safe_float(series.skew()),
                    "outliers": outliers,
                    "outlier_pct": round(outliers / max(len(non_null), 1) * 100, 2),
                }
            )
        else:
            category_columns.append(column)
            top_values = series.astype("string").value_counts(dropna=True).head(8)
            record["top_values"] = [
                {"label": str(index), "count": int(value)}
                for index, value in top_values.items()
            ]
            if pd.api.types.is_datetime64_any_dtype(series):
                record["min"] = None if non_null.empty else str(non_null.min())
                record["max"] = None if non_null.empty else str(non_null.max())

        if record["missing_pct"] >= 30:
            alerts.append(
                {
                    "level": "high",
                    "title": f"{column} has heavy missingness",
                    "detail": f"{record['missing_pct']}% of sampled values are missing.",
                }
            )
        if record["unique_pct"] >= 95 and semantic_type == "text":
            alerts.append(
                {
                    "level": "medium",
                    "title": f"{column} may be an identifier",
                    "detail": "Nearly every non-empty value is unique.",
                }
            )
        columns.append(record)

    if duplicate_pct >= 0.05:
        alerts.append(
            {
                "level": "medium",
                "title": "Duplicate rows detected",
                "detail": f"{duplicate_rows:,} rows are duplicated in the full dataset.",
            }
        )

    numeric_df = (
        profiled[numeric_columns].select_dtypes(include=[np.number])
        if numeric_columns
        else pd.DataFrame()
    )
    correlations: list[dict[str, Any]] = []
    correlation_matrix: dict[str, dict[str, float | None]] = {}
    if len(numeric_df.columns) >= 2:
        corr = numeric_df.corr(numeric_only=True)
        for left in corr.columns:
            correlation_matrix[str(left)] = {
                str(right): _safe_float(corr.loc[left, right]) for right in corr.columns
            }
        for i, left in enumerate(corr.columns):
            for right in corr.columns[i + 1 :]:
                value = _safe_float(corr.loc[left, right])
                if value is not None:
                    correlations.append(
                        {
                            "left": str(left),
                            "right": str(right),
                            "value": value,
                            "abs": abs(value),
                        }
                    )
        correlations = sorted(correlations, key=lambda item: item["abs"], reverse=True)[
            :10
        ]

    charts = {
        "missing": [
            {"label": item["name"], "value": item["missing_pct"]}
            for item in sorted(
                columns, key=lambda col: col["missing_pct"], reverse=True
            )[:12]
        ],
        "distributions": [],
        "categories": [],
    }

    for column in numeric_df.columns[:6]:
        values = numeric_df[column].dropna()
        if values.empty:
            continue
        counts, edges = np.histogram(
            values, bins=min(14, max(5, int(math.sqrt(len(values)))))
        )
        charts["distributions"].append(
            {
                "column": str(column),
                "bins": [
                    {
                        "label": f"{_safe_float(edges[i])} to {_safe_float(edges[i + 1])}",
                        "count": int(counts[i]),
                    }
                    for i in range(len(counts))
                ],
            }
        )

    for column in category_columns[:6]:
        values = profiled[column].astype("string").value_counts(dropna=True).head(8)
        if not values.empty:
            charts["categories"].append(
                {
                    "column": str(column),
                    "values": [
                        {"label": str(index), "count": int(count)}
                        for index, count in values.items()
                    ],
                }
            )

    quality_score = max(
        0, 100 - (missing_pct * 45) - (duplicate_pct * 25) - min(len(alerts) * 3, 20)
    )
    quality_score = round(float(quality_score), 1)

    return {
        "filename": filename,
        "overview": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "sampled_rows": int(len(profiled)),
            "missing_cells": missing_cells,
            "missing_pct": round(missing_pct * 100, 2),
            "duplicate_rows": duplicate_rows,
            "duplicate_pct": round(duplicate_pct * 100, 2),
            "quality_score": quality_score,
            "sample_note": sample_note,
        },
        "schema": {
            "numeric": len(numeric_columns),
            "categorical": len(category_columns),
            "columns": columns,
        },
        "correlations": correlations,
        "correlation_matrix": correlation_matrix,
        "charts": charts,
        "alerts": alerts[:12],
        "preview": [
            {str(key): _jsonable(value) for key, value in row.items()}
            for row in df.head(10).to_dict(orient="records")
        ],
    }
