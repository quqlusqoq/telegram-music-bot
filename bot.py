import logging
import asyncio
import re
import requests
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from dotenv import load_dotenv
import yt_dlp

# Логи (ОЧЕНЬ помогают на Railway)
logging.basicConfig(level=logging.INFO)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)  # Подключаем роутер

DOWNLOAD_DIR = Path("/tmp")  # Railway разрешает запись только во временную папку


# ▶ Старт
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Привет! 👋 Пришли ссылку на YouTube или Spotify — пришлю MP3 🎵")


# ▶ Получаем название трека из Spotify страницы
def get_spotify_title(url: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=10).text

        title_match = re.search(r"<title>(.*?)</title>", html)
        if not title_match:
            return None

        title = title_match.group(1)
        title = title.replace(" | Spotify", "").strip()
        return title

    except Exception as e:
        print("Ошибка получения названия из Spotify:", e)
        return None


# ▶ Скачивание аудио через yt-dlp
def download_audio(url: str) -> str | None:
    if "spotify.com" in url:
        title = get_spotify_title(url)
        if not title:
            print("Не удалось получить название трека из Spotify")
            return None
        url = f"ytsearch1:{title} audio"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "nocheckcertificate": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if "entries" in info:
                info = info["entries"][0]

            filename = ydl.prepare_filename(info)
            return str(Path(filename).with_suffix(".mp3"))

    except Exception as e:
        print("Ошибка загрузки:", e)
        return None


# ▶ Обработка ссылок
@router.message()
async def handle_link(message: Message):
    url = message.text.strip()

    if not any(x in url for x in ["youtube.com", "youtu.be", "spotify.com"]):
        await message.answer("Пришли ссылку на YouTube или Spotify 🎵")
        return

    wait_msg = await message.answer("Скачиваю аудио, подожди ⏳")

    try:
        print(f"Downloading: {url}")
        file_path = download_audio(url)

        if not file_path or not os.path.exists(file_path):
            await message.answer("Не удалось скачать аудио 😢")
            return

        audio = FSInputFile(file_path)
        await message.answer_audio(audio=audio, title=Path(file_path).stem)

        os.remove(file_path)
        await wait_msg.delete()

    except Exception as e:
        print("ERROR:", e)
        await message.answer(f"Ошибка загрузки: {e}")


# ▶ Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
