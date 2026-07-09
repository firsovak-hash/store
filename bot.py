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
import fcntl
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from aiogram.filters import Command, CommandStart
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("store-bot")

dp = Dispatcher()

# Файловый лок держим открытым всю жизнь процесса (ОС снимет его при завершении)
_LOCK_FP = None


def acquire_single_instance_lock() -> bool:
    """Не даёт запустить второй экземпляр бота (иначе Telegram-конфликт getUpdates).

    Возвращает True, если лок захвачен. flock освобождается ОС автоматически,
    когда процесс завершается — «зависших» локов не остаётся.
    """
    global _LOCK_FP
    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot.lock")
    _LOCK_FP = open(lock_path, "w")
    try:
        fcntl.flock(_LOCK_FP, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _LOCK_FP.write(str(os.getpid()))
    _LOCK_FP.flush()
    return True


def _has_webapp() -> bool:
    return WEBAPP_URL.startswith("https://")


@dp.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """Показывает числовой ID — чтобы вписать его в ADMIN_CHAT_ID (куда падают заказы)."""
    uid = message.from_user.id
    await message.answer(
        "Твой Telegram ID: <code>{}</code>\n"
        "Chat ID: <code>{}</code>\n\n"
        "Впиши ID в <b>ADMIN_CHAT_ID</b> — на этот адрес бот будет слать заказы.".format(
            uid, message.chat.id
        ),
        parse_mode="HTML",
    )


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
    # drop_pending_updates — сбрасываем очередь, чтобы старт был чистым
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        log.error("BOT_TOKEN не задан в .env — добавь и запусти снова.")
        sys.exit(1)

    if not acquire_single_instance_lock():
        log.warning("Бот уже запущен в другом процессе — второй экземпляр не нужен, выхожу.")
        sys.exit(0)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен.")
    except TelegramConflictError:
        log.error("Конфликт с другим экземпляром бота (getUpdates). "
                  "Останови другой процесс и запусти снова.")
        sys.exit(0)
    except Exception as e:
        log.error("Бот остановлен из-за ошибки: %s: %s", type(e).__name__, e)
        sys.exit(1)
