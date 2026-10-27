
import json
import re
from pathlib import Path

from helpdesk.multi_rag import MultiRAG
from helpdesk.router import select_knowledge_bases
from helpdesk.generation.answer import generate_answer


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "abstention_cases.json"

ABSTENTION_PATTERNS = (
     r"couldn.t find supporting evidence",
    r"does not mention",
    r"does not contain any information",
    r"doesn.t contain.*information",
    r"not enough information",
    r"not enough evidence",
    r"insufficient evidence",
    r"i don.t have enough information",
    r"i don.t have enough evidence",
    r"i don.t have evidence",
    r"no evidence about",
    r"i cannot determine",
    r"i can.t determine",
    r"cannot determine",
    r"can.t determine",
    r"unable to determine",
    r"none mention",
    r"not provided in the documents",
    r"not available in the provided documents",
    r"cannot answer from the provided documents",
    r"can.t answer from the provided documents",
    r"please contact it support",
)


def answer_indicates_abstention(answer: str) -> bool:
    """Detect common phrases indicating insufficient evidence."""
    text = answer.lower()
    text = text.replace("’", "'").replace("‘", "'")

    return any(
        re.search(pattern, text)
        for pattern in ABSTENTION_PATTERNS
    )


def evaluate():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["test_cases"]

    if not cases:
        print("No abstention test cases found.")
        return

    rag = MultiRAG()
    passed = 0
    failed_cases = []

    print(f"\nEvaluating {len(cases)} abstention cases...\n")

    for case in cases:
        question = case["question"]

        selected_kbs = select_knowledge_bases(question)

        evidence = rag.search(
            question,
            knowledge_bases=selected_kbs,
            top_k=3,
        )

        result = generate_answer(question, evidence)

        answer = result["answer"]
        abstained = answer_indicates_abstention(answer)

        expected_behavior = case["expected_behavior"]

        if expected_behavior == "abstain":
            passed_case = abstained
        elif expected_behavior == "answer":
            passed_case = not abstained
        else:
            raise ValueError(
                f"Unsupported expected_behavior: {expected_behavior}"
            )

        passed += int(passed_case)

        print(f"ID: {case['id']}")
        print(f"Question: {question}")
        print(f"Selected knowledge bases: {selected_kbs}")
        print(f"Retrieved evidence count: {len(evidence)}")
        print(f"Answer: {answer}")
        print(f"Grounded flag: {result['grounded']}")
        print(f"Detected abstention: {abstained}")
        print(
            f"Abstention check: {'PASS' if passed_case else 'FAIL'}"
        )

        if not passed_case:
            failed_cases.append({
                "id": case["id"],
                "question": question,
                "answer": answer,
                "detected_abstention": abstained,
                "expected_behavior": expected_behavior,
            })

        print("-" * 60)

    count = len(cases)

    print("\n===== ABSTENTION SUMMARY =====")
    print(f"Passed: {passed}/{count}")
    print(f"Failed: {count - passed}/{count}")
    print(f"Pass rate: {passed / count:.2%}")

    print("\n===== FAILED CASE DETAILS =====")

    if failed_cases:
        for item in failed_cases:
            print(f"\nID: {item['id']}")
            print(f"Question: {item['question']}")
            print(f"Answer: {item['answer']!r}")
            print(
                f"Expected behavior: {item['expected_behavior']}"
            )
            print(
                f"Detected abstention: "
                f"{item['detected_abstention']}"
            )
    else:
        print("No failed cases.")


if __name__ == "__main__":
    evaluate()
