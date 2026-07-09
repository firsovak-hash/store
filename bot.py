"""Telegram-бот для магазина STORE by Sasha.

Открывает Flask-магазин как Telegram Mini App.
Токен и URL берутся из .env (BOT_TOKEN, WEBAPP_URL).

Запуск локально:
    python3 bot.py

WEBAPP_URL должен быть HTTPS (Telegram не открывает http/localhost в WebApp).
Для локального теста поднимаем cloudflared-туннель на Flask (:8080) и кладём
полученный https://...trycloudflare.com в .env → WEBAPP_URL.
"""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = (os.getenv("WEBAPP_URL") or "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("store-bot")

dp = Dispatcher()


def _has_webapp() -> bool:
    return WEBAPP_URL.startswith("https://")


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if _has_webapp():
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🛍 Открыть магазин",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]]
        )
        await message.answer(
            "Добро пожаловать в <b>STORE by Sasha</b> 🖤\n"
            "Нажми кнопку ниже, чтобы открыть магазин.",
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "Бот запущен, но WEBAPP_URL пока не задан (нужен HTTPS-адрес).\n"
            "Добавь его в .env и перезапусти бота."
        )


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    me = await bot.get_me()

    if _has_webapp():
        # Кнопка «Меню» слева от поля ввода тоже открывает Mini App
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Магазин",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )
        log.info("Menu-button настроен на %s", WEBAPP_URL)
    else:
        log.warning("WEBAPP_URL не задан или не HTTPS — кнопки WebApp отключены.")

    log.info("Бот @%s запущен. Жду сообщений (/start)…", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
