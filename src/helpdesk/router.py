
import re


ROUTING_RULES = {
    "troubleshooting": {
        "vpn", "error", "809", "connection", "connectivity",
        "firewall", "network", "broken", "not working", "failed",
        "failure", "diagnostic", "troubleshoot",
    },
    "access_policies": {
        "azure", "permission", "permissions", "access",
        "rbac", "role", "roles", "authorization", "authorize",
        "privilege", "privileges", "approval",
    },
    "it_documentation": {
        "procedure", "procedures", "escalate", "escalation",
        "support", "support team", "ticket", "tickets",
        "documentation", "it process", "unresolved",
    },
}

IT_DOCUMENTATION_KEYWORDS = {
    "support", "support team", "ticket", "tickets",
    "documentation", "it process", "escalate", "escalation",
    "unresolved",
}


def contains_keyword(text: str, keyword: str) -> bool:
    """Match whole words or phrases."""
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, text) is not None


def select_knowledge_bases(query: str) -> list[str]:
    """Select knowledge bases using keyword matching and routing rules."""
    if not query or not query.strip():
        return []

    text = query.lower()
    selected = []

    for knowledge_base, keywords in ROUTING_RULES.items():
        if any(contains_keyword(text, keyword) for keyword in keywords):
            selected.append(knowledge_base)

    # Avoid routing a simple Azure permission procedure question
    # to general IT documentation unless it mentions a specific
    # support workflow.
    if (
        "it_documentation" in selected
        and "access_policies" in selected
        and not any(
            contains_keyword(text, keyword)
            for keyword in IT_DOCUMENTATION_KEYWORDS
        )
    ):
        selected.remove("it_documentation")

    # If no rules match, search all available knowledge bases.
    return selected or list(ROUTING_RULES.keys())
