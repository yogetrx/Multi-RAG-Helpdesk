
import pytest
from fastapi.testclient import TestClient

import helpdesk.main as main


TEST_API_KEY = "MyHelpdeskLocalTestKey2026"


@pytest.fixture
def client(monkeypatch, request):
    monkeypatch.setenv("HELPDESK_API_KEY", TEST_API_KEY)

    # Mock retrieval so tests don't call FAISS or Azure OpenAI.
    class FakeRAG:
        def search(self, question, knowledge_bases, top_k):
            return []

    monkeypatch.setattr(main, "get_rag", lambda: FakeRAG())

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

    # Give the rate-limit test its own IP address.
    if request.node.name == "test_ask_rate_limit":
        test_client = TestClient(
            main.app,
            client=("198.51.100.10", 50000),
        )
    else:
        test_client = TestClient(main.app)

    return test_client


def test_ask_with_valid_api_key(client):
    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={"question": "How do I troubleshoot VPN error 809?", "top_k": 3},
    )

    assert response.status_code == 200


def test_ask_without_api_key(client):
    response = client.post(
        "/ask",
        json={"question": "How do I troubleshoot VPN error 809?", "top_k": 3},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_ask_with_invalid_api_key(client):
    response = client.post(
        "/ask",
        headers={"X-API-Key": "WrongTestKey123"},
        json={"question": "How do I troubleshoot VPN error 809?", "top_k": 3},
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
            headers={"X-API-Key": TEST_API_KEY},
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
