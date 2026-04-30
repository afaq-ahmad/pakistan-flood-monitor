from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol


class NotificationChannel(str, Enum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"


@dataclass
class NotificationRecipient:
    recipient_id: str
    phone_number: str | None = None
    email: str | None = None
    whatsapp_number: str | None = None
    opt_in_channels: set[NotificationChannel] = field(default_factory=set)


@dataclass
class NotificationResult:
    provider_message_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryAttempt:
    event_id: str
    recipient_id: str
    channel: str
    provider: str
    status: str
    attempt: int
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


class RetryableDeliveryError(RuntimeError):
    pass


class NotificationProvider(Protocol):
    channel: NotificationChannel
    provider_name: str

    def send(self, payload: dict[str, Any], recipient: NotificationRecipient) -> NotificationResult:
        ...


class MissingProviderConfigurationError(RuntimeError):
    pass


class BaseStubProvider:
    channel: NotificationChannel

    def __init__(self, provider_name: str, api_key_env_var: str) -> None:
        self.provider_name = provider_name
        self.api_key_env_var = api_key_env_var

    def _require_api_key(self) -> str:
        api_key = os.getenv(self.api_key_env_var)
        if not api_key:
            raise MissingProviderConfigurationError(
                f"missing required provider credential: {self.api_key_env_var}"
            )
        return api_key


class SMSProvider(BaseStubProvider):
    channel = NotificationChannel.sms

    def send(self, payload: dict[str, Any], recipient: NotificationRecipient) -> NotificationResult:
        self._require_api_key()
        if not recipient.phone_number:
            raise ValueError("recipient missing phone_number for SMS delivery")
        if payload.get("force_retry"):
            raise RetryableDeliveryError("simulated transient SMS failure")
        return NotificationResult(
            provider_message_id=f"sms-{recipient.recipient_id}-{payload.get('event_id', 'unknown')}",
            metadata={"destination": recipient.phone_number},
        )


class EmailProvider(BaseStubProvider):
    channel = NotificationChannel.email

    def send(self, payload: dict[str, Any], recipient: NotificationRecipient) -> NotificationResult:
        self._require_api_key()
        if not recipient.email:
            raise ValueError("recipient missing email for email delivery")
        if payload.get("force_retry"):
            raise RetryableDeliveryError("simulated transient email failure")
        return NotificationResult(
            provider_message_id=f"email-{recipient.recipient_id}-{payload.get('event_id', 'unknown')}",
            metadata={"destination": recipient.email, "subject": payload.get("template", "flood-alert")},
        )


class WhatsAppProvider(BaseStubProvider):
    channel = NotificationChannel.whatsapp

    def send(self, payload: dict[str, Any], recipient: NotificationRecipient) -> NotificationResult:
        self._require_api_key()
        if not recipient.whatsapp_number:
            raise ValueError("recipient missing whatsapp_number for WhatsApp delivery")
        if payload.get("force_retry"):
            raise RetryableDeliveryError("simulated transient WhatsApp failure")
        return NotificationResult(
            provider_message_id=f"wa-{recipient.recipient_id}-{payload.get('event_id', 'unknown')}",
            metadata={"destination": recipient.whatsapp_number},
        )


class NotificationDispatcher:
    def __init__(self, providers: dict[NotificationChannel, NotificationProvider], max_retries: int = 2) -> None:
        self.providers = providers
        self.max_retries = max_retries
        self.audit_log: list[DeliveryAttempt] = []

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()

    def _record(self, **kwargs: Any) -> None:
        self.audit_log.append(DeliveryAttempt(timestamp=self._timestamp(), **kwargs))

    def dispatch(self, payload: dict[str, Any], recipient: NotificationRecipient, channel: NotificationChannel) -> NotificationResult:
        event_id = payload.get("event_id", "unknown")
        provider = self.providers.get(channel)
        if provider is None:
            self._record(
                event_id=event_id,
                recipient_id=recipient.recipient_id,
                channel=channel.value,
                provider="unconfigured",
                status="failed",
                attempt=0,
                details={"reason": "channel provider not configured"},
            )
            raise ValueError(f"provider not configured for channel={channel.value}")

        if channel not in recipient.opt_in_channels:
            self._record(
                event_id=event_id,
                recipient_id=recipient.recipient_id,
                channel=channel.value,
                provider=provider.provider_name,
                status="blocked",
                attempt=0,
                details={"reason": "recipient did not opt in"},
            )
            raise PermissionError(f"recipient {recipient.recipient_id} is not opted in for {channel.value}")

        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            self._record(
                event_id=event_id,
                recipient_id=recipient.recipient_id,
                channel=channel.value,
                provider=provider.provider_name,
                status="attempted",
                attempt=attempt,
            )
            try:
                result = provider.send(payload, recipient)
                self._record(
                    event_id=event_id,
                    recipient_id=recipient.recipient_id,
                    channel=channel.value,
                    provider=provider.provider_name,
                    status="succeeded",
                    attempt=attempt,
                    details={"provider_message_id": result.provider_message_id},
                )
                return result
            except RetryableDeliveryError as exc:
                self._record(
                    event_id=event_id,
                    recipient_id=recipient.recipient_id,
                    channel=channel.value,
                    provider=provider.provider_name,
                    status="retryable_failed",
                    attempt=attempt,
                    details={"reason": str(exc)},
                )
                if attempt > self.max_retries:
                    break
            except Exception as exc:  # noqa: BLE001
                self._record(
                    event_id=event_id,
                    recipient_id=recipient.recipient_id,
                    channel=channel.value,
                    provider=provider.provider_name,
                    status="failed",
                    attempt=attempt,
                    details={"reason": str(exc)},
                )
                raise

        self._record(
            event_id=event_id,
            recipient_id=recipient.recipient_id,
            channel=channel.value,
            provider=provider.provider_name,
            status="failed",
            attempt=attempt,
            details={"reason": "retry limit exceeded"},
        )
        raise RuntimeError(f"delivery failed after {attempt} attempts for channel={channel.value}")
