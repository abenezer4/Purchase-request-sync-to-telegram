from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.config import TELEGRAM_BOT_TOKEN
from src.bot.handlers import start, help_command, logout
from src.bot.search_handlers import search_command, pagination_handler, view_pr_handler
from src.api import router as api_router
import asyncio
import sys
import os

# Add project root to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Bot Application Global
bot_app = None

async def start_bot():
    """Start the bot polling."""
    global bot_app
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CommandHandler('help', help_command))
    bot_app.add_handler(CommandHandler('logout', logout))
    bot_app.add_handler(CommandHandler('find', search_command))
    bot_app.add_handler(CallbackQueryHandler(pagination_handler, pattern='^page:'))
    bot_app.add_handler(MessageHandler(filters.Regex(r'^/view_\d+'), view_pr_handler))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    print("Bot started polling.")

async def stop_bot():
    """Stop the bot."""
    global bot_app
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        print("Bot stopped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(start_bot())
    yield
    # Shutdown
    await stop_bot()

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
app.include_router(api_router)

# Static Files (Frontend)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
