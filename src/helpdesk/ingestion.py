
from pathlib import Path


def load_documents(folder: str, source_name: str) -> list[dict]:
    """Read text files and split them into overlapping chunks."""
    documents = []
    directory = Path(folder)

    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        # Simple starter chunking. We will improve this later.
        chunk_size = 700
        overlap = 100
        start = 0
        chunk_number = 0

        while start < len(text):
            chunk = text[start:start + chunk_size].strip()

            if chunk:
                documents.append({
                    "text": chunk,
                    "source": path.name,
                    "knowledge_base": source_name,
                    "chunk_id": chunk_number,
                })
                chunk_number += 1

            if start + chunk_size >= len(text):
                break

            start += chunk_size - overlap

    return documents
