"""Transactional emails sent through SMTP or Resend."""

import html
import logging
import smtplib
from email.message import EmailMessage

import resend

from config import settings

logger = logging.getLogger("knowly.email")


def _send_smtp(to: str, subject: str, body_html: str) -> None:
    """Deliver through SMTP: a local catcher such as MailDev, or an authenticated
    server such as Gmail (STARTTLS + login) when credentials are configured."""
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Este mail requiere un cliente con soporte HTML.")
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_username:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    logger.info("Email to %s sent to SMTP %s:%s | %s", to, settings.smtp_host, settings.smtp_port, subject)


def _send(to: str, subject: str, body_html: str) -> None:
    if settings.smtp_host:
        _send_smtp(to, subject, body_html)
        return

    if not settings.resend_api_key:
        # Dev fallback: no provider configured, print the email instead of sending it.
        logger.warning("RESEND_API_KEY not set. Email to %s | %s\n%s", to, subject, body_html)
        return

    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": body_html,
    })


def _layout(content: str) -> str:
    return (
        '<div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#111">'
        '<h2 style="margin:0 0 16px">Knowly</h2>'
        f"{content}"
        "</div>"
    )


def send_otp_email(to: str, code: str) -> None:
    _send(
        to,
        f"Tu código de acceso a Knowly: {code}",
        _layout(
            "<p>Usá este código para ingresar a Knowly:</p>"
            f'<p style="font-size:32px;font-weight:700;letter-spacing:6px;margin:16px 0">{code}</p>'
            f"<p>Vence en {settings.otp_expire_minutes} minutos. "
            "Si no lo pediste, podés ignorar este mail.</p>"
        ),
    )


def send_access_approved_email(to: str) -> None:
    url = html.escape(settings.frontend_url)
    _send(
        to,
        "Tu acceso a Knowly fue aprobado",
        _layout(
            "<p>Ya tenés acceso a Knowly.</p>"
            f'<p><a href="{url}/login">Ingresá con tu mail</a> y te enviaremos un código.</p>'
        ),
    )


def send_new_request_email(requester: str) -> None:
    url = html.escape(settings.frontend_url)
    for admin in settings.admin_emails:
        _send(
            admin,
            "Nueva solicitud de acceso a Knowly",
            _layout(
                f"<p><strong>{html.escape(requester)}</strong> pidió acceso a Knowly.</p>"
                f'<p><a href="{url}/admin">Revisar solicitudes</a></p>'
            ),
        )
