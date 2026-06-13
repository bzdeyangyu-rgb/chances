from frontend.app import build_page_options, build_review_queue, paginate_rows, normalize_jobs_response


def test_normalize_jobs_response_accepts_paginated_envelope():
    payload = {
        "items": [{"id": 1, "job_title": "AI产品经理"}],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }

    rows, meta = normalize_jobs_response(payload)

    assert rows[0]["job_title"] == "AI产品经理"
    assert meta["total"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 20


def test_normalize_jobs_response_keeps_legacy_list_response():
    rows, meta = normalize_jobs_response([{"id": 1, "job_title": "AI产品经理"}])

    assert rows == [{"id": 1, "job_title": "AI产品经理"}]
    assert meta["total"] == 1
    assert meta["page"] == 1


def test_build_page_options_returns_stable_page_numbers():
    assert build_page_options(total=0, page_size=20) == [1]
    assert build_page_options(total=41, page_size=20) == [1, 2, 3]


def test_paginate_rows_returns_requested_slice_and_meta():
    rows = [{"id": index} for index in range(25)]

    page_rows, meta = paginate_rows(rows, page=2, page_size=10)

    assert [row["id"] for row in page_rows] == list(range(10, 20))
    assert meta == {"total": 25, "page": 2, "page_size": 10}


def test_build_review_queue_prioritizes_pending_high_priority_jobs():
    rows = [
        {"job_title": "普通待评估", "status": "待评估", "priority": "普通"},
        {"job_title": "高优推进", "status": "建议推进", "priority": "高"},
        {"job_title": "已归档", "status": "已归档", "priority": "高"},
    ]

    queue = build_review_queue(rows)

    assert [row["job_title"] for row in queue] == ["高优推进", "普通待评估"]
