"""Web server for Duolingo-style typing interface."""
import asyncio
import json
import os
import random
import time
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict, field

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

# Import bot modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import SUPPORTED_LANGUAGES, DIFFICULTY_LEVELS, LESSON_SETTINGS
from database import DatabaseManager, User, LessonResult
from lessons import LessonGenerator, get_key_finger, KEYBOARD_LAYOUTS

# Global instances
db = DatabaseManager("typing_bot.db")
lesson_generator = LessonGenerator()

# Active web sessions
web_sessions: Dict[str, "WebTypingSession"] = {}


@dataclass
class WebTypingSession:
    """Web typing session data."""
    session_id: str
    user_id: int
    lesson_text: str
    language: str
    level: int
    start_time: float
    chars_typed: int = 0
    correct_chars: int = 0
    errors: list = field(default_factory=list)
    current_position: int = 0
    hearts: int = 5
    xp_earned: int = 0
    perfect_chars: int = 0
    keystrokes: list = field(default_factory=list)  # for replay/analysis


# ==================== KEYBOARD LAYOUTS ====================

KEYBOARD_LAYOUTS_WEB = {
    "ru": {
        "name": "Русская (ЙЦУКЕН)",
        "rows": [
            ["ё", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
            ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ"],
            ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
            ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "."],
            [" ", " "]  # spacebar
        ],
        "shift_rows": [
            ["Ё", "!", "\"", "№", ";", "%", ":", "?", "*", "(", ")", "_", "+"],
            ["Й", "Ц", "У", "К", "Е", "Н", "Г", "Ш", "Щ", "З", "Х", "Ъ"],
            ["Ф", "Ы", "В", "А", "П", "Р", "О", "Л", "Д", "Ж", "Э"],
            ["Я", "Ч", "С", "М", "И", "Т", "Ь", "Б", "Ю", ","],
            [" ", " "]
        ],
        "finger_map": {
            "ф": "lp", "ы": "lr", "в": "lm", "а": "li", "п": "li", "р": "li",
            "о": "ri", "л": "ri", "д": "rm", "ж": "rr", "э": "rp",
            "я": "lp", "ч": "lr", "с": "lm", "м": "li", "и": "ri", "т": "ri",
            "ь": "rm", "б": "rr", "ю": "rp", ".": "rp",
            "й": "lp", "ц": "lr", "у": "lm", "к": "li", "е": "li", "н": "ri",
            "г": "ri", "ш": "rm", "щ": "rr", "з": "rp", "х": "rp", "ъ": "rp",
            "ё": "lp", "1": "lp", "2": "lr", "3": "lm", "4": "li", "5": "li",
            "6": "ri", "7": "ri", "8": "rm", "9": "rr", "0": "rp", "-": "rp", "=": "rp",
        },
        "finger_names": {
            "lp": "Левый мизинец", "lr": "Левый безымянный", "lm": "Левый средний",
            "li": "Левый указательный", "ri": "Правый указательный", "rm": "Правый средний",
            "rr": "Правый безымянный", "rp": "Правый мизинец"
        }
    },
    "en": {
        "name": "English (QWERTY)",
        "rows": [
            ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"],
            ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"],
            [" ", " "]
        ],
        "shift_rows": [
            ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+"],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\""],
            ["Z", "X", "C", "V", "B", "N", "M", "<", ">", "?"],
            [" ", " "]
        ],
        "finger_map": {
            "a": "lp", "s": "lr", "d": "lm", "f": "li", "g": "li", "h": "ri",
            "j": "ri", "k": "rm", "l": "rr", ";": "rp", "'": "rp",
            "z": "lp", "x": "lr", "c": "lm", "v": "li", "b": "li", "n": "ri",
            "m": "ri", ",": "rm", ".": "rr", "/": "rp",
            "q": "lp", "w": "lr", "e": "lm", "r": "li", "t": "li", "y": "ri",
            "u": "ri", "i": "rm", "o": "rr", "p": "rp", "[": "rp", "]": "rp", "\\": "rp",
            "`": "lp", "1": "lp", "2": "lr", "3": "lm", "4": "li", "5": "li",
            "6": "ri", "7": "ri", "8": "rm", "9": "rr", "0": "rp", "-": "rp", "=": "rp",
        },
        "finger_names": {
            "lp": "Left Pinky", "lr": "Left Ring", "lm": "Left Middle",
            "li": "Left Index", "ri": "Right Index", "rm": "Right Middle",
            "rr": "Right Ring", "rp": "Right Pinky"
        }
    }
}


# ==================== ROUTES ====================

