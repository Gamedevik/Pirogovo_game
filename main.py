import os
import json
import threading
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from database import Base, engine, get_db
from models import User, Village, Building
from schemas import UserCreate
from auth import hash_password, verify_password, create_token
from dependencies import get_optional_user, get_current_user

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Хроники Пирогово",
    description="Стратегический симулятор в Telegram Mini App",
    version="1.0.0"
)

templates = Jinja2Templates(directory="templates")


# ======================================================================
# ЗАПУСК TELEGRAM БОТА В ФОНОВОМ РЕЖИМЕ
# ======================================================================

def run_telegram_bot():
    """Запускает Telegram бота в отдельном потоке"""
    try:
        from telegram_bot import main as bot_main
        bot_main()
    except Exception as e:
        print(f"⚠️ Ошибка запуска бота: {e}")

@app.on_event("startup")
def startup_event():
    """Действия при запуске приложения"""
    # Создаем админа
    create_admin_on_startup()
    
    # Запускаем Telegram бота
    if os.getenv("BOT_TOKEN"):
        thread = threading.Thread(target=run_telegram_bot, daemon=True)
        thread.start()
        print("🤖 Telegram бот запущен в фоновом режиме")
    else:
        print("⚠️ BOT_TOKEN не задан, бот не запущен")


# ======================================================================
# АВТОМАТИЧЕСКОЕ СОЗДАНИЕ АДМИНА
# ======================================================================

def create_admin_on_startup():
    """Автоматически создает админа при первом запуске"""
    from database import SessionLocal
    from models import User
    from auth import hash_password
    import bcrypt
    
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
        
        if admin:
            # Обновляем пароль через bcrypt
            password_bytes = admin_password.encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            admin.password = hashed
            admin.role = "admin"
            db.commit()
            print(f"✅ Пароль администратора обновлен: {admin_email}")
        else:
            # Создаем нового админа
            password_bytes = admin_password.encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            
            admin = User(
                username=admin_username,
                email=admin_email,
                password=hashed,
                role="admin"
            )
            db.add(admin)
            db.commit()
            print(f"✅ Администратор создан!")
            print(f"   Email: {admin_email}")
            print(f"   Пароль: {admin_password}")
                
    except Exception as e:
        print(f"⚠️ Ошибка создания админа: {e}")
    finally:
        db.close()


# ======================================================================
# ЭНДПОИНТ ДЛЯ СОЗДАНИЯ АДМИНА ЧЕРЕЗ БРАУЗЕР
# ======================================================================

@app.get("/create-admin-now")
def create_admin_now(db: Session = Depends(get_db)):
    """Создает админа при переходе по ссылке"""
    import bcrypt
    
    email = "pcelovek102@gmail.com"
    password = "root_8888"
    username = "pcelovek102"
    
    # Удаляем старого админа
    admin = db.query(User).filter(User.email == email).first()
    if admin:
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
    
    return {
        "message": "Администратор создан!",
        "email": email,
        "password": password
    }


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
            return JSONResponse(
                status_code=400,
                content={"error": "No user data from Telegram"}
            )
        
        # Получаем данные от Telegram
        telegram_id = str(user_data.get('id'))
        username = user_data.get('username', f"user_{telegram_id}")
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or username
        
        # Проверяем, существует ли пользователь
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            # Создаем нового пользователя
            import secrets
            from auth import hash_password
            
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
            print(f"✅ Создан новый пользователь через Telegram: {username}")
        
        # Создаем JWT токен
        token = create_token({"user_id": user.id, "role": user.role})
        
        return {
            "status": "ok",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }
        
    except Exception as e:
        print(f"⚠️ Ошибка Telegram авторизации: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


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
        httponly=True,
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
# ИГРОВЫЕ МАРШРУТЫ
# ======================================================================

@app.get("/game")
def game_page(
    request: Request,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Игровая страница"""
    if not user:
        return RedirectResponse("/", status_code=303)
    
    # Получаем или создаем деревню
    village = db.query(Village).filter(Village.user_id == user.id).first()
    if not village:
        village = Village(
            user_id=user.id,
            name=f"Деревня {user.username}",
            wood=100,
            food=100,
            gold=50,
            population=10
        )
        db.add(village)
        db.commit()
        db.refresh(village)
    
    return templates.TemplateResponse(
        request,
        "game.html",
        {"user": user, "village": village}
    )


@app.post("/game/build/{building_type}")
def build_building(
    building_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Строит здание в деревне"""
    village = db.query(Village).filter(Village.user_id == user.id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Деревня не найдена")
    
    # Стоимость строительства
    costs = {
        "farm": {"wood": 50, "gold": 20},
        "lumbermill": {"wood": 30, "gold": 10},
        "mine": {"wood": 40, "gold": 30},
        "barracks": {"wood": 60, "gold": 40}
    }
    
    if building_type not in costs:
        raise HTTPException(status_code=400, detail="Неизвестный тип здания")
    
    cost = costs[building_type]
    
    # Проверяем ресурсы
    if village.wood < cost["wood"] or village.gold < cost["gold"]:
        raise HTTPException(status_code=400, detail="Недостаточно ресурсов")
    
    # Строим здание
    building = Building(
        village_id=village.id,
        type=building_type,
        level=1
    )
    db.add(building)
    village.wood -= cost["wood"]
    village.gold -= cost["gold"]
    db.commit()
    
    return {"message": f"Здание {building_type} построено!"}


# ======================================================================
# ВЫХОД
# ======================================================================

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("token")
    return response


# ======================================================================
# HEALTH CHECK
# ======================================================================

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Хроники Пирогово"}


# ======================================================================
# ЗАПУСК
# ======================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)