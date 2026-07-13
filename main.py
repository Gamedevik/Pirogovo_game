import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from database import Base, engine, get_db
from models import User, Territory, BuildingOnMap, GameQueue
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
        
        process = subprocess.Popen(
            [sys.executable, "telegram_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"🤖 Бот запущен (PID: {process.pid})")
        
    except Exception as e:
        print(f"⚠️ Ошибка запуска бота: {e}")


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
# ЗАГРУЗКА КАРТЫ ИЗ KML
# ======================================================================

def create_test_territories(db):
    """Создаёт тестовые территории, если KML не загрузился"""
    from models import Territory
    
    test_territories = [
        {'name': 'Пирогово', 'faction': 'Сенат', 'color': '#4345ed', 'lat': 56.779955, 'lon': 53.15681, 'pop': 1200},
        {'name': 'Сыпычевский пруд', 'faction': 'Пираты', 'color': '#c97b17', 'lat': 56.7732, 'lon': 53.1379, 'pop': 300},
        {'name': 'Гвардейская крепость', 'faction': 'Гвардия', 'color': '#ff1eb5', 'lat': 56.7723, 'lon': 53.1540, 'pop': 500},
        {'name': 'Разбойничий стан', 'faction': 'Разбойники', 'color': '#595959', 'lat': 56.7798, 'lon': 53.1528, 'pop': 200},
        {'name': 'Пироговская ГЭС', 'faction': 'Рабочие', 'color': '#79470e', 'lat': 56.7797, 'lon': 53.1645, 'pop': 800},
        {'name': 'Территория Шигапова', 'faction': 'Шигапов', 'color': '#1ed2ff', 'lat': 56.7849, 'lon': 53.1817, 'pop': 600},
        {'name': 'Синдикаты', 'faction': 'Синдикаты', 'color': '#03ad1b', 'lat': 56.7815, 'lon': 53.1651, 'pop': 400},
        {'name': 'Территория негров', 'faction': 'Негры', 'color': '#4345ed', 'lat': 56.7758, 'lon': 53.1260, 'pop': 150},
        {'name': 'Военный округ', 'faction': 'Воен.округ', 'color': '#03ad1b', 'lat': 56.7813, 'lon': 53.1366, 'pop': 350},
        {'name': 'Мотоциклисты', 'faction': 'Мото', 'color': '#4345ed', 'lat': 56.7775, 'lon': 53.1404, 'pop': 250},
        {'name': 'Независимые ВВС', 'faction': 'ВВС', 'color': '#1ed2ff', 'lat': 56.7784, 'lon': 53.1488, 'pop': 180},
        {'name': 'Рабочие и крестьяне', 'faction': 'Раб.крест.', 'color': '#595959', 'lat': 56.7761, 'lon': 53.1539, 'pop': 300},
        {'name': 'Территория баронов', 'faction': 'Бароны', 'color': '#00a197', 'lat': 56.7784, 'lon': 53.1590, 'pop': 450},
        {'name': 'Империя Пятерочки', 'faction': '5-ка', 'color': '#4345ed', 'lat': 56.7748, 'lon': 53.1631, 'pop': 1000},
        {'name': 'Студенты', 'faction': 'Студенты', 'color': '#79470e', 'lat': 56.7967, 'lon': 53.1542, 'pop': 350},
        {'name': 'Союз Шундов', 'faction': 'Шунды', 'color': '#03ad1b', 'lat': 56.8047, 'lon': 53.1409, 'pop': 700},
    ]
    
    for t in test_territories:
        territory = Territory(
            name=t['name'],
            faction=t['faction'],
            color=t['color'],
            population=t['pop'],
            center_lat=t['lat'],
            center_lon=t['lon'],
            wood=50 + t['pop'] // 10,
            food=50 + t['pop'] // 10,
            gold=20 + t['pop'] // 20,
            stone=10 + t['pop'] // 30,
            owner_id=None
        )
        db.add(territory)
    
    db.commit()
    print(f"✅ Создано {len(test_territories)} тестовых территорий")


def load_map_data():
    """Загружает данные из KML в базу (только если таблица пуста)"""
    from database import SessionLocal
    from models import Territory
    
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже данные
        count = db.query(Territory).count()
        if count > 0:
            print(f"🗺️ Карта уже загружена ({count} территорий)")
            return
        
        # Пробуем загрузить KML
        kml_path = 'data/Карта развалившегося пирогово_01-07-2025_18-11-29.kml'
        
        # Проверяем, существует ли файл
        if not os.path.exists(kml_path):
            print(f"⚠️ Файл {kml_path} не найден!")
            create_test_territories(db)
            return
        
        # Импортируем парсер
        try:
            from kml_parser import parse_kml
            territories = parse_kml(kml_path)
        except ImportError:
            print("⚠️ Модуль kml_parser не найден, создаём тестовые данные...")
            create_test_territories(db)
            return
        
        if not territories:
            print("⚠️ Не удалось распарсить KML, создаём тестовые данные...")
            create_test_territories(db)
            return
        
        for t in territories:
            territory = Territory(
                name=t.get('name', 'Без названия'),
                faction=t.get('faction', 'Неизвестно'),
                color=t.get('color', '#666666'),
                population=t.get('population', 100),
                center_lat=t.get('center', {}).get('lat', 0),
                center_lon=t.get('center', {}).get('lon', 0),
                wood=t.get('resources', {}).get('wood', 50),
                food=t.get('resources', {}).get('food', 50),
                gold=t.get('resources', {}).get('gold', 20),
                stone=10,
                owner_id=None
            )
            db.add(territory)
        
        db.commit()
        print(f"✅ Загружено {len(territories)} территорий из KML")
        
    except Exception as e:
        print(f"⚠️ Ошибка загрузки карты: {e}")
        db.rollback()
        create_test_territories(db)
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    """Действия при запуске"""
    create_admin_on_startup()
    load_map_data()
    start_bot()


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
# API ДЛЯ КАРТЫ
# ======================================================================

@app.get("/api/map-data")
def get_map_data(db: Session = Depends(get_db)):
    """Возвращает все территории для карты"""
    territories = db.query(Territory).all()
    return [
        {
            'id': t.id,
            'name': t.name,
            'faction': t.faction,
            'color': t.color,
            'population': t.population,
            'center_lat': t.center_lat,
            'center_lon': t.center_lon,
            'wood': t.wood,
            'food': t.food,
            'gold': t.gold,
            'stone': t.stone,
            'owner_id': t.owner_id,
            'owner_name': db.query(User).filter(User.id == t.owner_id).first().username if t.owner_id else None
        }
        for t in territories
    ]


@app.get("/api/territory/{territory_id}")
def get_territory(territory_id: int, db: Session = Depends(get_db)):
    """Информация о конкретной территории"""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        return {"error": "Территория не найдена"}
    
    buildings = db.query(BuildingOnMap).filter(BuildingOnMap.territory_id == territory_id).all()
    
    return {
        'id': territory.id,
        'name': territory.name,
        'faction': territory.faction,
        'color': territory.color,
        'population': territory.population,
        'wood': territory.wood,
        'food': territory.food,
        'gold': territory.gold,
        'stone': territory.stone,
        'owner_id': territory.owner_id,
        'buildings': [{'type': b.type, 'level': b.level} for b in buildings]
    }


@app.post("/api/build/{territory_id}")
def build_on_territory(
    territory_id: int,
    building_type: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Строит здание на территории"""
    territory = db.query(Territory).filter(Territory.id == territory_id).first()
    if not territory:
        return {"error": "Территория не найдена"}
    
    # Стоимость строительства
    costs = {
        'farm': {'wood': 30, 'gold': 10},
        'mine': {'wood': 40, 'gold': 20},
        'sawmill': {'wood': 20, 'gold': 5},
        'house': {'wood': 25, 'gold': 15},
        'barracks': {'wood': 50, 'gold': 30}
    }
    
    if building_type not in costs:
        return {"error": "Неизвестный тип здания"}
    
    cost = costs[building_type]
    
    if territory.wood < cost['wood'] or territory.gold < cost['gold']:
        return {"error": f"Недостаточно ресурсов! Нужно: дерево {cost['wood']}, золото {cost['gold']}"}
    
    # Тратим ресурсы
    territory.wood -= cost['wood']
    territory.gold -= cost['gold']
    
    # Создаем здание
    building = BuildingOnMap(
        territory_id=territory_id,
        type=building_type,
        level=1,
        owner_id=user.id
    )
    db.add(building)
    db.commit()
    
    # Добавляем в очередь
    queue = GameQueue(
        user_id=user.id,
        territory_id=territory_id,
        action_type='build',
        target_id=building.id,
        finished_at=datetime.now(timezone.utc) + timedelta(minutes=2)
    )
    db.add(queue)
    db.commit()
    
    return {
        'status': 'success',
        'message': f'Здание {building_type} построено!',
        'queue_time': '2 минуты'
    }


@app.get("/api/queue")
def get_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Очередь действий пользователя"""
    queue = db.query(GameQueue).filter(
        GameQueue.user_id == user.id,
        GameQueue.completed == False
    ).order_by(GameQueue.finished_at).all()
    
    return [
        {
            'id': q.id,
            'action_type': q.action_type,
            'finished_at': q.finished_at,
            'time_left': max(0, (q.finished_at - datetime.now(timezone.utc)).seconds // 60)
        }
        for q in queue
    ]


@app.get("/api/complete-queue")
def complete_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Завершает выполненные задания в очереди"""
    now = datetime.now(timezone.utc)
    queue_items = db.query(GameQueue).filter(
        GameQueue.user_id == user.id,
        GameQueue.completed == False,
        GameQueue.finished_at <= now
    ).all()
    
    for q in queue_items:
        q.completed = True
        # Если это строительство, можно добавить бонусы
        if q.action_type == 'build':
            building = db.query(BuildingOnMap).filter(BuildingOnMap.id == q.target_id).first()
            if building:
                building.level += 1
    
    db.commit()
    return {"completed": len(queue_items)}


# ======================================================================
# ОСНОВНЫЕ МАРШРУТЫ
# ======================================================================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/game")
def game_page(request: Request, user: User = Depends(get_optional_user)):
    """Страница игры (карта)"""
    if not user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "game.html", {"user": user})


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
    territories = db.query(Territory).all()
    return templates.TemplateResponse(
        request, 
        "admin.html", 
        {"user": user, "users": users, "territories": territories}
    )


@app.get("/create-admin-now")
def create_admin_now(db: Session = Depends(get_db)):
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


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="#c5a83d"/>
        <text x="50" y="65" font-size="40" text-anchor="middle" fill="#1a1f16">🏰</text>
    </svg>'''
    return Response(content=svg, media_type="image/svg+xml")


# ======================================================================
# АВТОРИЗАЦИЯ
# ======================================================================

@app.post("/register")
def register(
    username: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
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
def login(
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password):
        return RedirectResponse("/?detail=Неверный логин или пароль", status_code=303)
    
    token = create_token({"user_id": user.id, "role": user.role})
    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie(key="token", value=token, httponly=True, samesite="lax", max_age=24*60*60)
    return response


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
        return RedirectResponse("/profile?detail=Пароль должен быть не короче 6 символов", status_code=303)

    user.password = hash_password(new_password)
    db.commit()

    return RedirectResponse("/profile?msg=password_changed", status_code=303)


@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("token")
    return response


@app.get("/players")
def get_players(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    players = db.query(User).filter(User.id != user.id).all()
    return [
        {
            "id": p.id,
            "username": p.username,
            "email": p.email,
            "role": p.role,
            "created_at": p.created_at
        }
        for p in players
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


# ======================================================================
# ЗАПУСК
# ======================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)