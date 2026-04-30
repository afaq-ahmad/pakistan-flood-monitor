import os

import pytest

from pakistan_flood_monitor.services.notifications import (
    EmailProvider,
    MissingProviderConfigurationError,
    NotificationChannel,
    NotificationDispatcher,
    NotificationRecipient,
    RetryableDeliveryError,
    SMSProvider,
    WhatsAppProvider,
)


class FlakySMSProvider(SMSProvider):
    def __init__(self) -> None:
        super().__init__(provider_name="flaky-sms", api_key_env_var="SMS_API_KEY")
        self.calls = 0

    def send(self, payload, recipient):
        self.calls += 1
        if self.calls < 2:
            raise RetryableDeliveryError("temporary timeout")
        return super().send(payload, recipient)


@pytest.fixture
def configured_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMS_API_KEY", "sms-secret")
    monkeypatch.setenv("EMAIL_API_KEY", "email-secret")
    monkeypatch.setenv("WHATSAPP_API_KEY", "wa-secret")


def _recipient() -> NotificationRecipient:
    return NotificationRecipient(
        recipient_id="ops-1",
        phone_number="+923001112233",
        email="ops@example.org",
        whatsapp_number="+923001112233",
        opt_in_channels={NotificationChannel.sms, NotificationChannel.email, NotificationChannel.whatsapp},
    )


def test_dispatch_success_for_each_adapter(configured_env: None) -> None:
    dispatcher = NotificationDispatcher(
        providers={
            NotificationChannel.sms: SMSProvider("twilio-stub", "SMS_API_KEY"),
            NotificationChannel.email: EmailProvider("ses-stub", "EMAIL_API_KEY"),
            NotificationChannel.whatsapp: WhatsAppProvider("meta-stub", "WHATSAPP_API_KEY"),
        }
    )
    payload = {"event_id": "evt-101", "template": "ndma_pdma_flood_alert_v1"}
    recipient = _recipient()

    sms_result = dispatcher.dispatch(payload, recipient, NotificationChannel.sms)
    email_result = dispatcher.dispatch(payload, recipient, NotificationChannel.email)
    wa_result = dispatcher.dispatch(payload, recipient, NotificationChannel.whatsapp)

    assert sms_result.provider_message_id.startswith("sms-")
    assert email_result.provider_message_id.startswith("email-")
    assert wa_result.provider_message_id.startswith("wa-")
    assert any(entry.status == "succeeded" and entry.channel == "sms" for entry in dispatcher.audit_log)
    assert any(entry.status == "succeeded" and entry.channel == "email" for entry in dispatcher.audit_log)
    assert any(entry.status == "succeeded" and entry.channel == "whatsapp" for entry in dispatcher.audit_log)


def test_opt_in_enforcement_blocks_delivery(configured_env: None) -> None:
    dispatcher = NotificationDispatcher(providers={NotificationChannel.sms: SMSProvider("twilio-stub", "SMS_API_KEY")})
    recipient = NotificationRecipient(
        recipient_id="ops-2",
        phone_number="+923002223334",
        opt_in_channels={NotificationChannel.email},
    )

    with pytest.raises(PermissionError):
        dispatcher.dispatch({"event_id": "evt-102"}, recipient, NotificationChannel.sms)

    assert dispatcher.audit_log[-1].status == "blocked"


def test_retry_and_failure_audit(configured_env: None) -> None:
    dispatcher = NotificationDispatcher(
        providers={NotificationChannel.sms: FlakySMSProvider()},
        max_retries=2,
    )
    recipient = _recipient()

    result = dispatcher.dispatch({"event_id": "evt-103"}, recipient, NotificationChannel.sms)

    assert result.provider_message_id.startswith("sms-")
    statuses = [entry.status for entry in dispatcher.audit_log]
    assert "retryable_failed" in statuses
    assert statuses.count("attempted") >= 2
    assert statuses[-1] == "succeeded"


def test_missing_config_fails_without_hardcoded_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMS_API_KEY", raising=False)
    provider = SMSProvider("twilio-stub", "SMS_API_KEY")

    with pytest.raises(MissingProviderConfigurationError):
        provider.send({"event_id": "evt-104"}, _recipient())


def test_unconfigured_channel_is_visible_failure(configured_env: None) -> None:
    dispatcher = NotificationDispatcher(providers={})

    with pytest.raises(ValueError):
        dispatcher.dispatch({"event_id": "evt-105"}, _recipient(), NotificationChannel.sms)

    assert dispatcher.audit_log[-1].status == "failed"
    assert dispatcher.audit_log[-1].details["reason"] == "channel provider not configured"
