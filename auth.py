import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

# Берем секрет из переменных окружения
SECRET_KEY = os.getenv("SECRET_KEY", "PUT_YOUR_OWN_RANDOM_SECRET_HERE_ANY_LONG_STRING")
if SECRET_KEY == "PUT_YOUR_OWN_RANDOM_SECRET_HERE_ANY_LONG_STRING":
    raise ValueError("⚠️ Установите SECRET_KEY в переменных окружения!")

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 24))

# Используем bcrypt с обходом ошибки версии
try:
    # Пробуем стандартный способ
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    # Если ошибка - используем обходной путь
    import bcrypt
    from passlib.handlers.bcrypt import bcrypt as bcrypt_handler
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Принудительно устанавливаем бекенд
    bcrypt_handler.set_backend("bcrypt")

def hash_password(password: str) -> str:
    """Хеширует пароль с обрезанием до 72 байт"""
    # bcrypt имеет ограничение 72 байта
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Проверяет пароль"""
    try:
        # Обрезаем до 72 байт
        if len(plain.encode('utf-8')) > 72:
            plain = plain[:72]
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def create_token(data: dict) -> str:
    """Создает JWT токен"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    """Декодирует JWT токен"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None