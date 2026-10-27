
from pathlib import Path

from helpdesk.ingestion import load_documents


ROOT = Path(__file__).resolve().parents[1]


def test_all_three_knowledge_bases_have_documents():
    folders = {
        "troubleshooting": ROOT / "data" / "troubleshooting",
        "access_policies": ROOT / "data" / "access_policies",
        "it_documentation": ROOT / "data" / "it_documentation",
    }

    for name, folder in folders.items():
        documents = load_documents(str(folder), name)
        assert documents, f"No documents loaded for {name}"
        assert all(doc["knowledge_base"] == name for doc in documents)
