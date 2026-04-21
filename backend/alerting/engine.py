import httpx
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
import aiosmtplib

from config import get_settings
from database import async_session, AlertHistory, AlertRule, AlertSeverity

logger = logging.getLogger(__name__)
settings = get_settings()


class AlertingEngine:
    """
    Multi-channel alerting with configurable rules and cooldowns.
    Supports: Slack, PagerDuty, Email.
    """

    def __init__(self):
        self._last_alert_times: Dict[int, datetime] = {}  # rule_id -> last_alert_time

    async def evaluate_and_alert(
        self,
        model_id: int,
        metric_type: str,
        metric_value: float,
        metric_details: Dict[str, Any] = {},
    ):
        """Evaluate all active rules against a metric and trigger alerts."""
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AlertRule).where(
                    AlertRule.is_active == True,
                    AlertRule.metric_type == metric_type,
                    (AlertRule.model_id == model_id) | (AlertRule.model_id.is_(None)),
                )
            )
            rules = result.scalars().all()

        for rule in rules:
            if self._check_condition(metric_value, rule.condition, rule.threshold):
                if self._check_cooldown(rule.id, rule.cooldown_minutes):
                    await self._trigger_alert(rule, model_id, metric_value, metric_details)

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: abs(v - t) < 1e-6,
        }
        return ops.get(condition, lambda v, t: False)(value, threshold)

    def _check_cooldown(self, rule_id: int, cooldown_minutes: int) -> bool:
        last = self._last_alert_times.get(rule_id)
        if last is None:
            return True
        return datetime.now(timezone.utc) - last > timedelta(minutes=cooldown_minutes)

    async def _trigger_alert(
        self,
        rule: AlertRule,
        model_id: int,
        metric_value: float,
        details: Dict[str, Any],
    ):
        message = (
            f"🚨 *RAI Alert: {rule.name}*\n"
            f"Model ID: {model_id}\n"
            f"Metric: {rule.metric_type} = {metric_value:.4f}\n"
            f"Threshold: {rule.condition} {rule.threshold}\n"
            f"Severity: {rule.severity.value.upper()}\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        )

        channels_notified = []
        channels = rule.channels if isinstance(rule.channels, list) else [rule.channels]

        for channel in channels:
            try:
                if channel == "slack":
                    await self._send_slack(message)
                    channels_notified.append("slack")
                elif channel == "pagerduty":
                    await self._send_pagerduty(message, rule.severity.value)
                    channels_notified.append("pagerduty")
                elif channel == "email":
                    await self._send_email(
                        subject=f"RAI Alert: {rule.name}",
                        body=message,
                    )
                    channels_notified.append("email")
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

        # Record in database
        async with async_session() as session:
            alert_record = AlertHistory(
                rule_id=rule.id,
                model_id=model_id,
                severity=rule.severity,
                message=message,
                metric_value=metric_value,
                channels_notified=channels_notified,
            )
            session.add(alert_record)
            await session.commit()

        self._last_alert_times[rule.id] = datetime.now(timezone.utc)
        logger.info(f"Alert triggered: {rule.name} via {channels_notified}")

    async def _send_slack(self, message: str):
        if not settings.SLACK_WEBHOOK_URL:
            logger.warning("Slack webhook URL not configured, skipping")
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json={"text": message},
                timeout=10.0,
            )
            response.raise_for_status()

    async def _send_pagerduty(self, message: str, severity: str):
        if not settings.PAGERDUTY_API_KEY:
            logger.warning("PagerDuty API key not configured, skipping")
            return

        pd_severity_map = {
            "low": "info",
            "medium": "warning",
            "high": "error",
            "critical": "critical",
        }

        payload = {
            "routing_key": settings.PAGERDUTY_API_KEY,
            "event_action": "trigger",
            "payload": {
                "summary": message[:1024],
                "severity": pd_severity_map.get(severity, "warning"),
                "source": "rai-monitoring-platform",
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

    async def _send_email(self, subject: str, body: str):
        if not settings.SMTP_HOST or not settings.ALERT_EMAIL_TO:
            logger.warning("Email not configured, skipping")
            return

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_EMAIL_TO

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=True,
        )


# Singleton
alerting_engine = AlertingEngine()