from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Единственное место, где определяется путь к базе данных.
# Больше НИГДЕ (ни в main.py, ни в других файлах) не создаём свой engine/Base.
DATABASE_URL = "sqlite:///./db.sqlite3"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # нужно только для SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency для FastAPI: открывает сессию БД на время запроса
    и гарантированно закрывает её после.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
