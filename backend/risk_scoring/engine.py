import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    overall_score: float
    bias_score: float
    drift_score: float
    performance_score: float
    explainability_score: float
    risk_level: str
    details: Dict[str, Any]


class RiskScoringEngine:
    """
    Composite risk scoring engine.
    Produces a 0-1 score across dimensions:
      - Bias risk
      - Drift risk
      - Performance risk
      - Explainability risk

    Weights are configurable. Higher score = higher risk.
    """

    DEFAULT_WEIGHTS = {
        "bias": 0.30,
        "drift": 0.25,
        "performance": 0.25,
        "explainability": 0.20,
    }

    RISK_LEVELS = [
        (0.3, "low"),
        (0.5, "medium"),
        (0.7, "high"),
        (1.0, "critical"),
    ]

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def compute_risk(
        self,
        bias_metrics: List[Dict[str, Any]],
        drift_metrics: List[Dict[str, Any]],
        performance_metrics: Optional[Dict[str, float]] = None,
        explainability_metrics: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessment:
        """Compute composite risk score from all monitoring dimensions."""

        bias_score = self._compute_bias_risk(bias_metrics)
        drift_score = self._compute_drift_risk(drift_metrics)
        performance_score = self._compute_performance_risk(performance_metrics or {})
        explainability_score = self._compute_explainability_risk(explainability_metrics or {})

        overall_score = (
            self.weights["bias"] * bias_score
            + self.weights["drift"] * drift_score
            + self.weights["performance"] * performance_score
            + self.weights["explainability"] * explainability_score
        )

        overall_score = round(min(max(overall_score, 0.0), 1.0), 4)
        risk_level = self._get_risk_level(overall_score)

        return RiskAssessment(
            overall_score=overall_score,
            bias_score=round(bias_score, 4),
            drift_score=round(drift_score, 4),
            performance_score=round(performance_score, 4),
            explainability_score=round(explainability_score, 4),
            risk_level=risk_level,
            details={
                "weights": self.weights,
                "component_contributions": {
                    "bias": round(self.weights["bias"] * bias_score, 4),
                    "drift": round(self.weights["drift"] * drift_score, 4),
                    "performance": round(self.weights["performance"] * performance_score, 4),
                    "explainability": round(self.weights["explainability"] * explainability_score, 4),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _compute_bias_risk(self, metrics: List[Dict[str, Any]]) -> float:
        """Convert bias metrics into a 0-1 risk score."""
        if not metrics:
            return 0.5  # Unknown = medium risk

        unfair_count = sum(1 for m in metrics if not m.get("is_fair", True))
        total = len(metrics)

        # Base risk from unfairness ratio
        base_risk = unfair_count / total if total > 0 else 0.0

        # Amplify risk based on severity of violations
        severity_bonus = 0.0
        for m in metrics:
            if not m.get("is_fair", True):
                value = abs(m.get("metric_value", 0))
                if m.get("metric_name") == "disparate_impact_ratio":
                    # Further from 1.0 = worse
                    severity_bonus += min(abs(1.0 - value), 0.5) * 0.3
                else:
                    severity_bonus += min(value, 0.5) * 0.3

        return min(base_risk + severity_bonus, 1.0)

    def _compute_drift_risk(self, metrics: List[Dict[str, Any]]) -> float:
        """Convert drift metrics into a 0-1 risk score."""
        if not metrics:
            return 0.0

        drifted_count = sum(1 for m in metrics if m.get("is_drifted", False))
        total = len(metrics)

        base_risk = drifted_count / total if total > 0 else 0.0

        # Weight by severity of drift
        severity_factors = []
        for m in metrics:
            if m.get("is_drifted"):
                p_val = m.get("p_value")
                if p_val is not None and p_val < 0.001:
                    severity_factors.append(0.3)
                elif p_val is not None and p_val < 0.01:
                    severity_factors.append(0.15)
                else:
                    severity_factors.append(0.05)

        return min(base_risk + sum(severity_factors), 1.0)

    def _compute_performance_risk(self, metrics: Dict[str, float]) -> float:
        """Convert performance metrics into a 0-1 risk score."""
        if not metrics:
            return 0.3  # Unknown = slight risk

        risk_factors = []

        accuracy = metrics.get("accuracy", 0.9)
        risk_factors.append(max(0, 1.0 - accuracy))

        precision = metrics.get("precision", 0.9)
        risk_factors.append(max(0, 1.0 - precision) * 0.5)

        recall = metrics.get("recall", 0.9)
        risk_factors.append(max(0, 1.0 - recall) * 0.5)

        return min(sum(risk_factors) / len(risk_factors) * 2, 1.0) if risk_factors else 0.3

    def _compute_explainability_risk(self, metrics: Dict[str, Any]) -> float:
        """Assess explainability risk (higher if explanations are unstable/unavailable)."""
        if not metrics:
            return 0.6  # No explanations = elevated risk

        stability = metrics.get("explanation_stability", 0.8)
        coverage = metrics.get("feature_coverage", 1.0)
        consistency = metrics.get("consistency_score", 0.8)

        risk = 1.0 - (0.4 * stability + 0.3 * coverage + 0.3 * consistency)
        return max(min(risk, 1.0), 0.0)

    def _get_risk_level(self, score: float) -> str:
        for threshold, level in self.RISK_LEVELS:
            if score <= threshold:
                return level
        return "critical"


# Singleton
risk_engine = RiskScoringEngine()