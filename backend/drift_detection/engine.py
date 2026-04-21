import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    feature_name: str
    drift_type: str
    statistic_name: str
    statistic_value: float
    p_value: Optional[float]
    is_drifted: bool
    details: Dict[str, Any]


class DriftDetectionEngine:
    """
    Drift detection engine using statistical tests, PSI, and Evidently-style analysis.
    """

    def __init__(self, significance_level: float = 0.05, psi_threshold: float = 0.2):
        self.significance_level = significance_level
        self.psi_threshold = psi_threshold

    def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        features: Optional[List[str]] = None,
    ) -> List[DriftResult]:
        """Run all drift detection methods on the given data."""
        if features is None:
            features = [c for c in reference_data.columns if c not in ("prediction", "actual", "timestamp")]

        results = []
        for feature in features:
            if feature not in reference_data.columns or feature not in current_data.columns:
                continue

            ref = reference_data[feature].dropna().values
            cur = current_data[feature].dropna().values

            if len(ref) < 10 or len(cur) < 10:
                continue

            # ── KS Test ──────────────────────────
            results.append(self._ks_test(feature, ref, cur))

            # ── PSI ──────────────────────────────
            results.append(self._psi(feature, ref, cur))

            # ── Wasserstein Distance ─────────────
            results.append(self._wasserstein(feature, ref, cur))

            # ── Chi-squared (for categorical-like) ─
            if len(np.unique(ref)) < 20:
                results.append(self._chi_squared(feature, ref, cur))

            # ── Mean Shift Test ──────────────────
            results.append(self._mean_shift_test(feature, ref, cur))

        return results

    def _ks_test(self, feature: str, ref: np.ndarray, cur: np.ndarray) -> DriftResult:
        stat, p_value = stats.ks_2samp(ref, cur)
        return DriftResult(
            feature_name=feature,
            drift_type="data_drift",
            statistic_name="kolmogorov_smirnov",
            statistic_value=round(float(stat), 6),
            p_value=round(float(p_value), 6),
            is_drifted=p_value < self.significance_level,
            details={
                "description": "Two-sample KS test",
                "significance_level": self.significance_level,
            }
        )

    def _psi(self, feature: str, ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> DriftResult:
        """Population Stability Index."""
        breakpoints = np.histogram_bin_edges(ref, bins=bins)

        ref_counts = np.histogram(ref, bins=breakpoints)[0] + 1  # Laplace smoothing
        cur_counts = np.histogram(cur, bins=breakpoints)[0] + 1

        ref_pct = ref_counts / ref_counts.sum()
        cur_pct = cur_counts / cur_counts.sum()

        psi_value = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

        return DriftResult(
            feature_name=feature,
            drift_type="data_drift",
            statistic_name="population_stability_index",
            statistic_value=round(psi_value, 6),
            p_value=None,
            is_drifted=psi_value > self.psi_threshold,
            details={
                "description": "Population Stability Index",
                "threshold": self.psi_threshold,
                "interpretation": (
                    "no_drift" if psi_value < 0.1
                    else "moderate_drift" if psi_value < 0.2
                    else "significant_drift"
                ),
            }
        )

    def _wasserstein(self, feature: str, ref: np.ndarray, cur: np.ndarray) -> DriftResult:
        distance = float(stats.wasserstein_distance(ref, cur))
        # Normalize by reference std
        ref_std = float(np.std(ref)) or 1.0
        normalized = distance / ref_std

        return DriftResult(
            feature_name=feature,
            drift_type="data_drift",
            statistic_name="wasserstein_distance",
            statistic_value=round(distance, 6),
            p_value=None,
            is_drifted=normalized > 0.1,
            details={
                "normalized_distance": round(normalized, 6),
                "reference_std": round(ref_std, 6),
            }
        )

    def _chi_squared(self, feature: str, ref: np.ndarray, cur: np.ndarray) -> DriftResult:
        categories = np.union1d(np.unique(ref), np.unique(cur))
        ref_counts = np.array([np.sum(ref == c) for c in categories]) + 1
        cur_counts = np.array([np.sum(cur == c) for c in categories]) + 1

        # Scale reference to match current sample size
        ref_expected = ref_counts * (cur_counts.sum() / ref_counts.sum())
        stat, p_value = stats.chisquare(cur_counts, f_exp=ref_expected)

        return DriftResult(
            feature_name=feature,
            drift_type="data_drift",
            statistic_name="chi_squared",
            statistic_value=round(float(stat), 6),
            p_value=round(float(p_value), 6),
            is_drifted=p_value < self.significance_level,
            details={"description": "Chi-squared test for categorical drift"}
        )

    def _mean_shift_test(self, feature: str, ref: np.ndarray, cur: np.ndarray) -> DriftResult:
        stat, p_value = stats.mannwhitneyu(ref, cur, alternative="two-sided")
        return DriftResult(
            feature_name=feature,
            drift_type="data_drift",
            statistic_name="mann_whitney_u",
            statistic_value=round(float(stat), 6),
            p_value=round(float(p_value), 6),
            is_drifted=p_value < self.significance_level,
            details={"description": "Mann-Whitney U test for distribution shift"}
        )

    def detect_prediction_drift(
        self,
        ref_predictions: np.ndarray,
        cur_predictions: np.ndarray,
    ) -> List[DriftResult]:
        """Detect drift in model predictions specifically."""
        results = []

        # KS test on predictions
        stat, p_value = stats.ks_2samp(ref_predictions, cur_predictions)
        results.append(DriftResult(
            feature_name="prediction",
            drift_type="prediction_drift",
            statistic_name="kolmogorov_smirnov",
            statistic_value=round(float(stat), 6),
            p_value=round(float(p_value), 6),
            is_drifted=p_value < self.significance_level,
            details={"description": "KS test on prediction distribution"}
        ))

        # PSI on predictions
        psi_result = self._psi("prediction", ref_predictions, cur_predictions)
        psi_result.drift_type = "prediction_drift"
        results.append(psi_result)

        return results


# Singleton
drift_engine = DriftDetectionEngine()