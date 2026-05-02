import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "bot_club.db")

T_BANK_TERMINAL_KEY = os.getenv("T_BANK_TERMINAL_KEY", "")
T_BANK_SECRET = os.getenv("T_BANK_SECRET", "")
PAYMENT_TEST_MODE = os.getenv("PAYMENT_TEST_MODE", "True").lower() in ("true", "1", "yes")

BASE_PRICE = int(os.getenv("BASE_PRICE", "1000"))

# Subscription periods (months)
SUBSCRIPTION_PERIODS = {
    1: {"months": 1, "label": "1 месяц", "multiplier": 1},
    3: {"months": 3, "label": "3 месяца", "multiplier": 3},
    6: {"months": 6, "label": "6 месяцев", "multiplier": 6},
    9: {"months": 9, "label": "9 месяцев", "multiplier": 9},
    12: {"months": 12, "label": "12 месяцев", "multiplier": 12},
}
