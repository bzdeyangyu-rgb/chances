from scripts.doctor import run_checks


def test_run_checks_reports_required_services():
    result = run_checks()

    assert "database" in result
    assert "frontend" in result
