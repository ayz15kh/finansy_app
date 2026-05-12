import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = os.getenv("DB_NAME", "finance.db")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ayz15kh.github.io/finansy_app")

if not API_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Проверь файл .env")