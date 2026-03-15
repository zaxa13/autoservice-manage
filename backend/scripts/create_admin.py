#!/usr/bin/env python3
"""
Скрипт для создания первого администратора системы.
Использование: python scripts/create_admin.py
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_first_admin():
    """Создание первого администратора"""
    # Создаем таблицы, если их нет
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Проверяем, есть ли уже пользователи
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("⚠️  В системе уже есть пользователи!")
            admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
            if admin_exists:
                print(f"✅ Администратор уже существует: {admin_exists.username}")
                return
            else:
                print("❌ Пользователи есть, но администратора нет. Используйте API для создания.")
                return
        
        # Запрашиваем данные
        print("=" * 50)
        print("Создание первого администратора")
        print("=" * 50)
        
        username = input("Введите имя пользователя (username): ").strip()
        if not username:
            print("❌ Имя пользователя не может быть пустым!")
            return
        
        email = input("Введите email: ").strip()
        if not email:
            print("❌ Email не может быть пустым!")
            return
        
        password = input("Введите пароль: ").strip()
        if not password:
            print("❌ Пароль не может быть пустым!")
            return
        
        # Проверяем, не существует ли уже такой пользователь
        if db.query(User).filter(User.username == username).first():
            print(f"❌ Пользователь с именем '{username}' уже существует!")
            return
        
        if db.query(User).filter(User.email == email).first():
            print(f"❌ Пользователь с email '{email}' уже существует!")
            return
        
        # Создаем администратора
        admin = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("=" * 50)
        print("✅ Администратор успешно создан!")
        print(f"   Username: {admin.username}")
        print(f"   Email: {admin.email}")
        print(f"   Role: {admin.role.value}")
        print("=" * 50)
        print("\nТеперь вы можете войти в систему и создавать других пользователей через API.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании администратора: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_first_admin()

