import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from database import init_db, async_session, MonitoredModel, PredictionLog, AlertRule, AlertSeverity

print("🚀 Script loaded")


async def seed():
    print("🚀 Seed started")

    await init_db()

    async with async_session() as session:

        def now():
            return datetime.now(timezone.utc).replace(tzinfo=None)

        # ── Models ───────────────────────────
        models_data = [
            {"name": "Credit Scoring Model v2.1", "model_type": "classification", "description": "Consumer credit risk assessment model"},
            {"name": "Hiring Recommendation Engine", "model_type": "classification", "description": "Resume screening and candidate ranking"},
            {"name": "Insurance Pricing Model", "model_type": "regression", "description": "Auto insurance premium estimation"},
        ]

        model_ids = []

        for md in models_data:
            result = await session.execute(
                select(MonitoredModel).where(MonitoredModel.name == md["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                model_ids.append(existing.id)
            else:
                model = MonitoredModel(**md, created_at=now())
                session.add(model)
                await session.flush()
                model_ids.append(model.id)

        await session.commit()
        print("Models:", model_ids)

        # ── Prediction Logs ───────────────────
        current_time = now()

        for model_id in model_ids:
            for _ in range(1000):

                ts = current_time - timedelta(minutes=np.random.uniform(0, 10080))

                # Features
                features = {
                    "age": max(18, int(np.random.normal(35, 10))),
                    "income": max(10000, float(np.random.normal(50000, 15000))),
                    "credit_score": max(300, min(850, int(np.random.normal(650, 80))))
                }

                # Protected attributes
                gender = int(np.random.choice([0, 1]))
                race = int(np.random.choice([0, 1, 2]))

                protected_attributes = {
                    "gender": gender,
                    "race": race
                }

                # Score logic
                score = (
                    0.3 * (features["credit_score"] / 850) +
                    0.3 * (features["income"] / 100000) -
                    0.2 * (features["age"] / 100)
                )

                if gender == 0:
                    score -= 0.05

                prediction = float(np.clip(score + np.random.normal(0, 0.1), 0, 1))
                actual = int(prediction > 0.5 if np.random.rand() > 0.1 else prediction <= 0.5)

                session.add(PredictionLog(
                    model_id=model_id,
                    timestamp=ts,
                    features=features,
                    prediction=prediction,
                    actual=actual,
                    protected_attributes=protected_attributes
                ))

        await session.commit()

        # ── Alert Rules ───────────────────────
        rules = [
            ("High Bias Alert", "bias", 0.15, AlertSeverity.HIGH),
            ("Drift Detected", "drift", 0.1, AlertSeverity.MEDIUM),
            ("Critical Risk Score", "risk", 0.8, AlertSeverity.CRITICAL),
        ]

        for name, metric, threshold, severity in rules:
            result = await session.execute(
                select(AlertRule).where(AlertRule.name == name)
            )
            if not result.scalar_one_or_none():
                session.add(AlertRule(
                    name=name,
                    metric_type=metric,
                    condition="gt",
                    threshold=threshold,
                    severity=severity,
                    channels=["slack"],
                    cooldown_minutes=30,
                    created_at=now()
                ))

        await session.commit()

        print("✅ Seed complete")
        print(f"Models: {len(model_ids)}")
        print(f"Logs: {1000 * len(model_ids)}")


if __name__ == "__main__":
    asyncio.run(seed())
