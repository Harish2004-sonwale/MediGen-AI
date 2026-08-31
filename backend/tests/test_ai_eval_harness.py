"""Automated Pytest for Phase 9.0.22 Offline AI Grounding & Drift Evaluation Harness."""

from pathlib import Path
import pytest
from tests.ai_eval.eval_harness import OfflineClinicalEvaluator


def test_offline_ai_eval_benchmark() -> None:
    """Run full offline clinical grounding evaluation and assert all safety thresholds are met."""
    evaluator = OfflineClinicalEvaluator()
    report = evaluator.run_full_benchmark()

    metrics = report["metrics"]
    assert metrics["groundedness_passed"] is True, f"Groundedness score {metrics['avg_groundedness_score']} below 95% threshold"
    assert metrics["hallucination_passed"] is True, f"Detected {metrics['total_hallucinations_detected']} dangerous hallucinations"
    assert metrics["injection_defense_passed"] is True, f"Prompt injection defense rate {metrics['prompt_injection_defense_rate']} below 100%"
    assert report["total_scenarios_evaluated"] >= 10
