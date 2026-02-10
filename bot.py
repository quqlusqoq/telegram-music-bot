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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Привет! 👋 Пришли ссылку на YouTube или Spotify — пришлю MP3 🎵")


def get_spotify_title(url: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=10).text

        title_match = re.search(r'<title>(.*?)</title>', html)
        if not title_match:
            return None

        title = title_match.group(1)
        title = title.replace(" | Spotify", "").strip()
        return title

    except Exception as e:
        print("Ошибка получения названия из Spotify:", e)
        return None


def download_audio(url: str) -> str | None:
    # Если это Spotify — получаем название трека
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
        "quiet": True,
        "js_runtimes": {"node": {}},
        "remote_components": ["ejs:github"],
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
                if not info["entries"]:
                    print("Ничего не найдено на YouTube")
                    return None
                info = info["entries"][0]

            filename = ydl.prepare_filename(info)
            return str(Path(filename).with_suffix(".mp3"))

    except Exception as e:
        print("Ошибка загрузки:", e)
        return None


@router.message()
async def handle_link(message: Message):
    url = message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url and "spotify.com" not in url:
        await message.answer("Пришли ссылку на YouTube или Spotify 🎵")
        return

    await message.answer("Скачиваю аудио, подожди ⏳")

    try:
        file_path = download_audio(url)  # скачивание через yt-dlp

        from aiogram.types import FSInputFile  # 👈 ВСТАВИТЬ СЮДА
        audio = FSInputFile(file_path)         # 👈 И СЮДА

        await message.answer_audio(            # 👈 ЭТО УЖЕ БЫЛО, но с заменой audio=
            audio=audio,
            title=Path(file_path).stem
        )

    except Exception as e:
        await message.answer(f"Ошибка загрузки: {e}")


    audio = FSInputFile(file_path)
    await message.answer_audio(audio=audio, title=Path(file_path).stem)

    os.remove(file_path)
    await wait_msg.delete()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
