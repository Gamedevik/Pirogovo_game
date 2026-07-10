from typing import Optional

from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import decode_token


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Используется на HTML-страницах (/profile, /admin и т.д).
    Никогда не кидает исключение — если пользователь не залогинен,
    просто возвращает None, а страница сама решает, что делать
    (обычно редиректит на "/").
    """
    token = request.cookies.get("token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("user_id")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == user_id).first()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Используется для "жёстких" API-маршрутов, где неавторизованный
    доступ должен возвращать 401 JSON-ошибку, а не редирект.
    """
    user = get_optional_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав (нужна роль admin)",
        )
    return user
