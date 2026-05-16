from frontend.app import collect_bulk_job_ids


def test_collect_bulk_job_ids_returns_selected_ids():
    rows = [{"id": 1, "selected": True}, {"id": 2, "selected": False}, {"id": 3, "selected": True}]

    assert collect_bulk_job_ids(rows) == [1, 3]
