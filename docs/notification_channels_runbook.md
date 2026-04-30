# Notification Channels Runbook (SMS, Email, WhatsApp)

## Purpose

This runbook describes outbound alert delivery for opt-in channels and failure handling.

## Environment configuration

Set provider credentials through environment variables (never hardcode):

- `SMS_API_KEY` (used by `SMSProvider`)
- `EMAIL_API_KEY` (used by `EmailProvider`)
- `WHATSAPP_API_KEY` (used by `WhatsAppProvider`)

If a key is missing, delivery fails with `MissingProviderConfigurationError` and a failed audit record is produced.

## Delivery flow

1. Alert payload is prepared (usually from `render_alert_template`).
2. `NotificationDispatcher.dispatch(...)` is called with:
   - `payload`
   - `NotificationRecipient`
   - target `NotificationChannel`
3. Dispatcher enforces channel opt-in before calling provider.
4. Audit entries are appended for each state:
   - `attempted`
   - `succeeded`
   - `retryable_failed`
   - `failed`
   - `blocked` (opt-in denied)
5. Retryable errors are retried up to `max_retries`.

## Failure handling and operations

- `blocked`: recipient is not opted in for channel; update recipient channel preferences.
- `failed` with `channel provider not configured`: add missing provider adapter in runtime config.
- `failed` with missing credential: set required environment variable in deployment secret store.
- `retry limit exceeded`: investigate provider outage or payload quality and re-dispatch after incident resolution.

## Security notes

- Keep API keys in deployment secret manager / environment injection.
- Do not store provider secrets in repository, tests, or logs.
- Audit records should keep operational metadata only (status, reason, provider message id), not credentials.
