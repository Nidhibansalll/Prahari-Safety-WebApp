import smtplib
from email.message import EmailMessage


def send_sms(config, numbers, message):
    """
    Unified messenger used by app.py for SOS trigger, SOS cancel, and contact-add alerts.
    Supports SMS_PROVIDER = 'smtp' | 'twilio' | 'console'.
    """
    provider = (config.get("SMS_PROVIDER") or "console").strip().lower()
    if not numbers:
        return {"success": False, "sent": 0, "failed": 0, "error": "No recipients provided"}

    if provider == "console":
        for num in numbers:
            print(f"\n[CONSOLE SMS -> {num}]\n{message}\n", flush=True)
        return {"success": True, "sent": len(numbers), "failed": 0, "error": None}

    if provider == "smtp":
        return _send_via_smtp(config, numbers, message)

    if provider == "twilio":
        return _send_via_twilio(config, numbers, message)

    return {"success": False, "sent": 0, "failed": len(numbers), "error": f"Unknown SMS_PROVIDER: {provider}"}


def _send_via_smtp(config, numbers, message):
    host = config.get("SMTP_HOST", "smtp.gmail.com")
    port = int(config.get("SMTP_PORT", 587))
    user = config.get("SMTP_USER", "")
    password = config.get("SMTP_PASSWORD", "")
    sender = config.get("SMTP_FROM") or user
    gateway = (config.get("SMTP_SMS_GATEWAY") or "").lstrip("@").strip()

    if not user or not password:
        return {
            "success": False,
            "sent": 0,
            "failed": len(numbers),
            "error": "SMTP_USER or SMTP_PASSWORD missing in .env"
        }

    recipients = []
    for item in numbers:
        item_str = str(item).strip()
        if "@" in item_str:
            recipients.append(item_str)
        elif gateway:
            recipients.append(f"{item_str}@{gateway}")

    if not recipients:
        return {
            "success": False,
            "sent": 0,
            "failed": len(numbers),
            "error": "Set SMTP_SMS_GATEWAY in .env (e.g. airtelkk.com) or pass email recipients."
        }

    sent = 0
    errors = []
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(user, password)

        for rcpt in recipients:
            try:
                msg = EmailMessage()
                msg["Subject"] = "🚨 PRAHARI SOS ALERT"
                msg["From"] = f"Prahari Safety <{sender}>"
                msg["To"] = rcpt
                msg.set_content(message)
                server.send_message(msg)
                sent += 1
            except Exception as e:
                errors.append(f"{rcpt}: {e}")

        server.quit()
    except Exception as e:
        return {
            "success": False,
            "sent": sent,
            "failed": len(recipients) - sent,
            "error": f"SMTP connection/auth failed: {e}"
        }

    return {
        "success": sent > 0,
        "sent": sent,
        "failed": len(recipients) - sent,
        "error": "; ".join(errors) if errors else None
    }


def _send_via_twilio(config, numbers, message):
    sid = config.get("TWILIO_ACCOUNT_SID", "")
    token = config.get("TWILIO_AUTH_TOKEN", "")
    from_num = config.get("TWILIO_FROM_NUMBER", "")

    if not (sid and token and from_num):
        return {
            "success": False,
            "sent": 0,
            "failed": len(numbers),
            "error": "Twilio credentials missing in .env"
        }

    try:
        from twilio.rest import Client
        client = Client(sid, token)
    except Exception as e:
        return {"success": False, "sent": 0, "failed": len(numbers), "error": f"Twilio init error: {e}"}

    sent = 0
    errors = []
    for num in numbers:
        to_num = num if str(num).startswith("+") else f"+91{num}"
        try:
            client.messages.create(body=message, from_=from_num, to=to_num)
            sent += 1
        except Exception as e:
            errors.append(f"{to_num}: {e}")

    return {
        "success": sent > 0,
        "sent": sent,
        "failed": len(numbers) - sent,
        "error": "; ".join(errors) if errors else None
    }