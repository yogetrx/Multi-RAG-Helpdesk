import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from helpdesk.generation.answer import generate_answer


def test_answer_includes_source_citations():
    evidence = [{
        "text": "Verify internet connectivity.",
        "source": "vpn.txt",
        "knowledge_base": "troubleshooting",
        "score": 0.8,
    }]

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Verify internet connectivity first. [1]"
                )
            )
        ]
    )

    with patch(
        "helpdesk.generation.answer.OpenAI"
    ) as mock_openai:
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_response

        response = generate_answer("VPN issue", evidence)

    assert response["grounded"] is True
    assert response["citations"][0]["source"] == "vpn.txt"
    assert "Verify internet connectivity" in response["answer"]
    client.chat.completions.create.assert_called_once()


def test_answer_handles_missing_evidence():
    response = generate_answer("Unknown issue", [])

    assert response["grounded"] is False
    assert response["citations"] == []


def test_answer_handles_empty_query():
    response = generate_answer("  ", [])

    assert response["grounded"] is False
    assert response["citations"] == []

def test_answer_rejects_invalid_citation_ids():
    evidence = [{
        "text": "Verify internet connectivity.",
        "source": "vpn.txt",
        "knowledge_base": "troubleshooting",
        "score": 0.8,
    }]

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="The VPN uses port 9999. [99]"
                )
            )
        ]
    )

    with patch(
        "helpdesk.generation.answer.OpenAI"
    ) as mock_openai:
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_response

        response = generate_answer("VPN issue", evidence)

    assert response["grounded"] is False
    assert "invalid citations" in response["answer"]


def test_answer_marks_uncited_answer_not_grounded():
    evidence = [{
        "text": "Verify internet connectivity.",
        "source": "vpn.txt",
        "knowledge_base": "troubleshooting",
        "score": 0.8,
    }]

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Verify internet connectivity first."
                )
            )
        ]
    )

    with patch(
        "helpdesk.generation.answer.OpenAI"
    ) as mock_openai:
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_response

        response = generate_answer("VPN issue", evidence)

    assert response["grounded"] is False
    assert response["citations"][0]["source"] == "vpn.txt"

def test_answer_marks_unsupported_response_not_grounded():
    evidence = [{
        "text": "Azure access policies and VPN troubleshooting.",
        "source": "support.txt",
        "knowledge_base": "it_documentation",
        "score": 0.8,
    }]

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "The exact employee bonus percentage cannot be "
                        "determined from the provided evidence. [1]"
                    )
                )
            )
        ]
    )

    with patch(
        "helpdesk.generation.answer.OpenAI"
    ) as mock_openai, patch(
        "helpdesk.generation.answer.settings.azure_openai_endpoint",
        "https://example.openai.azure.com/",
    ):
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_response

        response = generate_answer(
            "What is the exact employee bonus percentage for this year?",
            evidence,
        )

    assert response["grounded"] is False
    assert "cannot be determined" in response["answer"]
