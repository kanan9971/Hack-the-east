import os
from dotenv import load_dotenv

load_dotenv()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.1"

ALLOWED_ORIGINS = [
    "chrome-extension://*",
    "http://localhost:*",
    "*",
]
