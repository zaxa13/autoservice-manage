import httpx
import json
from sqlalchemy.orm import Session
from app.config import settings
from app.models.integration import IntegrationLog, IntegrationType


def send_sms(db: Session, phone: str, message: str) -> bool:
    """Отправка SMS через sms.ru (пример)"""
    url = "https://sms.ru/sms/send"
    
    params = {
        "api_id": settings.SMS_API_KEY,
        "to": phone,
        "msg": message,
        "json": 1
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            result = response.json()
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.SMS,
            status="success" if result.get("status") == "OK" else "error",
            request_data=json.dumps(params),
            response_data=json.dumps(result)
        )
        db.add(log)
        db.commit()
        
        return result.get("status") == "OK"
    
    except Exception as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.SMS,
            status="error",
            request_data=json.dumps(params),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        return False

