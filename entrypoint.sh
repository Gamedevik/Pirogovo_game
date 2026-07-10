#!/bin/bash

echo "🚀 Запуск Хроники Пирогово..."
echo "📋 Переменные окружения:"
echo "PORT: ${PORT:-не задан}"
echo "DATABASE_URL: ${DATABASE_URL:-не задан}"

# Определяем порт
if [ -z "$PORT" ]; then
    echo "⚠️ PORT не задан, использую 8080"
    PORT=8080
fi

echo "🌐 Слушаем на порту: $PORT"
echo "📦 Запуск Uvicorn..."

exec uvicorn main:app --host 0.0.0.0 --port $PORT