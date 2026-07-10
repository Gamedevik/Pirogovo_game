from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

# ВАЖНО: замени эту строку на свой собственный длинный случайный секрет
# перед запуском в проде. Например: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = "PUT_YOUR_OWN_RANDOM_SECRET_HERE_ANY_LONG_STRING"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# --------------------------------------------------------------------
# Почему bcrypt_sha256, а не просто bcrypt:
#
# У чистого bcrypt есть жёсткое ограничение — он видит только первые
# 72 БАЙТА пароля. Раньше ты обходил это через password[:72], но это
# обрезает по СИМВОЛАМ, а не по байтам — если в пароле есть кириллица
# или эмодзи, обрезка съедет и хеш/проверка могут разойтись.
# Новые версии bcrypt вообще кидают ошибку на паролях длиннее 72 байт,
# вместо тихого обрезания — отсюда твои случайные 500-ки.
#
# bcrypt_sha256 сначала прогоняет пароль через SHA-256 (получается
# фиксированная длина 32 байта), а затем уже хеширует bcrypt-ом.
# Так лимит в 72 байта никогда не превышается, и никакого ручного
# обрезания делать не нужно.
# --------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
