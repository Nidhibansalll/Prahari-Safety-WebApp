import smtplib
from email.message import EmailMessage


def send_sms(cfg, numbers, message):
    provider = str(cfg.get("SMS_PROVIDER", "console")).strip().lower()

    if provider == "console":
        print(f"[CONSOLE ALERT] To {numbers}: {message}", flush=True)
        return {"success": True, "sent": len(numbers), "error": None}

    if provider == "smtp":
        host = cfg.get("SMTP_HOST", "smtp-relay.brevo.com")
        port = int(cfg.get("SMTP_PORT", 587))
        user = cfg.get("SMTP_USER", "")
        password = cfg.get("SMTP_PASSWORD", "")
        sender = cfg.get("SMTP_FROM", "").strip()

        # Collect only real email recipients (skip carrier gateways that bounce)
        recipients = [str(n).strip() for n in numbers if "@" in str(n)]
        if sender and "@" in sender and sender not in recipients:
            recipients.append(sender)

        if not recipients:
            return {"success": False, "sent": 0, "error": "No valid email recipient configured"}

        try:
            msg = EmailMessage()
            msg["Subject"] = "🚨 PRAHARI SOS ALERT"
            msg["From"] = f"Prahari Safety <{sender}>"
            msg["To"] = ", ".join(recipients)
            msg.set_content(message)

            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)

            return {"success": True, "sent": len(recipients), "error": None}
        except Exception as e:
            return {"success": False, "sent": 0, "error": str(e)}

    return {"success": False, "sent": 0, "error": f"Unknown SMS_PROVIDER: {provider}"}
