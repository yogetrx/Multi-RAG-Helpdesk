
import pytest
from fastapi.testclient import TestClient

import helpdesk.main as main


TEST_API_KEY = "MyHelpdeskLocalTestKey2026"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HELPDESK_API_KEY", TEST_API_KEY)

    # Mock retrieval so this test doesn't call FAISS or Azure OpenAI.
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

    return TestClient(main.app)


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
