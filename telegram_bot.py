import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL", "https://pirogovogame-production.up.railway.app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка для открытия игры"""
    keyboard = [[
        InlineKeyboardButton(
            "🎮 Открыть игру",
            web_app=WebAppInfo(url=f"{APP_URL}/game")
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏰 **Хроники Пирогово**\n\n"
        "Добро пожаловать в стратегическую игру!\n"
        "Нажми кнопку, чтобы начать.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"✅ Пользователь {update.effective_user.username} запустил бота")

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return
    
    logger.info(f"🤖 Запуск бота...")
    logger.info(f"🔗 Ссылка на игру: {APP_URL}")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        logger.info("✅ Бот готов к работе!")
        # drop_pending_updates=True очищает старые обновления
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise

if __name__ == "__main__":
    main()