
import json
from pathlib import Path

from helpdesk.multi_rag import MultiRAG
from helpdesk.router import select_knowledge_bases


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "test_cases.json"


def evaluate():
    # Load test cases from either supported JSON format
    data = json.loads(DATASET.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        cases = data.get("test_cases", [])
    elif isinstance(data, list):
        cases = data
    else:
        raise ValueError(
            "Test dataset must be a list or an object containing 'test_cases'."
        )

    if not cases:
        raise ValueError("No test cases found in test_cases.json.")

    if not all(
        isinstance(case, dict)
        and "question" in case
        and "expected_knowledge_bases" in case
        and "expected_sources" in case
        for case in cases
    ):
        raise ValueError(
            "Each test case must contain question, "
            "expected_knowledge_bases, and expected_sources."
        )

    rag = MultiRAG()

    routing_passes = 0
    exact_match_passes = 0
    hit_passes = 0
    routing_precision_scores = []
    routing_recall_scores = []
    source_recall_scores = []

    print(f"\nEvaluating {len(cases)} test cases...\n")

    for case in cases:
        question = case["question"]
        expected_kbs = set(case["expected_knowledge_bases"])
        expected_sources = set(case["expected_sources"])

        selected_kbs = set(select_knowledge_bases(question))

        # Routing metrics
        correct_kbs = expected_kbs & selected_kbs

        routing_ok = expected_kbs.issubset(selected_kbs)
        exact_match = expected_kbs == selected_kbs

        routing_precision = (
            len(correct_kbs) / len(selected_kbs)
            if selected_kbs
            else 0.0
        )

        routing_recall = (
            len(correct_kbs) / len(expected_kbs)
            if expected_kbs
            else 1.0
        )

        # Retrieve evidence from the selected knowledge bases
        results = rag.search(
            question,
            knowledge_bases=sorted(selected_kbs),
            top_k=3,
        )

        retrieved_sources = {
            result["source"] for result in results
        }

        # Source retrieval metrics
        hits = expected_sources & retrieved_sources
        hit_ok = bool(hits)

        source_recall = (
            len(hits) / len(expected_sources)
            if expected_sources
            else 1.0
        )

        # Update aggregate metrics
        routing_passes += int(routing_ok)
        exact_match_passes += int(exact_match)
        hit_passes += int(hit_ok)

        routing_precision_scores.append(routing_precision)
        routing_recall_scores.append(routing_recall)
        source_recall_scores.append(source_recall)

        # Print per-case results
        print(f"Question: {question}")
        print(f"Expected knowledge bases: {sorted(expected_kbs)}")
        print(f"Selected knowledge bases: {sorted(selected_kbs)}")
        print(f"Routing completeness: {'PASS' if routing_ok else 'FAIL'}")
        print(f"Exact match: {'PASS' if exact_match else 'FAIL'}")
        print(f"Routing precision: {routing_precision:.2f}")
        print(f"Routing recall: {routing_recall:.2f}")
        print(f"Expected sources: {sorted(expected_sources)}")
        print(f"Retrieved sources: {sorted(retrieved_sources)}")
        print(f"Source hit: {'PASS' if hit_ok else 'FAIL'}")
        print(f"Source Recall@3: {source_recall:.2f}")
        print("-" * 60)

    count = len(cases)

    # Print aggregate results
    print("\n===== SUMMARY =====")
    print(f"Routing completeness: {routing_passes}/{count}")
    print(f"Exact-match accuracy: {exact_match_passes}/{count}")
    print(
        "Mean routing precision: "
        f"{sum(routing_precision_scores) / count:.2%}"
    )
    print(
        "Mean routing recall: "
        f"{sum(routing_recall_scores) / count:.2%}"
    )
    print(f"Source hit rate: {hit_passes}/{count}")
    print(
        "Mean source Recall@3: "
        f"{sum(source_recall_scores) / count:.2%}"
    )


if __name__ == "__main__":
    evaluate()
