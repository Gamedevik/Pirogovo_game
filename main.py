import os
import json
import subprocess
import sys
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from database import Base, engine, get_db
from models import User
from schemas import UserCreate
from auth import hash_password, verify_password, create_token
from dependencies import get_optional_user, get_current_user

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Хроники Пирогово",
    description="Стратегическая игра в Telegram",
    version="1.0.0"
)

templates = Jinja2Templates(directory="templates")


# ======================================================================
# ЗАПУСК TELEGRAM БОТА
# ======================================================================

def start_bot():
    """Запускает Telegram бота в отдельном процессе"""
    try:
        if not os.getenv("BOT_TOKEN"):
            print("⚠️ BOT_TOKEN не задан")
            return
        
        # Просто запускаем бота без проверки через ps
        process = subprocess.Popen(
            [sys.executable, "telegram_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"🤖 Бот запущен (PID: {process.pid})")
        
    except Exception as e:
        print(f"⚠️ Ошибка запуска бота: {e}")

@app.on_event("startup")
def startup_event():
    """Действия при запуске"""
    create_admin_on_startup()
    start_bot()


# ======================================================================
# СОЗДАНИЕ АДМИНА
# ======================================================================

def create_admin_on_startup():
    """Создает админа при первом запуске"""
    from database import SessionLocal
    from models import User
    import bcrypt
    
    if os.getenv("CREATE_ADMIN", "false").lower() != "true":
        return
    
    db = SessionLocal()
    try:
        email = os.getenv("ADMIN_EMAIL", "pcelovek102@gmail.com")
        password = os.getenv("ADMIN_PASSWORD", "root_8888")
        username = os.getenv("ADMIN_USERNAME", "pcelovek102")
        
        admin = db.query(User).filter(User.email == email).first()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if admin:
            admin.password = hashed
            admin.role = "admin"
            db.commit()
            print(f"✅ Админ обновлен: {email}")
        else:
            admin = User(username=username, email=email, password=hashed, role="admin")
            db.add(admin)
            db.commit()
            print(f"✅ Админ создан: {email}")
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    finally:
        db.close()


# ======================================================================
# TELEGRAM АВТОРИЗАЦИЯ
# ======================================================================

@app.post("/telegram-auth")
async def telegram_auth(request: Request, db: Session = Depends(get_db)):
    """Авторизация через Telegram WebApp"""
    try:
        data = await request.json()
        user_data = data.get('user')
        
        if not user_data:
            return JSONResponse(status_code=400, content={"error": "No user data"})
        
        telegram_id = str(user_data.get('id'))
        username = user_data.get('username', f"user_{telegram_id}")
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or username
        
        # Ищем пользователя
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            import secrets
            email = f"{telegram_id}@telegram.user"
            user = User(
                username=username,
                email=email,
                password=hash_password(secrets.token_urlsafe(16)),
                role="user"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Новый пользователь: {username}")
        
        # Создаем токен
        token = create_token({"user_id": user.id, "role": user.role})
        
        return {
            "status": "ok",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": full_name
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ======================================================================
# ОСНОВНЫЕ МАРШРУТЫ
# ======================================================================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/game")
def game_page(request: Request, user: User = Depends(get_optional_user)):
    """Страница игры (карточка пользователя)"""
    if not user:
        return RedirectResponse("/", status_code=303)
    
    return templates.TemplateResponse(
        request,
        "game.html",
        {"user": user}
    )

@app.get("/profile")
def profile(request: Request, user: User = Depends(get_optional_user)):
    if not user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "profile.html", {"user": user})

@app.get("/admin")
def admin_panel(request: Request, user: User = Depends(get_optional_user), db: Session = Depends(get_db)):
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=303)
    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(request, "admin.html", {"user": user, "users": users})

@app.get("/create-admin-now")
def create_admin_now(db: Session = Depends(get_db)):
    """Создает админа"""
    import bcrypt
    
    email = "pcelovek102@gmail.com"
    password = "root_8888"
    username = "pcelovek102"
    
    try:
        admin = db.query(User).filter(User.email == email).first()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if admin:
            admin.password = hashed
            admin.role = "admin"
            db.commit()
            return {"status": "ok", "message": "Админ обновлен"}
        else:
            new_admin = User(username=username, email=email, password=hashed, role="admin")
            db.add(new_admin)
            db.commit()
            return {"status": "ok", "message": "Админ создан"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/register")
def register(username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        data = UserCreate(username=username, email=email, password=password)
    except ValidationError as e:
        return RedirectResponse(f"/?detail={e.errors()[0]['msg']}", status_code=303)
    
    if db.query(User).filter((User.email == data.email) | (User.username == data.username)).first():
        return RedirectResponse("/?detail=Логин или email заняты", status_code=303)
    
    user = User(username=data.username, email=data.email, password=hash_password(data.password), role="user")
    db.add(user)
    db.commit()
    return RedirectResponse("/?msg=registered", status_code=303)

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password):
        return RedirectResponse("/?detail=Неверный логин или пароль", status_code=303)
    
    token = create_token({"user_id": user.id, "role": user.role})
    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie(key="token", value=token, httponly=True, samesite="lax", max_age=24*60*60)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("token")
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)


@app.get("/api/map-data")
def get_map_data():
    """Возвращает данные карты из KML"""
    from kml_parser import parse_kml
    
    territories = parse_kml('data/Карта развалившегося пирогово_01-07-2025_18-11-29.kml')
    
    return {
        "territories": territories,
        "bounds": {
            "min_lat": 53.12,
            "max_lat": 53.18,
            "min_lon": 56.76,
            "max_lon": 56.81
        }
    }
@app.get("/game")
def game_page(request: Request, user: User = Depends(get_optional_user)):
    if not user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "game.html", {"user": user})

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    # Простой SVG-круг как иконка
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="#c5a83d"/>
        <text x="50" y="65" font-size="40" text-anchor="middle" fill="#1a1f16">🏰</text>
    </svg>'''
    return Response(content=svg, media_type="image/svg+xml")