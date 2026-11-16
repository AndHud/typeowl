"""Configuration for the Typing Bot."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    """Bot configuration settings."""
    token: str
    db_path: str = "typing_bot.db"
    admin_ids: list = None

    def __post_init__(self):
        if self.admin_ids is None:
            self.admin_ids = []


# Default configuration - replace with your bot token
# Get token from @BotFather in Telegram
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9100945927:AAEXbPKVDn65CF2xA-3vygpX-AWdsESneZE")

config = BotConfig(
    token=BOT_TOKEN,
    db_path="typing_bot.db"
)

# Lesson settings
LESSON_SETTINGS = {
    "min_lesson_length": 50,  # minimum characters per lesson
    "max_lesson_length": 500,  # maximum characters per lesson
    "chars_per_level": 100,  # characters to unlock next level
    "wpm_threshold": {
        "beginner": 20,
        "intermediate": 40,
        "advanced": 60,
        "expert": 80
    }
}

# Supported languages
SUPPORTED_LANGUAGES = {
    "ru": {
        "name": "Русский",
        "flag": "🇷🇺",
        "alphabet": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "special_chars": ".,!?-–—()[]{}«»\"':;/@#№%&*+=_\\|<>^~`",
        "keyboard_layout": "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ",
        "common_words": [
            "привет", "мир", "как", "дела", "спасибо", "пожалуйста",
            "хорошо", "плохо", "да", "нет", "может", "быть",
            "время", "день", "ночь", "работа", "дом", "школа",
            "учеба", "друг", "семья", "любовь", "счастье", "успех"
        ]
    },
    "en": {
        "name": "English",
        "flag": "🇺🇸",
        "alphabet": "abcdefghijklmnopqrstuvwxyz",
        "special_chars": ".,!?-–—()[]{}«»\"':;/@#%&*+=_\\|<>^~`",
        "keyboard_layout": "QWERTYUIOPASDFGHJKLZXCVBNM",
        "common_words": [
            "hello", "world", "how", "are", "you", "thank", "you",
            "good", "bad", "yes", "no", "maybe", "be", "time",
            "day", "night", "work", "home", "school", "study",
            "friend", "family", "love", "happiness", "success", "life"
        ]
    }
}

# Difficulty levels
DIFFICULTY_LEVELS = {
    1: {"name": "Новичок", "chars": 30, "words": 5, "include_special": False},
    2: {"name": "Начинающий", "chars": 50, "words": 10, "include_special": False},
    3: {"name": "Любитель", "chars": 80, "words": 15, "include_special": True},
    4: {"name": "Профи", "chars": 120, "words": 20, "include_special": True},
    5: {"name": "Мастер", "chars": 200, "words": 30, "include_special": True},
}