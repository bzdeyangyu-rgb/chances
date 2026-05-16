# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from frontend.labels import COLUMN_ORDER


DEFAULT_WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "jobs.xlsx"


def create_empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMN_ORDER)


def normalize_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()

    for column in COLUMN_ORDER:
        if column not in normalized.columns:
            normalized[column] = ""

    normalized = normalized[COLUMN_ORDER].fillna("")

    for column in COLUMN_ORDER:
        normalized[column] = normalized[column].astype(str)

    return normalized


def save_jobs(frame: pd.DataFrame, workbook_path: Path | str = DEFAULT_WORKBOOK) -> pd.DataFrame:
    path = Path(workbook_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    normalized = normalize_dataframe(frame)
    normalized.to_excel(path, index=False)
    return normalized


def load_or_initialize_jobs(workbook_path: Path | str = DEFAULT_WORKBOOK) -> pd.DataFrame:
    path = Path(workbook_path)

    if not path.exists():
        return save_jobs(create_empty_dataframe(), path)

    frame = pd.read_excel(path, dtype=str).fillna("")
    return save_jobs(frame, path)


def filter_jobs(
    frame: pd.DataFrame,
    sites: list[str] | None = None,
    keyword: str = "",
    location: str = "",
) -> pd.DataFrame:
    filtered = normalize_dataframe(frame)

    if sites:
        filtered = filtered[filtered["招聘网站"].isin(sites)]

    if keyword:
        token = keyword.strip().lower()
        mask = (
            filtered["岗位名称"].str.lower().str.contains(token)
            | filtered["公司名称"].str.lower().str.contains(token)
            | filtered["技能要求"].str.lower().str.contains(token)
            | filtered["主要信息"].str.lower().str.contains(token)
        )
        filtered = filtered[mask]

    if location:
        filtered = filtered[filtered["工作地点"].str.contains(location.strip(), case=False, na=False)]

    return filtered
