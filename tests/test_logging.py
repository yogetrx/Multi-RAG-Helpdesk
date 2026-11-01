
import logging

from fastapi.testclient import TestClient

import helpdesk.main as main


def test_request_details_are_logged(caplog):
    client = TestClient(main.app)

    with caplog.at_level(logging.INFO, logger="helpdesk"):
        response = client.get("/health")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    matching_logs = [
        record
        for record in caplog.records
        if record.name == "helpdesk"
        and getattr(record, "request_id", None) == request_id
    ]

    assert len(matching_logs) == 1

    log_record = matching_logs[0]

    assert log_record.getMessage() == "HTTP request completed"
    assert log_record.method == "GET"
    assert log_record.path == "/health"
    assert log_record.status == 200
    assert log_record.duration_seconds >= 0


def test_unexpected_exception_is_logged(caplog):
    client = TestClient(main.app)

    @main.app.get("/test-logging-error")
    def trigger_error():
        raise RuntimeError("Simulated internal error")

    try:
        with caplog.at_level(logging.ERROR, logger="helpdesk"):
            client.get("/test-logging-error")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError was not raised")

    error_logs = [
        record
        for record in caplog.records
        if record.name == "helpdesk"
        and record.getMessage() == "Unexpected HTTP request error"
    ]

    assert len(error_logs) == 1

    error_log = error_logs[0]

    assert error_log.request_id is not None
    assert error_log.method == "GET"
    assert error_log.path == "/test-logging-error"
    assert error_log.duration_seconds >= 0
    assert error_log.exc_info is not None
