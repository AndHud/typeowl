"""Lesson generator for typing practice."""
import random
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from config import SUPPORTED_LANGUAGES, DIFFICULTY_LEVELS


@dataclass
class Lesson:
    """Typing lesson."""
    text: str
    language: str
    level: int
    target_chars: int
    include_special: bool
    metadata: Dict


class LessonGenerator:
    """Generates typing lessons for different languages and levels."""

    # Russian texts by difficulty
    RU_TEXTS = {
        1: [  # Basic words
            "мама папа брат сестра друг друг",
            "дом кот собака рыба птица зверь",
            "солнце луна звезда небо облако дождь",
            "стол стул окно дверь пол потолок",
            "книга ручка карандаш тетрадь сумка учебник",
            "вода хлеб молоко сок чай кофе сахар",
            "один два три четыре пять шесть семь",
            "красный синий зеленый желтый белый черный",
            "большой маленький высокий низкий длинный короткий",
            "идти бежать сидеть лежать стоять смотреть слушать",
        ],
        2: [  # Simple sentences
            "Привет, как дела? Всё хорошо, спасибо.",
            "Сегодня прекрасная погода, солнечный день.",
            "Я учусь печатать быстро и без ошибок.",
            "Мой друг живёт в большом красивом доме.",
            "Кошка спит на мягком ковре в углу.",
            "Мы идём в школу по зелёной улице.",
            "Мама готовит вкусный ужин для семьи.",
            "Папа читает интересную книгу вечером.",
            "Дети играют во дворе с мячом.",
            "Птицы поют песни на высоких деревьях.",
        ],
        3: [  # Longer sentences with punctuation
            "Программирование — это увлекательное занятие, которое требует терпения и внимания.",
            "Клавиатура является главным инструментом для ввода текста в компьютер.",
            "Регулярные тренировки помогают развить мышечную память и увеличить скорость печати.",
            "Русский язык богат на правила орфографии и пунктуации, которые нужно знать.",
            "Слепая печать — это навык набора текста без взгляда на клавиатуру.",
            "Правильная постановка пальцев на клавиатуре — залог быстрой и точной печати.",
            "Тренажёры для печати помогают отработать навык до автоматизма.",
            "Ошибки при наборе текста случаются у всех, главное — учиться на них.",
            "Скорость печати измеряется в знаках в минуту или словах в минуту.",
            "Точность не менее важна, чем скорость, при освоении слепой печати.",
        ],
        4: [  # Complex texts with numbers and special chars
            "В 2024 году популярность онлайн-обучения достигла новых высот: 85% студентов используют цифровые платформы.",
            "Скорость 120 знаков/мин считается профессиональной для секретарей и переводчиков.",
            "Клавиатуры типа mechanical (Cherry MX Red, Blue, Brown) стоят от 5 000 до 15 000 руб.",
            "Раскладка ЙЦУКЕН используется в России, а QWERTY — в англоязычных странах.",
            "Спецсимволы: @ # $ % ^ & * ( ) _ + - = { } [ ] | \\ : ; \" ' < > , . ? / ` ~",
            "Email: user.name@domain.com | Телефон: +7 (999) 123-45-67 | Сайт: https://example.ru",
            "Цены: 1 299 ₽, 2 499 ₽, 3 999 ₽ | Скидки: 10%, 20%, 30% | НДС: 20%",
            "Код: print('Hello, World!') | Формула: E = mc² | Дата: 31.12.2024",
            "Сочетания клавиш: Ctrl+C, Ctrl+V, Ctrl+Z, Ctrl+S, Alt+Tab, Win+D",
            "Валюты: $ € £ ¥ ₹ ₽ | Математика: ± × ÷ ≤ ≥ ≠ ∞ ∑ ∏ √ ∂ ∫",
        ],
        5: [  # Expert level - mixed content
            "Алгоритм быстрой сортировки (QuickSort) имеет среднюю сложность O(n log n) и используется во многих библиотеках.",
            "Регулярные выражения (regex) позволяют находить шаблоны в тексте: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "В Python словари (dict) — это хеш-таблицы с O(1) доступом: data = {'key': 'value', 'num': 42, 'list': [1, 2, 3]}",
            "Git команды: git commit -m \"feat: add typing lessons\" && git push origin main — базовый рабочий процесс.",
            "JSON формат: {\"user\": {\"id\": 123, \"name\": \"Иван\", \"skills\": [\"Python\", \"SQL\", \"Git\"]}, \"active\": true}",
            "CSS селекторы: .container > .row .col-md-6:nth-child(2) { display: flex; justify-content: center; }",
            "SQL запрос: SELECT u.name, COUNT(l.id) FROM users u LEFT JOIN lessons l ON u.id = l.user_id GROUP BY u.id HAVING COUNT(l.id) > 10;",
            "Markdown: **жирный**, *курсив*, `код`, [ссылка](url), ![картинка](img.png), > цитата, --- разделитель",
            "Docker: docker run -d --name bot -p 8080:8080 -v $(pwd)/data:/data myimage:latest",
            "Hotkeys: Ctrl+Shift+Esc (Task Manager), Win+V (Clipboard), Win+Shift+S (Screenshot), Alt+F4 (Close)",
        ]
    }

    # English texts by difficulty
    EN_TEXTS = {
        1: [  # Basic words
            "hello world how are you today",
            "cat dog bird fish horse mouse",
            "sun moon star sky cloud rain",
            "table chair window door floor roof",
            "book pen pencil paper bag school",
            "water bread milk juice tea coffee",
            "one two three four five six seven",
            "red blue green yellow white black",
            "big small high low long short",
            "go run sit lie stand look listen",
        ],
        2: [  # Simple sentences
            "Hello, how are you? I am fine, thanks.",
            "Today is a beautiful sunny day outside.",
            "I am learning to type fast without errors.",
            "My friend lives in a big beautiful house.",
            "The cat sleeps on the soft carpet corner.",
            "We go to school on the green street.",
            "Mom cooks delicious dinner for family.",
            "Dad reads an interesting book evening.",
            "Children play in the yard with ball.",
            "Birds sing songs on the high trees.",
        ],
        3: [  # Longer sentences with punctuation
            "Programming is an exciting activity that requires patience and attention.",
            "The keyboard is the main tool for entering text into a computer.",
            "Regular training helps develop muscle memory and increase typing speed.",
            "English has many spelling and punctuation rules that must be learned.",
            "Touch typing is the skill of typing text without looking at the keyboard.",
            "Proper finger placement on the keyboard is the key to fast and accurate typing.",
            "Typing tutors help practice the skill until it becomes automatic.",
            "Mistakes when typing happen to everyone, the main thing is to learn from them.",
            "Typing speed is measured in characters per minute or words per minute.",
            "Accuracy is no less important than speed when mastering touch typing.",
        ],
        4: [  # Complex texts with numbers and special chars
            "In 2024, online learning popularity reached new heights: 85% of students use digital platforms.",
            "Speed of 120 chars/min is considered professional for secretaries and translators.",
            "Mechanical keyboards (Cherry MX Red, Blue, Brown) cost from $50 to $150.",
            "The QWERTY layout is used in English-speaking countries, JCUKEN in Russia.",
            "Special chars: @ # $ % ^ & * ( ) _ + - = { } [ ] | \\ : ; \" ' < > , . ? / ` ~",
            "Email: user.name@domain.com | Phone: +1 (555) 123-4567 | Site: https://example.com",
            "Prices: $12.99, $24.99, $39.99 | Discounts: 10%, 20%, 30% | Tax: 8.25%",
            "Code: print('Hello, World!') | Formula: E = mc² | Date: 12/31/2024",
            "Shortcuts: Ctrl+C, Ctrl+V, Ctrl+Z, Ctrl+S, Alt+Tab, Win+D",
            "Currencies: $ € £ ¥ ₹ ₽ | Math: ± × ÷ ≤ ≥ ≠ ∞ ∑ ∏ √ ∂ ∫",
        ],
        5: [  # Expert level - mixed content
            "The QuickSort algorithm has average complexity O(n log n) and is used in many standard libraries.",
            "Regular expressions (regex) allow finding patterns in text: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "In Python, dictionaries (dict) are hash tables with O(1) access: data = {'key': 'value', 'num': 42, 'list': [1, 2, 3]}",
            "Git commands: git commit -m \"feat: add typing lessons\" && git push origin main — basic workflow.",
            "JSON format: {\"user\": {\"id\": 123, \"name\": \"John\", \"skills\": [\"Python\", \"SQL\", \"Git\"]}, \"active\": true}",
            "CSS selectors: .container > .row .col-md-6:nth-child(2) { display: flex; justify-content: center; }",
            "SQL query: SELECT u.name, COUNT(l.id) FROM users u LEFT JOIN lessons l ON u.id = l.user_id GROUP BY u.id HAVING COUNT(l.id) > 10;",
            "Markdown: **bold**, *italic*, `code`, [link](url), ![image](img.png), > quote, --- separator",
            "Docker: docker run -d --name bot -p 8080:8080 -v $(pwd)/data:/data myimage:latest",
            "Hotkeys: Ctrl+Shift+Esc (Task Manager), Win+V (Clipboard), Win+Shift+S (Screenshot), Alt+F4 (Close)",
        ]
    }

    # Special characters for each language
    SPECIAL_CHARS = {
        "ru": ".,!?-–—()[]{}«»\"':;/@#№%&*+=_\\|<>^~`",
        "en": ".,!?-–—()[]{}«»\"':;/@#%&*+=_\\|<>^~`"
    }

    def __init__(self):
        self.lesson_cache = {}

    def get_lesson(self, language: str, level: int, include_special: bool = None) -> Lesson:
        """Generate a lesson for the given language and level."""
        if language not in SUPPORTED_LANGUAGES:
            language = "ru"

        if level not in DIFFICULTY_LEVELS:
            level = 1

        level_config = DIFFICULTY_LEVELS[level]
        target_chars = level_config["chars"]
        words_count = level_config["words"]

        if include_special is None:
            include_special = level_config["include_special"]

        # Get texts for the language and level
        texts = self.RU_TEXTS if language == "ru" else self.EN_TEXTS
        level_texts = texts.get(level, texts[1])

        # Build lesson text
        lesson_text = self._build_lesson_text(
            level_texts, target_chars, words_count,
            include_special, language
        )

        return Lesson(
            text=lesson_text,
            language=language,
            level=level,
            target_chars=target_chars,
            include_special=include_special,
            metadata={
                "words_count": words_count,
                "source_level": level
            }
        )

    def _build_lesson_text(self, texts: List[str], target_chars: int,
                           words_count: int, include_special: bool, language: str) -> str:
        """Build lesson text from available texts."""
        # Shuffle texts for variety
        available_texts = texts.copy()
        random.shuffle(available_texts)

        result = []
        current_length = 0

        for text in available_texts:
            if current_length + len(text) > target_chars * 1.5:
                break
            result.append(text)
            current_length += len(text) + 1  # +1 for space

        lesson = " ".join(result)

        # Trim to target length
        if len(lesson) > target_chars:
            lesson = lesson[:target_chars].rsplit(' ', 1)[0]

        # Add special characters if needed
        if include_special and len(lesson) < target_chars:
            specials = self.SPECIAL_CHARS.get(language, "")
            special_sample = " ".join(random.sample(list(specials), min(10, len(specials))))
            lesson += " " + special_sample

        return lesson.strip()

    def get_random_lesson(self, languages: List[str], level: int) -> Lesson:
        """Get a random lesson from selected languages."""
        language = random.choice(languages)
        return self.get_lesson(language, level)

    def get_practice_text(self, language: str, length: int = 200) -> str:
        """Get a practice text of specific length."""
        texts = self.RU_TEXTS if language == "ru" else self.EN_TEXTS
        all_texts = []
        for level_texts in texts.values():
            all_texts.extend(level_texts)

        random.shuffle(all_texts)
        result = []
        current_length = 0

        for text in all_texts:
            if current_length + len(text) > length:
                break
            result.append(text)
            current_length += len(text) + 1

        practice = " ".join(result)
        if len(practice) > length:
            practice = practice[:length].rsplit(' ', 1)[0]

        return practice


