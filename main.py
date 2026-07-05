import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from database.db import init_db
from handlers import start, menu, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8174608066:AAGBd7qUsQ0-OyNbjvug_ww6ocAwMIMGwOE"


async def main():

    # Init DB
    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(menu.router)

    logger.info("Bot ishga tushmoqda...")
    # MUHIM: drop_pending_updates=False bo'lishi shart!
    # Aks holda bot o'chib turgan vaqtda kelgan barcha eski
    # chat_join_request (zayavka) xabarlari Telegram tomonidan
    # butunlay yo'qotiladi va bazaga umuman tushmaydi.
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=[
        "message", "callback_query", "chat_join_request",
        "my_chat_member", "channel_post"
    ])


if __name__ == "__main__":
    asyncio.run(main())
