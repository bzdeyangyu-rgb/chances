from pathlib import Path

from frontend.app import present_application_events, present_open_tasks


def test_frontend_has_no_known_english_section_labels():
    source = (
        Path(__file__).resolve().parents[2] / "frontend" / "app.py"
    ).read_text(encoding="utf-8")

    for label in (
        "TODAY OPERATIONS",
        "WEEKLY REVIEW",
        "CANDIDATE SPEC",
        "Local job operating system",
    ):
        assert label not in source


def test_internal_event_and_task_values_are_presented_in_chinese():
    events = present_application_events(
        [{"event_at": "2026-06-13", "event_type": "applied", "channel": "BOSS", "note": ""}]
    )
    tasks = present_open_tasks(
        [{"id": 1, "title": "跟进", "due_date": "2026-06-14", "status": "open"}]
    )

    assert events.loc[0, "事件"] == "已投递"
    assert tasks.loc[0, "状态"] == "待完成"