# Keyboard layout helpers
KEYBOARD_LAYOUTS = {
    "ru": {
        "rows": [
            "ё1234567890-=",
            "йцукенгшщзхъ",
            "фывапролджэ",
            "ячсмитьбю."
        ],
        "shift_rows": [
            "Ё!\"№;%:?*()_+",
            "ЙЦУКЕНГШЩЗХЪ",
            "ФЫВАПРОЛДЖЭ",
            "ЯЧСМИТЬБЮ,"
        ],
        "finger_map": {
            # Left hand
            "ф": "left_pinky", "ы": "left_ring", "в": "left_middle", "а": "left_index",
            "п": "left_index", "р": "left_index", "о": "right_index", "л": "right_index",
            "д": "right_middle", "ж": "right_ring", "э": "right_pinky",
            "я": "left_pinky", "ч": "left_ring", "с": "left_middle", "м": "left_index",
            "и": "right_index", "т": "right_index", "ь": "right_middle", "б": "right_ring", "ю": "right_pinky",
            "й": "left_pinky", "ц": "left_ring", "у": "left_middle", "к": "left_index",
            "е": "left_index", "н": "right_index", "г": "right_index", "ш": "right_middle",
            "щ": "right_ring", "з": "right_pinky", "х": "right_pinky", "ъ": "right_pinky",
        }
    },
    "en": {
        "rows": [
            "`1234567890-=",
            "qwertyuiop[]\\",
            "asdfghjkl;'",
            "zxcvbnm,./"
        ],
        "shift_rows": [
            "~!@#$%^&*()_+",
            "QWERTYUIOP{}|",
            "ASDFGHJKL:\"",
            "ZXCVBNM<>?"
        ],
        "finger_map": {
            # Left hand
            "a": "left_pinky", "s": "left_ring", "d": "left_middle", "f": "left_index",
            "g": "left_index", "h": "right_index", "j": "right_index", "k": "right_middle",
            "l": "right_ring", ";": "right_pinky", "'": "right_pinky",
            "z": "left_pinky", "x": "left_ring", "c": "left_middle", "v": "left_index",
            "b": "left_index", "n": "right_index", "m": "right_index", ",": "right_middle",
            ".": "right_ring", "/": "right_pinky",
            "q": "left_pinky", "w": "left_ring", "e": "left_middle", "r": "left_index",
            "t": "left_index", "y": "right_index", "u": "right_index", "i": "right_middle",
            "o": "right_ring", "p": "right_pinky", "[": "right_pinky", "]": "right_pinky", "\\": "right_pinky",
        }
    }
}


def get_key_finger(key: str, language: str) -> str:
    """Get which finger should press a key."""
    key = key.lower()
    finger_map = KEYBOARD_LAYOUTS.get(language, {}).get("finger_map", {})
    return finger_map.get(key, "unknown")


def get_keyboard_visual(language: str, highlight_keys: str = "") -> str:
    """Get visual keyboard representation."""
    layout = KEYBOARD_LAYOUTS.get(language, KEYBOARD_LAYOUTS["en"])
    highlight_set = set(highlight_keys.lower())

    rows = []
    for row in layout["rows"]:
        row_keys = []
        for key in row:
            if key in highlight_set:
                row_keys.append(f"[{key.upper()}]")
            else:
                row_keys.append(f" {key} ")
        rows.append(" ".join(row_keys))

    return "\n".join(rows)