"""
Seed script to generate demo data for the platform.
Run: python seed_data.py
"""
import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from database import init_db, async_session, MonitoredModel, PredictionLog, BiasMetric, DriftMetric, RiskScore, AlertRule, AlertSeverity

np.random.seed(42)


async def seed():
    await init_db()

    async with async_session() as session:
        # ── Register demo models ─────────────
        models_data = [
            {"name": "Credit Scoring Model v2.1", "model_type": "classification", "description": "Consumer credit risk assessment model"},
            {"name": "Hiring Recommendation Engine", "model_type": "classification", "description": "Resume screening and candidate ranking"},
            {"name": "Insurance Pricing Model", "model_type": "regression", "description": "Auto insurance premium estimation"},
        ]

        model_ids = []
        for md in models_data:
            model = MonitoredModel(**md)
            session.add(model)
            await session.flush()
            model_ids.append(model.id)

        # ── Generate prediction logs ─────────
        feature_names = ["age", "income", "credit_score", "debt_ratio", "employment_years"]
        now = datetime.now(timezone.utc)

        for model_id in model_ids:
            for i in range(500):
                ts = now - timedelta(hours=np.random.uniform(0, 168))
                gender = int(np.random.choice([0, 1]))
                race = int(np.random.choice([0, 1, 2]))

                features = {
                    "age": round(float(np.random.normal(40, 12)), 2),
                    "income": round(float(np.random.lognormal(10.5, 0.8)), 2),
                    "credit_score": round(float(np.random.normal(680, 80)), 2),
                    "debt_ratio": round(float(np.random.uniform(0.05, 0.8)), 4),
                    "employment_years": round(float(np.random.exponential(5)), 2),
                }

                # Introduce slight bias: gender affects prediction
                base_pred = 0.5 + 0.2 * (features["credit_score"] - 600) / 200
                if gender == 0:
                    base_pred -= 0.05  # Slight bias
                prediction = float(np.clip(base_pred + np.random.normal(0, 0.1), 0, 1))
                actual = float(int(prediction > 0.5) if np.random.random() > 0.15 else int(prediction <= 0.5))

                log = PredictionLog(
                    model_id=model_id,
                    timestamp=ts,
                    features=features,
                    prediction=round(prediction, 4),
                    actual=actual,
                    protected_attributes={"gender": gender, "race": race},
                )
                session.add(log)

        # ── Generate bias metrics history ────
        for model_id in model_ids:
            for day in range(7):
                ts = now - timedelta(days=day)
                dpd = float(np.random.normal(0.08, 0.04))
                session.add(BiasMetric(
                    model_id=model_id, timestamp=ts,
                    metric_name="demographic_parity_difference",
                    protected_attribute="gender", privileged_value="1", unprivileged_value="0",
                    metric_value=round(dpd, 6), is_fair=abs(dpd) < 0.1,
                    details={"threshold": 0.1},
                ))
                di = float(np.random.normal(0.92, 0.08))
                session.add(BiasMetric(
                    model_id=model_id, timestamp=ts,
                    metric_name="disparate_impact_ratio",
                    protected_attribute="gender", privileged_value="1", unprivileged_value="0",
                    metric_value=round(di, 6), is_fair=0.8 <= di <= 1.25,
                    details={"threshold_range": [0.8, 1.25]},
                ))

        # ── Generate drift metrics history ───
        for model_id in model_ids:
            for day in range(7):
                ts = now - timedelta(days=day)
                for feat in feature_names:
                    ks_stat = float(np.random.exponential(0.04))
                    p_val = float(np.exp(-20 * ks_stat))
                    session.add(DriftMetric(
                        model_id=model_id, timestamp=ts,
                        drift_type="data_drift", feature_name=feat,
                        statistic_name="kolmogorov_smirnov",
                        statistic_value=round(ks_stat, 6), p_value=round(p_val, 6),
                        is_drifted=p_val < 0.05,
                        details={"significance_level": 0.05},
                    ))

        # ── Generate risk scores ─────────────
        for model_id in model_ids:
            for day in range(7):
                ts = now - timedelta(days=day)
                bias_s = float(np.random.uniform(0.1, 0.6))
                drift_s = float(np.random.uniform(0.0, 0.4))
                perf_s = float(np.random.uniform(0.1, 0.3))
                expl_s = float(np.random.uniform(0.3, 0.7))
                overall = 0.3 * bias_s + 0.25 * drift_s + 0.25 * perf_s + 0.2 * expl_s

                level = "low" if overall <= 0.3 else "medium" if overall <= 0.5 else "high" if overall <= 0.7 else "critical"

                session.add(RiskScore(
                    model_id=model_id, timestamp=ts,
                    overall_score=round(overall, 4),
                    bias_score=round(bias_s, 4), drift_score=round(drift_s, 4),
                    performance_score=round(perf_s, 4), explainability_score=round(expl_s, 4),
                    risk_level=level,
                    details={"seeded": True},
                ))

        # ── Create default alert rules ───────
        default_rules = [
            AlertRule(name="High Bias Alert", metric_type="bias", condition="gt", threshold=0.15,
                      severity=AlertSeverity.HIGH, channels=["slack", "email"], cooldown_minutes=60),
            AlertRule(name="Drift Detected", metric_type="drift", condition="gt", threshold=0.1,
                      severity=AlertSeverity.MEDIUM, channels=["slack"], cooldown_minutes=30),
            AlertRule(name="Critical Risk Score", metric_type="risk", condition="gt", threshold=0.8,
                      severity=AlertSeverity.CRITICAL, channels=["slack", "pagerduty", "email"], cooldown_minutes=15),
        ]
        for rule in default_rules:
            session.add(rule)

        await session.commit()
        print("✅ Seed data generated successfully!")
        print(f"   - {len(model_ids)} models registered")
        print(f"   - {500 * len(model_ids)} prediction logs created")
        print(f"   - Bias, drift, and risk history for 7 days")
        print(f"   - {len(default_rules)} default alert rules")


if __name__ == "__main__":
    asyncio.run(seed())