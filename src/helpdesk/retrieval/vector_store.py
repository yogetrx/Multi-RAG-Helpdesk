
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class VectorStore:
    def __init__(self, model: SentenceTransformer):
        self.model = model
        self.index = None
        self.documents = []

    def add_documents(self, documents: list[dict]) -> None:
        if not documents:
            return

        texts = [doc["text"] for doc in documents]

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        if self.index is None:
            self.index = faiss.IndexFlatIP(vectors.shape[1])

        self.index.add(vectors)
        self.documents.extend(documents)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if self.index is None or not self.documents:
            return []

        vector = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        k = min(top_k, len(self.documents))
        scores, indices = self.index.search(vector, k)

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            results.append({
                **self.documents[int(idx)],
                "score": float(score),
            })

        return results
