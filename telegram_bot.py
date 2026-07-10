import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL", "https://ваш-сайт.up.railway.app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с кнопкой открытия игры"""
    keyboard = [[
        InlineKeyboardButton(
            "🎮 Открыть игру",
            web_app=WebAppInfo(url=f"{APP_URL}/game")
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏰 **Хроники Пирогово**\n\n"
        "Стратегический симулятор, где вместо стран — деревни, "
        "вместо танков — тракторы.\n\n"
        "Нажми кнопку, чтобы начать игру!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 **Как играть:**\n\n"
        "1. Нажми кнопку 'Открыть игру'\n"
        "2. Зарегистрируйся или войди\n"
        "3. Управляй своей деревней\n"
        "4. Строй здания и развивай экономику\n"
        "5. Завоевывай соседние деревни!\n\n"
        "Удачи, князь! 👑",
        parse_mode='Markdown'
    )

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("⚠️ BOT_TOKEN не установлен в переменных окружения!")
        return
    
    print(f"🤖 Запуск бота...")
    print(f"🔗 Ссылка на игру: {APP_URL}")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запускаем бота
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    main()