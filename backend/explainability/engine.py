import numpy as np
import shap
import lime.lime_tabular
from typing import Dict, Any, List, Optional
from sklearn.ensemble import GradientBoostingClassifier
import logging
import pickle

logger = logging.getLogger(__name__)


class ExplainabilityEngine:
    """
    Model explainability using SHAP, LIME, and custom feature importance.
    Operates with a surrogate model or a provided model artifact.
    """

    def __init__(self):
        self._surrogate_models: Dict[int, Any] = {}
        self._training_data: Dict[int, np.ndarray] = {}
        self._feature_names: Dict[int, List[str]] = {}

    def register_surrogate(
        self,
        model_id: int,
        model: Any,
        training_data: np.ndarray,
        feature_names: List[str],
    ):
        """Register a model and its training data for explanations."""
        self._surrogate_models[model_id] = model
        self._training_data[model_id] = training_data
        self._feature_names[model_id] = feature_names

    def train_surrogate(
        self,
        model_id: int,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
    ):
        """Train a surrogate model from prediction logs."""
        surrogate = GradientBoostingClassifier(
            n_estimators=100, max_depth=4, random_state=42
        )
        surrogate.fit(X, y)
        self.register_surrogate(model_id, surrogate, X, feature_names)
        logger.info(f"Surrogate model trained for model_id={model_id}")
        return surrogate

    def explain_shap(
        self, model_id: int, instance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate SHAP explanations for a single instance."""
        if model_id not in self._surrogate_models:
            return self._fallback_explanation(instance, "shap")

        model = self._surrogate_models[model_id]
        bg_data = self._training_data[model_id]
        feature_names = self._feature_names[model_id]

        instance_array = np.array([[instance.get(f, 0.0) for f in feature_names]])

        # Use KernelExplainer for model-agnostic explanations
        bg_sample = shap.sample(bg_data, min(100, len(bg_data)))
        explainer = shap.KernelExplainer(model.predict_proba, bg_sample)
        shap_values = explainer.shap_values(instance_array)

        # Get SHAP values for positive class
        if isinstance(shap_values, list):
            sv = shap_values[1][0]  # Class 1
        else:
            sv = shap_values[0]

        feature_importances = {
            name: round(float(val), 6)
            for name, val in zip(feature_names, sv)
        }

        # Sort by absolute importance
        feature_importances = dict(
            sorted(feature_importances.items(), key=lambda x: abs(x[1]), reverse=True)
        )

        return {
            "method": "shap",
            "feature_importances": feature_importances,
            "explanation_details": {
                "base_value": float(explainer.expected_value[1]) if isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value),
                "prediction_contribution": sum(sv),
                "top_positive_features": [
                    k for k, v in feature_importances.items() if v > 0
                ][:5],
                "top_negative_features": [
                    k for k, v in feature_importances.items() if v < 0
                ][:5],
            }
        }

    def explain_lime(
        self, model_id: int, instance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate LIME explanations for a single instance."""
        if model_id not in self._surrogate_models:
            return self._fallback_explanation(instance, "lime")

        model = self._surrogate_models[model_id]
        training_data = self._training_data[model_id]
        feature_names = self._feature_names[model_id]

        instance_array = np.array([instance.get(f, 0.0) for f in feature_names])

        explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data,
            feature_names=feature_names,
            class_names=["negative", "positive"],
            mode="classification",
        )

        explanation = explainer.explain_instance(
            instance_array,
            model.predict_proba,
            num_features=len(feature_names),
        )

        feature_importances = {
            name: round(float(weight), 6)
            for name, weight in explanation.as_list()
        }

        return {
            "method": "lime",
            "feature_importances": feature_importances,
            "explanation_details": {
                "intercept": float(explanation.intercept[1]),
                "prediction_local": float(explanation.local_pred[0]) if hasattr(explanation, 'local_pred') else None,
                "r_squared": float(explanation.score) if hasattr(explanation, 'score') else None,
            }
        }

    @staticmethod
    def _fallback_explanation(instance: Dict[str, float], method: str) -> Dict[str, Any]:
        """Provide a permutation-based pseudo-explanation when no model is registered."""
        values = list(instance.values())
        if not values:
            return {"method": method, "feature_importances": {}, "explanation_details": {"note": "empty instance"}}

        total = sum(abs(v) for v in values) or 1.0
        feature_importances = {
            k: round(v / total, 6) for k, v in instance.items()
        }
        return {
            "method": method,
            "feature_importances": feature_importances,
            "explanation_details": {
                "note": "Fallback: normalized feature magnitudes (no surrogate model registered)",
            }
        }


# Singleton instance
explainability_engine = ExplainabilityEngine()