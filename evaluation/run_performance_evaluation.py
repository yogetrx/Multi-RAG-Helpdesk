
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "evaluation" / "reports"

API_URL = "http://127.0.0.1:8000/ask"
HEALTH_URL = "http://127.0.0.1:8000/health"

TOP_K = 3
WARMUP_REQUESTS = 1

# Reference prices in USD per million tokens.
# Verify these against your actual Azure deployment pricing.
INPUT_PRICE_PER_MILLION = 2.50
OUTPUT_PRICE_PER_MILLION = 15.00

TEST_QUESTIONS = [
    "How do I troubleshoot VPN error 809?",
    "How do I request Azure access?",
    "What is the IT support procedure?",
    "What should I do if my VPN cannot connect?",
    "How do I get access to a restricted resource?",
]


def percentile(values, percentile_value):
    """Calculate a percentile without external dependencies."""
    ordered = sorted(values)

    if not ordered:
        return None

    index = round((percentile_value / 100) * (len(ordered) - 1))
    return ordered[index]


def send_question(question):
    """Send a question to the API and collect performance metrics."""
    payload = {
        "question": question,
        "top_k": TOP_K,
    }

    start = time.perf_counter()

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=120,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        try:
            body = response.json()
        except ValueError:
            body = {"raw_response": response.text}

        token_usage = body.get("token_usage")

        if isinstance(token_usage, dict):
            input_tokens = token_usage.get("input_tokens")
            output_tokens = token_usage.get("output_tokens")
            total_tokens = token_usage.get("total_tokens")

            valid_usage = all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
                for value in (
                    input_tokens,
                    output_tokens,
                    total_tokens,
                )
            )

            if not valid_usage:
                token_usage = None
        else:
            token_usage = None

        return {
            "question": question,
            "http_status": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "success": response.ok,
            "grounded": body.get("grounded"),
            "token_usage": token_usage,
            "response": body,
            "error": None,
        }

    except requests.RequestException as exc:
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "question": question,
            "http_status": None,
            "latency_ms": round(latency_ms, 2),
            "success": False,
            "grounded": None,
            "token_usage": None,
            "response": None,
            "error": str(exc),
        }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("MULTI-RAG HELPDESK PERFORMANCE EVALUATION")
    print("=" * 65)
    print(f"API: {API_URL}")
    print(f"Questions: {len(TEST_QUESTIONS)}")
    print(f"Top K: {TOP_K}")

    # Check API health.
    try:
        health_response = requests.get(
            HEALTH_URL,
            timeout=30,
        )
        health_response.raise_for_status()
        print("\nHealth check: PASS")

    except requests.RequestException as exc:
        print("\nHealth check: FAIL")
        print(f"Reason: {exc}")
        print("Check that the FastAPI server is running.")
        raise SystemExit(1)

    # Warm-up requests are excluded from measured results.
    print("\nRunning warm-up request...")

    for _ in range(WARMUP_REQUESTS):
        warmup = send_question(TEST_QUESTIONS[0])

        if not warmup["success"]:
            print("Warm-up request failed.")
            print(f"HTTP status: {warmup['http_status']}")
            print(f"Error: {warmup['error']}")
            print(f"Response: {warmup['response']}")
            raise SystemExit(1)

    results = []

    print("\nRunning performance tests...")

    for index, question in enumerate(TEST_QUESTIONS, start=1):
        result = send_question(question)
        results.append(result)

        status = "PASS" if result["success"] else "FAIL"

        print(
            f"[{index}/{len(TEST_QUESTIONS)}] {status} | "
            f"{result['latency_ms']:.2f} ms | "
            f"HTTP {result['http_status']} | "
            f"{question}"
        )

        usage = result["token_usage"]

        if usage:
            print(
                f"    Tokens: input={usage['input_tokens']}, "
                f"output={usage['output_tokens']}, "
                f"total={usage['total_tokens']}"
            )
        else:
            print("    Token usage: unavailable in API response")

    successful = [
        item for item in results if item["success"]
    ]

    latencies = [
        item["latency_ms"] for item in successful
    ]

    # Aggregate token usage from successful requests.
    usage_records = [
        item["token_usage"]
        for item in successful
        if item["token_usage"] is not None
    ]

    total_input_tokens = sum(
        item["input_tokens"] for item in usage_records
    )

    total_output_tokens = sum(
        item["output_tokens"] for item in usage_records
    )

    total_tokens = sum(
        item["total_tokens"] for item in usage_records
    )

    # Latency statistics.
    latency_summary = None

    if latencies:
        latency_summary = {
            "mean_ms": round(statistics.mean(latencies), 2),
            "median_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(percentile(latencies, 95), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
        }

    # Token usage statistics.
    token_summary = {
        "status": (
            "MEASURED" if usage_records else "NOT_MEASURED"
        ),
        "requests_with_usage": len(usage_records),
        "successful_requests": len(successful),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "average_input_tokens": (
            round(total_input_tokens / len(usage_records), 2)
            if usage_records else None
        ),
        "average_output_tokens": (
            round(total_output_tokens / len(usage_records), 2)
            if usage_records else None
        ),
        "average_total_tokens": (
            round(total_tokens / len(usage_records), 2)
            if usage_records else None
        ),
    }

    # Estimated model cost.
    estimated_input_cost = (
        total_input_tokens / 1_000_000
    ) * INPUT_PRICE_PER_MILLION

    estimated_output_cost = (
        total_output_tokens / 1_000_000
    ) * OUTPUT_PRICE_PER_MILLION

    estimated_total_cost = (
        estimated_input_cost + estimated_output_cost
    )

    cost_summary = {
        "status": (
            "ESTIMATED" if usage_records else "NOT_CALCULATED"
        ),
        "currency": "USD",
        "pricing_model": "GPT-5.4 reference rates",
        "input_price_per_million_tokens": INPUT_PRICE_PER_MILLION,
        "output_price_per_million_tokens": OUTPUT_PRICE_PER_MILLION,
        "input_cost_usd": (
            round(estimated_input_cost, 8)
            if usage_records else None
        ),
        "output_cost_usd": (
            round(estimated_output_cost, 8)
            if usage_records else None
        ),
        "total_cost_usd": (
            round(estimated_total_cost, 8)
            if usage_records else None
        ),
        "average_cost_per_measured_request_usd": (
            round(estimated_total_cost / len(usage_records), 8)
            if usage_records else None
        ),
        "note": (
            "Estimated using reference rates. Actual Azure charges may "
            "differ by deployment type, region, cached tokens, and "
            "applicable pricing. Only reported generation tokens are "
            "included; other model calls may incur additional costs."
        ),
    }

    # Build report.
    timestamp_utc = datetime.now(timezone.utc)

    report = {
        "timestamp_utc": timestamp_utc.isoformat(),
        "api_url": API_URL,
        "top_k": TOP_K,
        "warmup_requests": WARMUP_REQUESTS,
        "total_questions": len(TEST_QUESTIONS),
        "successful_requests": len(successful),
        "failed_requests": len(results) - len(successful),
        "latency": latency_summary,
        "token_usage": token_summary,
        "estimated_cost": cost_summary,
        "results": results,
    }

    filename_timestamp = timestamp_utc.strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = REPORT_DIR / (
        f"performance_{filename_timestamp}.json"
    )

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Print summary.
    print("\n" + "=" * 65)
    print("PERFORMANCE SUMMARY")
    print("=" * 65)

    print(
        f"Successful requests: {len(successful)}/{len(results)}"
    )
    print(f"Failed requests: {len(results) - len(successful)}")

    if latency_summary:
        print(f"Mean latency: {latency_summary['mean_ms']} ms")
        print(f"Median latency: {latency_summary['median_ms']} ms")
        print(f"P95 latency: {latency_summary['p95_ms']} ms")
        print(f"Minimum latency: {latency_summary['min_ms']} ms")
        print(f"Maximum latency: {latency_summary['max_ms']} ms")

    print("\nTOKEN USAGE")
    print(
        f"Requests with token usage: "
        f"{len(usage_records)}/{len(successful)}"
    )
    print(f"Total input tokens: {total_input_tokens}")
    print(f"Total output tokens: {total_output_tokens}")
    print(f"Total tokens: {total_tokens}")

    if usage_records:
        print(
            "Average tokens per measured request: "
            f"{token_summary['average_total_tokens']}"
        )

    print("\nESTIMATED COST")
    if usage_records:
        print(f"Input cost: ${estimated_input_cost:.8f}")
        print(f"Output cost: ${estimated_output_cost:.8f}")
        print(f"Total cost: ${estimated_total_cost:.8f}")
        print(
            "Average cost per measured request: "
            f"${estimated_total_cost / len(usage_records):.8f}"
        )
    else:
        print("Cost not calculated because token usage is unavailable.")

    print(f"\nReport saved to: {report_path.relative_to(ROOT)}")

    if len(successful) != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