async def index(request: Request) -> Response:
    """Serve the main typing interface."""
    with open(os.path.join(os.path.dirname(__file__), "web", "index.html"), "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")


async def api_get_lesson(request: Request) -> Response:
    """Get a new lesson for the user."""
    data = await request.json()
    user_id = data.get("user_id", 1)
    language = data.get("language", "ru")
    level = data.get("level", 1)

    # Get or create user
    db_user = db.get_or_create_user(user_id=user_id)

    # Check level access
    if level > db_user.current_level:
        return web.json_response({"error": "Level locked"}, status=403)

    # Generate lesson
    lesson = lesson_generator.get_lesson(language, level)

    # Create session
    session_id = f"{user_id}_{int(time.time() * 1000)}"
    session = WebTypingSession(
        session_id=session_id,
        user_id=user_id,
        lesson_text=lesson.text,
        language=language,
        level=level,
        start_time=time.time(),
        hearts=5
    )
    web_sessions[session_id] = session

    # Return lesson data + keyboard layout
    layout = KEYBOARD_LAYOUTS_WEB[language]

    return web.json_response({
        "session_id": session_id,
        "lesson_text": lesson.text,
        "language": language,
        "level": level,
        "level_name": DIFFICULTY_LEVELS[level]["name"],
        "language_name": SUPPORTED_LANGUAGES[language]["name"],
        "language_flag": SUPPORTED_LANGUAGES[language]["flag"],
        "keyboard_layout": layout,
        "hearts": 5,
        "max_hearts": 5
    })


async def api_keystroke(request: Request) -> Response:
    """Process a keystroke from the web interface."""
    data = await request.json()
    session_id = data.get("session_id")
    char = data.get("char", "")
    timestamp = data.get("timestamp", time.time())

    if session_id not in web_sessions:
        return web.json_response({"error": "Session not found"}, status=404)

    session = web_sessions[session_id]

    if session.current_position >= len(session.lesson_text):
        return web.json_response({"complete": True})

    expected_char = session.lesson_text[session.current_position]
    is_correct = char == expected_char

    # Record keystroke
    keystroke = {
        "char": char,
        "expected": expected_char,
        "position": session.current_position,
        "correct": is_correct,
        "timestamp": timestamp,
        "time_since_start": timestamp - session.start_time
    }
    session.keystrokes.append(keystroke)

    if is_correct:
        session.correct_chars += 1
        session.perfect_chars += 1
        session.xp_earned += 2
    else:
        session.errors.append(session.current_position)
        session.perfect_chars = 0
        session.hearts -= 1

    session.chars_typed += 1
    session.current_position += 1

    # Check completion
    complete = session.current_position >= len(session.lesson_text)
    failed = session.hearts <= 0

    # Calculate current stats
    elapsed = timestamp - session.start_time
    wpm = (session.correct_chars / 5) / (elapsed / 60) if elapsed > 0 else 0
    accuracy = (session.correct_chars / session.chars_typed * 100) if session.chars_typed > 0 else 100

    response = {
        "correct": is_correct,
        "position": session.current_position,
        "total": len(session.lesson_text),
        "progress": int((session.current_position / len(session.lesson_text)) * 100),
        "hearts": max(0, session.hearts),
        "wpm": round(wpm, 1),
        "accuracy": round(accuracy, 1),
        "xp_earned": session.xp_earned,
        "complete": complete,
        "failed": failed,
        "current_char": session.lesson_text[session.current_position] if session.current_position < len(session.lesson_text) else None,
        "next_chars": session.lesson_text[session.current_position:session.current_position+3] if session.current_position < len(session.lesson_text) else ""
    }

    if complete or failed:
        # Save to database
        await save_lesson_result(session)
        del web_sessions[session_id]
        response["final"] = True

    return web.json_response(response)


async def api_backspace(request: Request) -> Response:
    """Handle backspace - go back one position."""
    data = await request.json()
    session_id = data.get("session_id")

    if session_id not in web_sessions:
        return web.json_response({"error": "Session not found"}, status=404)

    session = web_sessions[session_id]

    if session.current_position > 0:
        session.current_position -= 1
        # Remove last keystroke
        if session.keystrokes:
            last = session.keystrokes.pop()
            if last["correct"]:
                session.correct_chars -= 1
            else:
                if session.current_position in session.errors:
                    session.errors.remove(session.current_position)
                session.hearts = min(5, session.hearts + 1)
            session.chars_typed -= 1

    return web.json_response({
        "position": session.current_position,
        "hearts": session.hearts,
        "chars_typed": session.chars_typed,
        "correct_chars": session.correct_chars
    })


