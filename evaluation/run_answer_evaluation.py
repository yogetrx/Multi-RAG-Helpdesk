
import json
from pathlib import Path

from helpdesk.multi_rag import MultiRAG
from helpdesk.router import select_knowledge_bases
from helpdesk.generation.answer import generate_answer


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "answer_quality_cases.json"


def evaluate():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["test_cases"]

    rag = MultiRAG()

    source_passes = 0
    citation_passes = 0
    fact_checks_passed = 0

    print(f"\nEvaluating {len(cases)} answer-quality cases...\n")

    for case in cases:
        question = case["question"]
        expected_source = case["expected_source"]
        expected_facts = case["expected_facts"]

        selected_kbs = select_knowledge_bases(question)

        evidence = rag.search(
            question,
            knowledge_bases=selected_kbs,
            top_k=3,
        )

        result = generate_answer(question, evidence)
        answer = result["answer"]

        cited_sources = {
            citation["source"]
            for citation in result["citations"]
            if f'[{citation["id"]}]' in answer
        }

        source_ok = expected_source in cited_sources

        valid_citation_ids = {
            str(citation["id"])
            for citation in result["citations"]
        }

        import re

        used_ids = set(re.findall(r"\[(\d+)\]", answer))
        citation_ok = bool(used_ids) and used_ids.issubset(
            valid_citation_ids
        )

        answer_lower = answer.lower()
        facts_ok = all(
            fact.lower() in answer_lower
            for fact in expected_facts
        )

        source_passes += int(source_ok)
        citation_passes += int(citation_ok)
        fact_checks_passed += int(facts_ok)

        print(f"ID: {case['id']}")
        print(f"Question: {question}")
        print(f"Answer: {answer}")
        print(f"Expected source cited: {'PASS' if source_ok else 'FAIL'}")
        print(f"Citation IDs valid: {'PASS' if citation_ok else 'FAIL'}")
        print(f"Expected keyword check: {'PASS' if facts_ok else 'FAIL'}")
        print(f"Grounded flag: {result['grounded']}")
        print("-" * 60)

    count = len(cases)

    print("\n===== ANSWER EVALUATION SUMMARY =====")
    print(f"Expected source cited: {source_passes}/{count}")
    print(f"Valid citation IDs: {citation_passes}/{count}")
    print(f"Expected keyword checks: {fact_checks_passed}/{count}")


if __name__ == "__main__":
    evaluate()
