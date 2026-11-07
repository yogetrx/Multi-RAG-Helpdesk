
from fastapi.testclient import TestClient
import helpdesk.main as main


TEST_API_KEY = "HybridTestKey2026"


def setup_hybrid_test(monkeypatch):
    monkeypatch.setenv("HELPDESK_API_KEY", TEST_API_KEY)

    class FakeRAG:
        def search(self, question, knowledge_bases, top_k):
            return [
                {
                    "id": 1,
                    "text": "VPN Error 809 troubleshooting instructions",
                    "source": "vpn-guide.txt",
                    "knowledge_base": "troubleshooting",
                    "score": 0.95,
                }
            ]

    monkeypatch.setattr(main, "get_rag", lambda: FakeRAG())

    return TestClient(main.app)


def test_general_question_uses_general_mode(monkeypatch):
    client = setup_hybrid_test(monkeypatch)
    captured = {}

    def fake_generate_answer(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "Photosynthesis converts light into chemical energy.",
            "citations": [],
            "grounded": False,
            "token_usage": None,
        }

    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={"question": "Explain photosynthesis in simple terms."},
    )

    assert response.status_code == 200
    assert captured["mode"] == "general"
    assert captured["evidence"] == []
    assert response.json()["selected_knowledge_bases"] == []


def test_company_question_uses_rag_mode(monkeypatch):
    client = setup_hybrid_test(monkeypatch)
    captured = {}

    def fake_generate_answer(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "Follow the VPN troubleshooting instructions.",
            "citations": [
                {
                    "id": 1,
                    "source": "vpn-guide.txt",
                    "knowledge_base": "troubleshooting",
                }
            ],
            "grounded": True,
            "token_usage": None,
        }

    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={"question": "How do I troubleshoot VPN error 809?"},
    )

    assert response.status_code == 200
    assert captured["mode"] == "rag"
    assert len(captured["evidence"]) > 0
    assert "troubleshooting" in response.json()["selected_knowledge_bases"]


def test_conversation_history_reaches_generation(monkeypatch):
    client = setup_hybrid_test(monkeypatch)
    captured = {}

    def fake_generate_answer(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "Try restarting the VPN connection.",
            "citations": [],
            "grounded": True,
            "token_usage": None,
        }

    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    history = [
        {
            "role": "user",
            "content": "How do I troubleshoot VPN error 809?",
        },
        {
            "role": "assistant",
            "content": "Check your VPN connection settings.",
        },
    ]

    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={
            "question": "What should I try next?",
            "conversation_history": history,
        },
    )

    assert response.status_code == 200
    assert captured["conversation_history"] == history
    assert captured["mode"] == "rag"

def test_follow_up_uses_contextualized_query_for_retrieval(monkeypatch):
    client = setup_hybrid_test(monkeypatch)

    captured = {
        "retrieval_query": None,
        "generation_query": None,
    }

    rewritten_question = (
        "What additional troubleshooting steps can "
        "resolve VPN error 809?"
    )

    # Mock contextualization to avoid a real Azure API call.
    def fake_contextualize_question(query, conversation_history):
        return rewritten_question

    monkeypatch.setattr(
        main,
        "contextualize_question",
        fake_contextualize_question,
    )

    # Capture the exact question sent to FAISS.
    class TrackingRAG:
        def search(self, question, knowledge_bases, top_k):
            captured["retrieval_query"] = question

            return [
                {
                    "id": 1,
                    "text": "Check VPN firewall and network settings.",
                    "source": "vpn-guide.txt",
                    "knowledge_base": "troubleshooting",
                    "score": 0.95,
                }
            ]

    monkeypatch.setattr(
        main,
        "get_rag",
        lambda: TrackingRAG(),
    )

    # Capture the original question sent to answer generation.
    def fake_generate_answer(**kwargs):
        captured["generation_query"] = kwargs["query"]

        return {
            "answer": "Check your VPN firewall settings.",
            "citations": [
                {
                    "id": 1,
                    "source": "vpn-guide.txt",
                    "knowledge_base": "troubleshooting",
                }
            ],
            "grounded": True,
            "token_usage": None,
        }

    monkeypatch.setattr(
        main,
        "generate_answer",
        fake_generate_answer,
    )

    original_question = "What should I try next?"

    history = [
        {
            "role": "user",
            "content": "How do I troubleshoot VPN error 809?",
        },
        {
            "role": "assistant",
            "content": "Check your VPN connection settings.",
        },
    ]

    response = client.post(
        "/ask",
        headers={"X-API-Key": TEST_API_KEY},
        json={
            "question": original_question,
            "conversation_history": history,
        },
    )

    assert response.status_code == 200

    # FAISS must receive the rewritten question.
    assert captured["retrieval_query"] == rewritten_question

    # Answer generation must receive the original question.
    assert captured["generation_query"] == original_question

    # Routing must select the troubleshooting knowledge base.
    assert "troubleshooting" in (
        response.json()["selected_knowledge_bases"]
    )
