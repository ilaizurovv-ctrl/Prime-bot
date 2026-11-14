import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import settings
from app.db import init_db
from app.handlers.start import router as start_router
from app.handlers.deals import router as deals_router
from app.handlers.admin import router as admin_router

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(deals_router)
    dp.include_router(admin_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
