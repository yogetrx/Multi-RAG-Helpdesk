
from helpdesk.retrieval.fusion import fuse_results


def test_fusion_removes_duplicate_chunks():
    results = [
        {"text": "Check VPN connectivity", "score": 0.7,
         "source": "vpn.txt"},
        {"text": "  CHECK VPN CONNECTIVITY  ", "score": 0.9,
         "source": "vpn_copy.txt"},
    ]

    fused = fuse_results(results)

    assert len(fused) == 1
    assert fused[0]["score"] == 0.9


def test_fusion_ranks_and_limits_results():
    results = [
        {"text": "A", "score": 0.4},
        {"text": "B", "score": 0.9},
        {"text": "C", "score": 0.7},
    ]

    fused = fuse_results(results, top_k=2)

    assert [item["text"] for item in fused] == ["B", "C"]


def test_fusion_handles_empty_results():
    assert fuse_results([]) == []
