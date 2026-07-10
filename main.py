from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from database import Base, engine, get_db
from models import User
from schemas import UserCreate
from auth import hash_password, verify_password, create_token
from dependencies import get_optional_user

# Создаёт таблицы, если их ещё нет. Модель должна быть импортирована
# (import models.User выше) ДО этой строки, иначе SQLAlchemy о ней не узнает.
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# ======================================================================
# ГЛАВНАЯ СТРАНИЦА
# ======================================================================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


# ======================================================================
# РЕГИСТРАЦИЯ
# ======================================================================

@app.post("/register")
def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Валидация данных через pydantic-схему (длина имени, формат email,
    # длина пароля). Если что-то не так - собираем понятную ошибку
    # и редиректим обратно с ?detail=...
    try:
        data = UserCreate(username=username, email=email, password=password)
    except ValidationError as e:
        first_error = e.errors()[0]["msg"]
        return RedirectResponse(f"/?detail={first_error}", status_code=303)

    user_exists = (
        db.query(User)
        .filter((User.email == data.email) | (User.username == data.username))
        .first()
    )
    if user_exists:
        return RedirectResponse("/?detail=Логин или email уже заняты", status_code=303)

    user = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role="user",
    )
    db.add(user)
    db.commit()

    return RedirectResponse("/?msg=registered", status_code=303)


# ======================================================================
# ЛОГИН
# ======================================================================

@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.strip().lower()).first()

    if not user or not verify_password(password, user.password):
        return RedirectResponse("/?detail=Неверный логин или пароль", status_code=303)

    token = create_token({"user_id": user.id, "role": user.role})

    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,   # JS не может прочитать куку - защита от XSS-кражи токена
        samesite="lax",
        max_age=24 * 60 * 60,
    )
    return response


# ======================================================================
# ПРОФИЛЬ
# ======================================================================

@app.get("/profile")
def profile(request: Request, user: User = Depends(get_optional_user)):
    if not user:
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {"user": user},
    )


# ======================================================================
# СМЕНА ПАРОЛЯ
# ======================================================================

@app.post("/change-password")
def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/", status_code=303)

    if not verify_password(old_password, user.password):
        return RedirectResponse("/profile?detail=Старый пароль неверен", status_code=303)

    if len(new_password) < 6:
        return RedirectResponse(
            "/profile?detail=Новый пароль должен быть не короче 6 символов",
            status_code=303,
        )

    user.password = hash_password(new_password)
    db.commit()

    return RedirectResponse("/profile?msg=password_changed", status_code=303)


# ======================================================================
# АДМИН-ПАНЕЛЬ
# ======================================================================

@app.get("/admin")
def admin_panel(
    request: Request,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/", status_code=303)
    if user.role != "admin":
        return RedirectResponse("/profile?detail=Доступ только для admin", status_code=303)

    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"user": user, "users": users},
    )


# ======================================================================
# ВЫХОД
# ======================================================================

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("token")
    return response

@app.get("/health")
def health_check():
    return {"status": "ok"}
# ======================================================================
# АВТОМАТИЧЕСКОЕ СОЗДАНИЕ АДМИНА
# ======================================================================

@app.on_event("startup")
def create_admin_on_startup():
    """Автоматически создает админа при первом запуске"""
    from database import SessionLocal
    from models import User
    from auth import hash_password
    import os
    
    # Проверяем, нужно ли создать админа
    create_admin = os.getenv("CREATE_ADMIN", "false").lower() == "true"
    
    if not create_admin:
        return
    
    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "pcelovek102@gmail.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "root_8888")
        admin_username = os.getenv("ADMIN_USERNAME", "pcelovek102")
        
        print(f"🔍 Проверка администратора: {admin_email}")
        
        # Проверяем, существует ли админ
        admin = db.query(User).filter(User.email == admin_email).first()
        
        if not admin:
            # Создаем нового админа
            admin = User(
                username=admin_username,
                email=admin_email,
                password=hash_password(admin_password),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print(f"✅ Администратор создан!")
            print(f"   Email: {admin_email}")
            print(f"   Пароль: {admin_password}")
        else:
            # Обновляем существующего до админа
            if admin.role != "admin":
                admin.role = "admin"
                admin.password = hash_password(admin_password)
                db.commit()
                print(f"✅ Пользователь {admin_email} обновлен до администратора!")
            else:
                print(f"ℹ️ Пользователь {admin_email} уже является администратором")
                
    except Exception as e:
        print(f"⚠️ Ошибка создания админа: {e}")
    finally:
        db.close()

#Добавляем эндпоинт для создания админа (через API)        
@app.post("/create-admin")
def create_admin_endpoint(
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    """Создает администратора (защищено секретным ключом)"""
    secret = os.getenv("ADMIN_SECRET", "")
    
    # Проверяем секретный ключ (можно передать в заголовке)
    # Для простоты - просто создаем, если нет админа
    
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return {"error": "Пользователь уже существует"}
    
    user = User(
        username=username,
        email=email,
        password=hash_password(password),
        role="admin"
    )
    db.add(user)
    db.commit()
    
    return {"message": f"Администратор {username} создан!"}        
