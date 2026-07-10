import os
import sys
import bcrypt
from database import SessionLocal
from models import User

def create_admin():
    db = SessionLocal()
    try:
        email = "pcelovek102@gmail.com"
        password = "root_8888"
        username = "pcelovek102"
        
        # Проверяем, существует ли админ
        admin = db.query(User).filter(User.email == email).first()
        if admin:
            # Удаляем старого
            db.delete(admin)
            db.commit()
            print("🗑️ Старый админ удален")
        
        # Создаем хеш пароля напрямую через bcrypt
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
        
        # Создаем нового админа
        new_admin = User(
            username=username,
            email=email,
            password=hashed,
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        
        print("✅ АДМИН СОЗДАН!")
        print(f"Email: {email}")
        print(f"Пароль: {password}")
        
        # Проверяем
        check = db.query(User).filter(User.email == email).first()
        if check:
            result = bcrypt.checkpw(password.encode('utf-8'), check.password.encode('utf-8'))
            if result:
                print("✅ Проверка: пароль правильный!")
            else:
                print("❌ Проверка: пароль НЕ правильный!")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()