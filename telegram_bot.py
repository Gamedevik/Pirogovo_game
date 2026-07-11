import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL", "https://pirogovogame-production.up.railway.app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "🎮 Открыть игру",
            web_app=WebAppInfo(url=f"{APP_URL}/game")
        )
    ]]
    await update.message.reply_text(
        "🏰 **Хроники Пирогово**\n\n"
        "Добро пожаловать!\n"
        "Нажми кнопку, чтобы начать.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен")
        return
    
    logger.info("🤖 Запуск бота...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    logger.info("✅ Бот готов!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()