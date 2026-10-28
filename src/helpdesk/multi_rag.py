
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

from helpdesk.ingestion import load_documents
from helpdesk.retrieval.fusion import fuse_results
from helpdesk.retrieval.vector_store import VectorStore
from helpdesk.router import select_knowledge_bases


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

# Initial threshold; calibrate using evaluation results.
MIN_RELEVANCE_SCORE = float(
    os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.30")
)

KNOWLEDGE_BASES = {
    "troubleshooting": DATA_DIR / "troubleshooting",
    "access_policies": DATA_DIR / "access_policies",
    "it_documentation": DATA_DIR / "it_documentation",
}


class MultiRAG:
    def __init__(self):
        # One shared embedding model, three independent vector indexes.
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.stores = {}

        for name, folder in KNOWLEDGE_BASES.items():
            store = VectorStore(self.model)
            documents = load_documents(str(folder), name)
            store.add_documents(documents)
            self.stores[name] = store

    def search(
        self,
        query: str,
        knowledge_bases: list[str] | None = None,
        top_k: int = 3,
    ) -> list[dict]:
        if not query or not query.strip():
            return []

        selected = (
            knowledge_bases
            if knowledge_bases is not None
            else select_knowledge_bases(query)
        )

        results = []

        for name in selected:
            if name not in self.stores:
                raise ValueError(f"Unknown knowledge base: {name}")

            results.extend(
                self.stores[name].search(query, top_k=top_k)
            )

        # Discard weak matches before combining the evidence.
        relevant_results = [
            item
            for item in results
            if item.get("score", float("-inf"))
            >= MIN_RELEVANCE_SCORE
        ]

        if not relevant_results:
            return []

        return fuse_results(relevant_results, top_k=top_k)
