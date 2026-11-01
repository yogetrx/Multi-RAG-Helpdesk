
import pytest
from fastapi.testclient import TestClient
import uuid
import helpdesk.main as main


TEST_API_KEY = "MyHelpdeskLocalTestKey2026"
RATE_LIMIT_TEST_API_KEY = "RateLimitOnlyTestKey2026"


@pytest.fixture
def client(monkeypatch, request):
    # Give the rate-limit test a separate API-key identity.
    if request.node.name == "test_ask_rate_limit":
        monkeypatch.setenv(
            "HELPDESK_API_KEY",
            RATE_LIMIT_TEST_API_KEY,
        )
    else:
        monkeypatch.setenv(
            "HELPDESK_API_KEY",
            TEST_API_KEY,
        )

    # Mock retrieval so tests don't call FAISS or Azure OpenAI.
    class FakeRAG:
        def search(self, question, knowledge_bases, top_k):
            return []

    monkeypatch.setattr(
        main,
        "get_rag",
        lambda: FakeRAG(),
    )

    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda question, evidence: {
            "answer": "Test answer",
            "citations": [],
            "grounded": True,
            "token_usage": None,
        },
    )

    return TestClient(main.app)


def test_ask_with_valid_api_key(client):
    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={
            "question": "How do I troubleshoot VPN error 809?",
            "top_k": 3,
        },
    )

    assert response.status_code == 200


def test_ask_without_api_key(client):
    response = client.post(
        "/ask",
        json={
            "question": "How do I troubleshoot VPN error 809?",
            "top_k": 3,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_ask_with_invalid_api_key(client):
    response = client.post(
        "/ask",
        headers={"X-API-Key": "WrongTestKey123"},
        json={
            "question": "How do I troubleshoot VPN error 809?",
            "top_k": 3,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_ask_when_server_api_key_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("HELPDESK_API_KEY")

    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={
            "question": "How do I troubleshoot VPN error 809?",
            "top_k": 3,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured."


def test_ask_rate_limit(client):
    responses = []

    for _ in range(11):
        response = client.post(
            "/ask",
            headers={"X-API-Key": RATE_LIMIT_TEST_API_KEY},
            json={
                "question": "How do I troubleshoot VPN error 809?",
                "top_k": 3,
            },
        )

        responses.append(response)

    # First 10 requests should be accepted.
    assert all(
        response.status_code == 200
        for response in responses[:10]
    )

    # The 11th request should be rejected.
    assert responses[10].status_code == 429

def test_response_contains_valid_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    request_id = response.headers["X-Request-ID"]

    # Verify that the request ID is a valid UUID.
    uuid.UUID(request_id)


def test_each_request_gets_unique_request_id(client):
    first_response = client.get("/health")
    second_response = client.get("/health")

    first_id = first_response.headers["X-Request-ID"]
    second_id = second_response.headers["X-Request-ID"]

    assert first_id != second_id