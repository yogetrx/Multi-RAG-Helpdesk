
from helpdesk.multi_rag import MultiRAG


def test_multi_rag_search_returns_source_metadata():
    rag = MultiRAG()

    results = rag.search(
        "How do I fix VPN error 809?",
        knowledge_bases=["troubleshooting"],
        top_k=2,
    )

    assert results
    assert results[0]["knowledge_base"] == "troubleshooting"
    assert "source" in results[0]
    assert "score" in results[0]


def test_multi_rag_searches_multiple_knowledge_bases():
    rag = MultiRAG()

    results = rag.search(
        "How do I get Azure permissions?",
        knowledge_bases=["access_policies", "it_documentation"],
        top_k=2,
    )

    assert results
    assert {
        result["knowledge_base"] for result in results
    }.issubset({"access_policies", "it_documentation"})