async def save_lesson_result(session: WebTypingSession):
    """Save lesson result to database."""
    elapsed = time.time() - session.start_time
    time_spent = max(1, int(elapsed))

    wpm = (session.correct_chars / 5) / (time_spent / 60) if time_spent > 0 else 0
    accuracy = (session.correct_chars / session.chars_typed * 100) if session.chars_typed > 0 else 0

    result = LessonResult(
        user_id=session.user_id,
        language=session.language,
        level=session.level,
        chars_typed=session.chars_typed,
        correct_chars=session.correct_chars,
        time_spent=time_spent,
        wpm=round(wpm, 1),
        accuracy=round(accuracy, 1),
        errors=json.dumps(session.errors),
        completed=session.hearts > 0
    )
    db.save_lesson_result(result)

    # Update user stats
    db_user = db.get_or_create_user(user_id=session.user_id)
    db_user.total_chars_typed += session.chars_typed
    db_user.total_correct_chars += session.correct_chars
    db_user.total_time_spent += time_spent
    db_user.lessons_completed += 1
    db_user.best_wpm = max(db_user.best_wpm, wpm)
    db_user.best_accuracy = max(db_user.best_accuracy, accuracy)

    if db_user.total_chars_typed >= db_user.current_level * LESSON_SETTINGS["chars_per_level"]:
        if db_user.current_level < max(DIFFICULTY_LEVELS.keys()):
            db_user.current_level += 1

    db.update_user(db_user)
    db.update_daily_stats(
        session.user_id, session.chars_typed, session.correct_chars,
        time_spent, wpm, accuracy
    )


async def api_user_stats(request: Request) -> Response:
    """Get user statistics."""
    data = await request.json()
    user_id = data.get("user_id", 1)

    db_user = db.get_or_create_user(user_id=user_id)
    stats = db.get_user_stats(user_id)

    total_xp = db_user.lessons_completed * 50 + db_user.total_correct_chars * 2

    return web.json_response({
        "user_id": user_id,
        "username": db_user.first_name or f"User{user_id}",
        "level": db_user.current_level,
        "level_name": DIFFICULTY_LEVELS[db_user.current_level]["name"],
        "xp": total_xp,
        "streak": db_user.current_streak,
        "max_streak": db_user.max_streak,
        "lessons_completed": db_user.lessons_completed,
        "best_wpm": db_user.best_wpm,
        "best_accuracy": db_user.best_accuracy,
        "total_chars": db_user.total_chars_typed,
        "selected_languages": db_user.selected_langs_list,
        "recent_lessons": stats.get("recent", [])[:10]
    })


async def api_leaderboard(request: Request) -> Response:
    """Get leaderboard."""
    leaders = db.get_leaderboard(10)
    return web.json_response({
        "leaders": [
            {
                "rank": i + 1,
                "name": u['first_name'] or u['username'] or f"User{u['user_id']}",
                "wpm": u['best_wpm'],
                "accuracy": u['best_accuracy'],
                "lessons": u['lessons_completed']
            }
            for i, u in enumerate(leaders)
        ]
    })


# ==================== STATIC FILES ====================

async def static_file(request: Request) -> Response:
    """Serve static files (CSS, JS)."""
    path = request.match_info.get('path', '')
    filepath = os.path.join(os.path.dirname(__file__), "web", path)

    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return web.Response(status=404)

    # Determine content type
    if filepath.endswith('.css'):
        content_type = 'text/css'
    elif filepath.endswith('.js'):
        content_type = 'application/javascript'
    elif filepath.endswith('.html'):
        content_type = 'text/html'
    else:
        content_type = 'application/octet-stream'

    with open(filepath, 'rb') as f:
        return web.Response(body=f.read(), content_type=content_type)


def create_app():
    """Create the web application."""
    app = web.Application()

    # Routes
    app.router.add_get('/', index)
    app.router.add_get('/web/{path:.*}', static_file)
    app.router.add_post('/api/lesson', api_get_lesson)
    app.router.add_post('/api/keystroke', api_keystroke)
    app.router.add_post('/api/backspace', api_backspace)
    app.router.add_post('/api/stats', api_user_stats)
    app.router.add_post('/api/leaderboard', api_leaderboard)

    return app


async def start_web_server(host='0.0.0.0', port=None):
    """Start the web server."""
    if port is None:
        port = int(os.environ.get('PORT', 8080))
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"🌐 Web server started at http://{host}:{port}")
    return runner


if __name__ == "__main__":
    import os
    async def main():
        runner = await start_web_server()
        # Keep running forever
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await runner.cleanup()

    asyncio.run(main())