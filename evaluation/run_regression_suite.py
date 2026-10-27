
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
REPORT_DIR = EVALUATION_DIR / "reports"

EVALUATORS = [
    ("routing_retrieval", "run_evaluation.py"),
    ("answer_quality", "run_answer_evaluation.py"),
    ("abstention", "run_abstention_evaluation.py"),
    ("grounding", "run_grounding_evaluation.py"),
    ("adversarial", "run_adversarial_evaluation.py"),
    ("prompt_injection", "run_prompt_injection_evaluation.py"),
]


def parse_count(output, label):
    """Parse summaries such as 'Failed: 0' or 'Failed: 0/5'."""
    match = re.search(
        rf"^\s*{re.escape(label)}:\s*(\d+)(?:\s*/\s*\d+)?",
        output,
        re.MULTILINE | re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def parse_fraction(output, label):
    """Parse summaries such as 'Passed: 3/3' or 'Routing completeness: 20/20'."""
    match = re.search(
        rf"^\s*{re.escape(label)}:\s*(\d+)\s*/\s*(\d+)",
        output,
        re.MULTILINE | re.IGNORECASE,
    )

    if not match:
        return None

    passed, total = map(int, match.groups())

    return {
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total * 100, 2) if total else None,
    }


def parse_percentage(output, label):
    """Parse metrics such as 'Mean routing precision: 100.00%'."""
    match = re.search(
        rf"^\s*{re.escape(label)}:\s*(\d+(?:\.\d+)?)\s*%",
        output,
        re.MULTILINE | re.IGNORECASE,
    )

    return float(match.group(1)) if match else None


def run_evaluator(name, filename):
    script = EVALUATION_DIR / filename

    if not script.exists():
        return {
            "name": name,
            "script": filename,
            "status": "ERROR",
            "error": "Evaluator file not found.",
        }

    print(f"\n{'=' * 65}")
    print(f"Running: {name} ({filename})")
    print("=" * 65)

    try:
        process = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "script": filename,
            "status": "ERROR",
            "error": "Evaluator timed out after 15 minutes.",
        }

    output = process.stdout or ""
    errors = process.stderr or ""
    combined = output + "\n" + errors

    print(output)

    if errors:
        print("STDERR:")
        print(errors)

    blocked = parse_count(combined, "Blocked by Azure") or 0
    failed = parse_count(combined, "Failed")
    passed = parse_count(combined, "Passed")

    # Routing and retrieval metrics
    routing_completeness = parse_fraction(
        combined, "Routing completeness"
    )
    exact_match = parse_fraction(
        combined, "Exact-match accuracy"
    )
    routing_precision = parse_percentage(
        combined, "Mean routing precision"
    )
    routing_recall = parse_percentage(
        combined, "Mean routing recall"
    )
    source_hit_rate = parse_fraction(
        combined, "Source hit rate"
    )
    source_recall = parse_percentage(
        combined, "Mean source Recall@3"
    )

    # Answer quality metrics
    expected_sources = parse_fraction(
        combined, "Expected source cited"
    )
    valid_citations = parse_fraction(
        combined, "Valid citation IDs"
    )
    expected_keywords = parse_fraction(
        combined, "Expected keyword checks"
    )

    quality_metrics = [
        expected_sources,
        valid_citations,
        expected_keywords,
    ]

    routing_metrics = [
        routing_completeness,
        exact_match,
        routing_precision,
        routing_recall,
        source_hit_rate,
        source_recall,
    ]

    # Check whether the evaluator printed all expected metrics.
    if name == "routing_retrieval":
        recognized = all(
            metric is not None for metric in routing_metrics
        )

    elif name == "answer_quality":
        recognized = all(
            metric is not None for metric in quality_metrics
        )

    else:
        recognized = passed is not None and failed is not None

    # Check whether any fraction-based metric has failures.
    fraction_metrics = [
        routing_completeness,
        exact_match,
        source_hit_rate,
        expected_sources,
        valid_citations,
        expected_keywords,
    ]

    fraction_failure = any(
        metric is not None
        and metric["passed"] < metric["total"]
        for metric in fraction_metrics
    )

    # Determine the evaluator's status.
    if process.returncode != 0:
        status = "ERROR"

    elif blocked > 0:
        status = "PARTIAL_BLOCKED"

    elif failed is not None and failed > 0:
        status = "FAIL"

    elif fraction_failure:
        status = "FAIL"

    elif not recognized:
        status = "REVIEW"

    else:
        status = "PASS"

    return {
        "name": name,
        "script": filename,
        "status": status,
        "return_code": process.returncode,
        "passed": passed,
        "failed": failed,
        "blocked_by_azure": blocked,
        "routing_completeness": routing_completeness,
        "exact_match_accuracy": exact_match,
        "mean_routing_precision": routing_precision,
        "mean_routing_recall": routing_recall,
        "source_hit_rate": source_hit_rate,
        "mean_source_recall_at_3": source_recall,
        "expected_sources": expected_sources,
        "valid_citations": valid_citations,
        "expected_keywords": expected_keywords,
        "stdout": output,
        "stderr": errors,
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for name, filename in EVALUATORS:
        result = run_evaluator(name, filename)
        results.append(result)

    errors = sum(
        item["status"] == "ERROR" for item in results
    )
    failures = sum(
        item["status"] == "FAIL" for item in results
    )
    blocked = sum(
        item["status"] == "PARTIAL_BLOCKED" for item in results
    )
    review = sum(
        item["status"] == "REVIEW" for item in results
    )
    passed = sum(
        item["status"] == "PASS" for item in results
    )

    if errors or failures:
        overall_status = "FAIL"
    elif blocked or review:
        overall_status = "INCOMPLETE"
    else:
        overall_status = "PASS"

    timestamp_utc = datetime.now(timezone.utc)

    report = {
        "timestamp_utc": timestamp_utc.isoformat(),
        "overall_status": overall_status,
        "summary": {
            "evaluators": len(results),
            "passed": passed,
            "failed": failures,
            "errors": errors,
            "partially_blocked": blocked,
            "needs_review": review,
        },
        "results": results,
    }

    filename_timestamp = timestamp_utc.strftime(
        "%Y%m%d_%H%M%S"
    )
    report_path = REPORT_DIR / (
        f"regression_{filename_timestamp}.json"
    )

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n{'=' * 65}")
    print("REGRESSION SUITE SUMMARY")
    print("=" * 65)

    for item in results:
        print(f"{item['name']:<22} {item['status']}")

    print(f"\nOverall status: {overall_status}")
    print(f"Passed evaluators: {passed}/{len(results)}")
    print(f"Failed evaluators: {failures}")
    print(f"Execution errors: {errors}")
    print(f"Partially blocked: {blocked}")
    print(f"Needs review: {review}")
    print(f"Report saved to: {report_path.relative_to(ROOT)}")

    if overall_status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
