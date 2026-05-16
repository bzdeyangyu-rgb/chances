from pathlib import Path

import pandas as pd

from frontend.data_store import COLUMN_ORDER, create_empty_dataframe, load_or_initialize_jobs


def test_create_empty_dataframe_uses_requested_column_order():
    frame = create_empty_dataframe()

    assert list(frame.columns) == COLUMN_ORDER
    assert frame.empty


def test_load_or_initialize_jobs_creates_workbook_when_missing(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"

    frame = load_or_initialize_jobs(workbook_path)

    assert workbook_path.exists()
    assert list(frame.columns) == COLUMN_ORDER
    assert frame.empty


def test_load_or_initialize_jobs_preserves_existing_rows_and_backfills_columns(tmp_path: Path):
    workbook_path = tmp_path / "jobs.xlsx"
    original = pd.DataFrame(
        [
            {
                "招聘网站": "Boss直聘",
                "岗位名称": "算法工程师",
                "公司名称": "示例科技",
                "薪资": "25K-45K",
                "详情页": "https://example.com/job/1",
            }
        ]
    )
    original.to_excel(workbook_path, index=False)

    frame = load_or_initialize_jobs(workbook_path)

    assert list(frame.columns) == COLUMN_ORDER
    assert frame.loc[0, "招聘网站"] == "Boss直聘"
    assert frame.loc[0, "岗位名称"] == "算法工程师"
    assert frame.loc[0, "技能要求"] == ""
    assert frame.loc[0, "主要信息"] == ""
