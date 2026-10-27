
from helpdesk.router import select_knowledge_bases


def test_vpn_question_routes_to_troubleshooting():
    assert select_knowledge_bases(
        "How do I fix VPN error 809?"
    ) == ["troubleshooting"]


def test_azure_permissions_routes_to_access_policies():
    assert select_knowledge_bases(
        "How do I request Azure permissions?"
    ) == ["access_policies"]


def test_escalation_routes_to_it_documentation():
    assert select_knowledge_bases(
        "How do I escalate an unresolved ticket?"
    ) == ["it_documentation"]


def test_combined_question_routes_to_multiple_sources():
    selected = select_knowledge_bases(
        "My VPN is broken and I need Azure access"
    )

    assert "troubleshooting" in selected
    assert "access_policies" in selected


def test_unknown_question_uses_fallback():
    assert set(select_knowledge_bases(
        "Tell me about something unusual"
    )) == {
        "troubleshooting",
        "access_policies",
        "it_documentation",
    }


def test_empty_question_returns_no_sources():
    assert select_knowledge_bases("   ") == []
