"""
Background notification tasks — email, SMS, and webhook hooks.
These are stub implementations that log notifications.
Plug in real providers (SendGrid, Twilio, etc.) for production.
"""

from loguru import logger

from app.tasks.celery_app import celery_app


@celery_app.task(
    name="app.tasks.notification_tasks.send_email_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="notifications",
)
def send_email_alert(
    self,
    recipient: str,
    subject: str,
    body: str,
):
    """
    Send an email alert notification.

    In production, integrate with SendGrid, AWS SES, or similar.

    Args:
        recipient: Email address.
        subject:   Email subject line.
        body:      Email body (HTML or plain text).
    """
    try:
        logger.info(
            "[EMAIL STUB] To: {} | Subject: {} | Body: {}",
            recipient, subject, body[:100],
        )
        # ----------------------------------------------------------------
        # Production implementation:
        # import sendgrid
        # sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        # message = Mail(from_email='alerts@urbansafety.ai', ...)
        # sg.send(message)
        # ----------------------------------------------------------------
        return {"status": "sent", "recipient": recipient}

    except Exception as exc:
        logger.error("Email notification failed: {}", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.notification_tasks.send_sms_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="notifications",
)
def send_sms_alert(
    self,
    phone_number: str,
    message: str,
):
    """
    Send an SMS alert notification.

    In production, integrate with Twilio or similar.

    Args:
        phone_number: Target phone number (E.164 format).
        message:      SMS body text.
    """
    try:
        logger.info(
            "[SMS STUB] To: {} | Message: {}",
            phone_number, message[:100],
        )
        # ----------------------------------------------------------------
        # Production implementation:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(body=message, from_='+1...', to=phone_number)
        # ----------------------------------------------------------------
        return {"status": "sent", "phone_number": phone_number}

    except Exception as exc:
        logger.error("SMS notification failed: {}", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.notification_tasks.send_webhook",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="notifications",
)
def send_webhook(
    self,
    webhook_url: str,
    payload: dict,
):
    """
    Send a webhook POST request with the alert payload.

    Args:
        webhook_url: Target URL.
        payload:     JSON payload to send.
    """
    try:
        logger.info(
            "[WEBHOOK STUB] URL: {} | Payload keys: {}",
            webhook_url, list(payload.keys()),
        )
        # ----------------------------------------------------------------
        # Production implementation:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(webhook_url, json=payload)
        #     response.raise_for_status()
        # ----------------------------------------------------------------
        return {"status": "sent", "webhook_url": webhook_url}

    except Exception as exc:
        logger.error("Webhook notification failed: {}", exc)
        raise self.retry(exc=exc)
