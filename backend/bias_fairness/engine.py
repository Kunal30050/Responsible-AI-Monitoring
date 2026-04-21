import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from fairlearn.metrics import (
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
)
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class BiasFairnessEngine:
    """
    Bias and fairness analysis engine using Fairlearn and AIF360-style metrics.
    Supports: Demographic Parity, Equalized Odds, Disparate Impact, Statistical Parity.
    """

    @staticmethod
    def compute_all_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sensitive_features: np.ndarray,
        privileged_value: Any,
        unprivileged_value: Any,
    ) -> List[Dict[str, Any]]:
        results = []

        # Filter to only privileged/unprivileged groups
        mask = np.isin(sensitive_features, [privileged_value, unprivileged_value])
        y_true_f = y_true[mask]
        y_pred_f = y_pred[mask]
        sf_f = sensitive_features[mask]

        # ── 1. Demographic Parity Difference ─────
        try:
            dpd = demographic_parity_difference(
                y_true_f, y_pred_f, sensitive_features=sf_f
            )
            results.append({
                "metric_name": "demographic_parity_difference",
                "metric_value": round(float(dpd), 6),
                "is_fair": abs(dpd) < 0.1,
                "details": {
                    "description": "Difference in positive prediction rates between groups",
                    "threshold": 0.1,
                    "interpretation": "fair" if abs(dpd) < 0.1 else "unfair",
                }
            })
        except Exception as e:
            logger.warning(f"DPD computation failed: {e}")

        # ── 2. Demographic Parity Ratio (Disparate Impact) ──
        try:
            dpr = demographic_parity_ratio(
                y_true_f, y_pred_f, sensitive_features=sf_f
            )
            results.append({
                "metric_name": "disparate_impact_ratio",
                "metric_value": round(float(dpr), 6),
                "is_fair": 0.8 <= dpr <= 1.25,
                "details": {
                    "description": "Ratio of positive prediction rates (4/5ths rule)",
                    "threshold_range": [0.8, 1.25],
                    "interpretation": "fair" if 0.8 <= dpr <= 1.25 else "unfair",
                }
            })
        except Exception as e:
            logger.warning(f"DPR computation failed: {e}")

        # ── 3. Equalized Odds Difference ─────────
        try:
            eod = equalized_odds_difference(
                y_true_f, y_pred_f, sensitive_features=sf_f
            )
            results.append({
                "metric_name": "equalized_odds_difference",
                "metric_value": round(float(eod), 6),
                "is_fair": abs(eod) < 0.1,
                "details": {
                    "description": "Max difference in TPR and FPR across groups",
                    "threshold": 0.1,
                    "interpretation": "fair" if abs(eod) < 0.1 else "unfair",
                }
            })
        except Exception as e:
            logger.warning(f"EOD computation failed: {e}")

        # ── 4. Statistical Parity (custom) ───────
        try:
            priv_mask = sf_f == privileged_value
            unpriv_mask = sf_f == unprivileged_value

            priv_rate = y_pred_f[priv_mask].mean() if priv_mask.sum() > 0 else 0
            unpriv_rate = y_pred_f[unpriv_mask].mean() if unpriv_mask.sum() > 0 else 0
            sp_diff = priv_rate - unpriv_rate

            results.append({
                "metric_name": "statistical_parity_difference",
                "metric_value": round(float(sp_diff), 6),
                "is_fair": abs(sp_diff) < 0.1,
                "details": {
                    "privileged_positive_rate": round(float(priv_rate), 4),
                    "unprivileged_positive_rate": round(float(unpriv_rate), 4),
                    "description": "Difference in positive outcome rates",
                }
            })
        except Exception as e:
            logger.warning(f"Statistical parity failed: {e}")

        # ── 5. Group-level accuracy ──────────────
        try:
            priv_acc = (y_true_f[priv_mask] == y_pred_f[priv_mask]).mean() if priv_mask.sum() > 0 else 0
            unpriv_acc = (y_true_f[unpriv_mask] == y_pred_f[unpriv_mask]).mean() if unpriv_mask.sum() > 0 else 0

            results.append({
                "metric_name": "accuracy_parity",
                "metric_value": round(float(priv_acc - unpriv_acc), 6),
                "is_fair": abs(priv_acc - unpriv_acc) < 0.05,
                "details": {
                    "privileged_accuracy": round(float(priv_acc), 4),
                    "unprivileged_accuracy": round(float(unpriv_acc), 4),
                }
            })
        except Exception as e:
            logger.warning(f"Accuracy parity failed: {e}")

        return results

    @staticmethod
    def compute_aif360_metrics(
        df: pd.DataFrame,
        label_col: str,
        pred_col: str,
        protected_col: str,
        privileged_value: Any,
        unprivileged_value: Any,
    ) -> List[Dict[str, Any]]:
        """Extended AIF360-style metrics using direct computation."""
        results = []

        priv = df[df[protected_col] == privileged_value]
        unpriv = df[df[protected_col] == unprivileged_value]

        # Theil Index (Generalized Entropy with alpha=1)
        try:
            y = df[pred_col].values.astype(float)
            mu = y.mean()
            if mu > 0:
                theil = float(np.mean((y / mu) * np.log(y / mu + 1e-10)))
                results.append({
                    "metric_name": "theil_index",
                    "metric_value": round(theil, 6),
                    "is_fair": theil < 0.1,
                    "details": {"description": "Generalized entropy index (individual fairness)"}
                })
        except Exception as e:
            logger.warning(f"Theil index failed: {e}")

        # Between-group generalized entropy
        try:
            if len(priv) > 0 and len(unpriv) > 0:
                priv_mean = priv[pred_col].mean()
                unpriv_mean = unpriv[pred_col].mean()
                overall_mean = df[pred_col].mean()

                if overall_mean > 0:
                    bge = (
                        (len(priv) / len(df)) * ((priv_mean / overall_mean) * np.log(priv_mean / overall_mean + 1e-10))
                        + (len(unpriv) / len(df)) * ((unpriv_mean / overall_mean) * np.log(unpriv_mean / overall_mean + 1e-10))
                    )
                    results.append({
                        "metric_name": "between_group_entropy",
                        "metric_value": round(float(bge), 6),
                        "is_fair": abs(bge) < 0.05,
                        "details": {"description": "Between-group generalized entropy index"}
                    })
        except Exception as e:
            logger.warning(f"BGE failed: {e}")

        return results