#!/bin/bash
# Создаем таблицы при старте
python -c "from database import engine, Base; from models import User; Base.metadata.create_all(bind=engine)"
# Запускаем приложение
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}