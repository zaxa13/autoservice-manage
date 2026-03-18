import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """
    Отправляет письмо со ссылкой для сброса пароля.
    Возвращает True при успехе, False при ошибке.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP не настроен (SMTP_USER / SMTP_PASSWORD отсутствуют). Письмо не отправлено.")
        logger.info(f"[DEV] Reset token for {to_email}: {reset_token}")
        return False

    subject = "Восстановление пароля — Автосервис"

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html_body = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    .container {{ max-width: 480px; margin: 0 auto; background: #fff; border-radius: 8px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .logo {{ font-size: 22px; font-weight: bold; color: #1a1a1a; margin-bottom: 24px; }}
    .title {{ font-size: 18px; color: #1a1a1a; margin-bottom: 12px; }}
    .text {{ font-size: 14px; color: #555; line-height: 1.6; margin-bottom: 24px; }}
    .btn {{ display: inline-block; background: #2563eb; color: #fff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; font-weight: 600; }}
    .note {{ font-size: 12px; color: #999; margin-top: 24px; }}
    .token-box {{ background: #f0f4ff; border: 1px solid #c7d7f9; border-radius: 4px; padding: 10px 14px; font-family: monospace; font-size: 13px; color: #1a1a1a; word-break: break-all; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">Автосервис</div>
    <div class="title">Сброс пароля</div>
    <p class="text">
      Здравствуйте, <strong>{username}</strong>!<br>
      Мы получили запрос на восстановление пароля для вашей учётной записи.
      Нажмите кнопку ниже чтобы задать новый пароль:
    </p>
    <a href="{reset_link}" class="btn">Сбросить пароль</a>
    <p class="text" style="margin-top:20px;">
      Или скопируйте ссылку в браузер:<br>
      <span style="color:#2563eb;font-size:12px;">{reset_link}</span>
    </p>
    <p class="note">
      Ссылка действительна <strong>30 минут</strong>.<br>
      Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо.<br>
      Ваш пароль останется прежним.
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Здравствуйте, {username}!\n\n"
        f"Для сброса пароля перейдите по ссылке:\n{reset_link}\n\n"
        f"Ссылка действительна 30 минут.\n"
        f"Если вы не запрашивали сброс — проигнорируйте это письмо."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP authentication failed for user {settings.SMTP_USER}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return False
