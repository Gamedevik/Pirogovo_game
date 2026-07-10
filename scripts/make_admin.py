"""
Разовый скрипт: делает пользователя админом по email.

Запуск (из папки my_game):
    py scripts/make_admin.py user@example.com

Нужен, потому что /admin доступен только тем, у кого role == "admin",
а через обычную регистрацию всем выдаётся role == "user". Так что
первого админа назначаем напрямую в БД.
"""
import sys
import os

# Добавляем корень проекта в путь, чтобы импорты database/models работали
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User


def make_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            print(f"Пользователь с email '{email}' не найден.")
            return
        user.role = "admin"
        db.commit()
        print(f"Готово: {user.username} ({user.email}) теперь admin.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: py scripts/make_admin.py user@example.com")
        sys.exit(1)
    make_admin(sys.argv[1])
