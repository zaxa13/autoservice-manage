import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.config import settings
from app.models.integration import IntegrationLog, IntegrationType


def send_email(db: Session, to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """Отправка email"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        
        # Текстовая версия
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)
        
        # HTML версия (если есть)
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)
        
        # Отправка
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.EMAIL,
            status="success",
            request_data=json.dumps({"to": to_email, "subject": subject}),
            response_data="Email sent successfully"
        )
        db.add(log)
        db.commit()
        
        return True
    
    except Exception as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.EMAIL,
            status="error",
            request_data=json.dumps({"to": to_email, "subject": subject}),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        return False

