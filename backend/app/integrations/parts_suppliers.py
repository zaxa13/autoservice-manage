import httpx
import json
from sqlalchemy.orm import Session
from app.config import settings
from app.models.integration import IntegrationLog, IntegrationType


def search_parts(db: Session, query: str) -> dict:
    """Поиск запчастей у поставщиков"""
    url = f"{settings.PARTS_SUPPLIER_API_URL}/search"
    
    headers = {
        "Authorization": f"Bearer {settings.PARTS_SUPPLIER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "query": query
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            result = response.json()
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.PARTS_SUPPLIER,
            status="success",
            request_data=json.dumps(params),
            response_data=json.dumps(result)
        )
        db.add(log)
        db.commit()
        
        return result
    
    except Exception as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.PARTS_SUPPLIER,
            status="error",
            request_data=json.dumps(params),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        return {"error": str(e), "results": []}


def create_supplier_order(db: Session, order_data: dict) -> dict:
    """Создание заказа у поставщика"""
    url = f"{settings.PARTS_SUPPLIER_API_URL}/orders"
    
    headers = {
        "Authorization": f"Bearer {settings.PARTS_SUPPLIER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=order_data, timeout=10.0)
            response.raise_for_status()
            result = response.json()
        
        # Логирование
        log = IntegrationLog(
            integration_type=IntegrationType.PARTS_SUPPLIER,
            status="success",
            request_data=json.dumps(order_data),
            response_data=json.dumps(result)
        )
        db.add(log)
        db.commit()
        
        return result
    
    except Exception as e:
        # Логирование ошибки
        log = IntegrationLog(
            integration_type=IntegrationType.PARTS_SUPPLIER,
            status="error",
            request_data=json.dumps(order_data),
            response_data=str(e)
        )
        db.add(log)
        db.commit()
        return {"error": str(e)}

