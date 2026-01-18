import httpx
import json
from sqlalchemy.orm import Session
from app.config import settings
from app.models.integration import IntegrationLog, IntegrationType


def check_vehicle_gibdd(db: Session, vin: str) -> dict:
    """Проверка транспортного средства в базе ГИБДД"""
    url = f"{settings.GIBDD_API_URL}/vehicle/check"
    
    headers = {
        "Authorization": f"Bearer {settings.GIBDD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "vin": vin
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            result = response.json()
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.GIBDD,
            status="success",
            request_data=json.dumps(payload),
            response_data=json.dumps(result)
        )
        db.add(log)
        db.commit()
        
        return result
    
    except Exception as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.GIBDD,
            status="error",
            request_data=json.dumps(payload),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        return {"error": str(e)}

