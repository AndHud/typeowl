"""Database models and manager for the Typing Bot."""
import sqlite3
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading


@dataclass
class User:
    """User model."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "ru"
    selected_languages: str = '["ru"]'  # JSON array
    current_level: int = 1
    total_chars_typed: int = 0
    total_correct_chars: int = 0
    total_time_spent: int = 0  # seconds
    lessons_completed: int = 0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0
    current_streak: int = 0
    max_streak: int = 0
    last_active_date: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    @property
    def selected_langs_list(self) -> List[str]:
        try:
            return json.loads(self.selected_languages)
        except:
            return ["ru"]

    @selected_langs_list.setter
    def selected_langs_list(self, value: List[str]):
        self.selected_languages = json.dumps(value)


@dataclass
class LessonResult:
    """Lesson result model."""
    id: Optional[int] = None
    user_id: int = 0
    language: str = "ru"
    level: int = 1
    chars_typed: int = 0
    correct_chars: int = 0
    time_spent: int = 0  # seconds
    wpm: float = 0.0
    accuracy: float = 0.0
    errors: str = "[]"  # JSON array of error positions
    completed: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class DailyStats:
    """Daily statistics model."""
    id: Optional[int] = None
    user_id: int = 0
    stat_date: str = ""
    chars_typed: int = 0
    correct_chars: int = 0
    time_spent: int = 0
    lessons_completed: int = 0
    avg_wpm: float = 0.0
    avg_accuracy: float = 0.0


class DatabaseManager:
    """Database manager for the typing bot."""

    def __init__(self, db_path: str = "typing_bot.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise

    def init_db(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'ru',
                    selected_languages TEXT DEFAULT '["ru"]',
                    current_level INTEGER DEFAULT 1,
                    total_chars_typed INTEGER DEFAULT 0,
                    total_correct_chars INTEGER DEFAULT 0,
                    total_time_spent INTEGER DEFAULT 0,
                    lessons_completed INTEGER DEFAULT 0,
                    best_wpm REAL DEFAULT 0.0,
                    best_accuracy REAL DEFAULT 0.0,
                    current_streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0,
                    last_active_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Lesson results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    chars_typed INTEGER DEFAULT 0,
                    correct_chars INTEGER DEFAULT 0,
                    time_spent INTEGER DEFAULT 0,
                    wpm REAL DEFAULT 0.0,
                    accuracy REAL DEFAULT 0.0,
                    errors TEXT DEFAULT '[]',
                    completed BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Daily stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stat_date TEXT NOT NULL,
                    chars_typed INTEGER DEFAULT 0,
                    correct_chars INTEGER DEFAULT 0,
                    time_spent INTEGER DEFAULT 0,
                    lessons_completed INTEGER DEFAULT 0,
                    avg_wpm REAL DEFAULT 0.0,
                    avg_accuracy REAL DEFAULT 0.0,
                    UNIQUE(user_id, stat_date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lesson_results_user_id ON lesson_results(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lesson_results_created_at ON lesson_results(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_user_id ON daily_stats(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(stat_date)")

            conn.commit()

    def get_or_create_user(self, user_id: int, username: str = None,
                           first_name: str = None, last_name: str = None,
                           language_code: str = "ru") -> User:
        """Get existing user or create new one."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                user = User(
                    user_id=row["user_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    language_code=row["language_code"],
                    selected_languages=row["selected_languages"],
                    current_level=row["current_level"],
                    total_chars_typed=row["total_chars_typed"],
                    total_correct_chars=row["total_correct_chars"],
                    total_time_spent=row["total_time_spent"],
                    lessons_completed=row["lessons_completed"],
                    best_wpm=row["best_wpm"],
                    best_accuracy=row["best_accuracy"],
                    current_streak=row["current_streak"],
                    max_streak=row["max_streak"],
                    last_active_date=row["last_active_date"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                # Update last active and info
                today = date.today().isoformat()
                if user.last_active_date != today:
                    user.current_streak = user.current_streak + 1 if user.last_active_date == (date.today().replace(day=date.today().day-1).isoformat() if date.today().day > 1 else None) else 1
                    user.max_streak = max(user.max_streak, user.current_streak)
                    user.last_active_date = today

                cursor.execute("""
                    UPDATE users SET username=?, first_name=?, last_name=?,
                    language_code=?, last_active_date=?, current_streak=?, max_streak=?, updated_at=?
                    WHERE user_id=?
                """, (username, first_name, last_name, language_code, today,
                      user.current_streak, user.max_streak, datetime.now().isoformat(), user_id))
                conn.commit()
                return user
            else:
                # Create new user
                today = date.today().isoformat()
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    last_active_date=today,
                    current_streak=1,
                    max_streak=1
                )
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name,
                    language_code, selected_languages, current_level, total_chars_typed,
                    total_correct_chars, total_time_spent, lessons_completed,
                    best_wpm, best_accuracy, current_streak, max_streak,
                    last_active_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user.user_id, user.username, user.first_name, user.last_name,
                      user.language_code, user.selected_languages, user.current_level,
                      user.total_chars_typed, user.total_correct_chars, user.total_time_spent,
                      user.lessons_completed, user.best_wpm, user.best_accuracy,
                      user.current_streak, user.max_streak, user.last_active_date,
                      user.created_at, user.updated_at))
                conn.commit()
                return user

    def update_user(self, user: User):
        """Update user data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            user.updated_at = datetime.now().isoformat()
            cursor.execute("""
                UPDATE users SET username=?, first_name=?, last_name=?,
                language_code=?, selected_languages=?, current_level=?,
                total_chars_typed=?, total_correct_chars=?, total_time_spent=?,
                lessons_completed=?, best_wpm=?, best_accuracy=?,
                current_streak=?, max_streak=?, last_active_date=?, updated_at=?
                WHERE user_id=?
            """, (user.username, user.first_name, user.last_name,
                  user.language_code, user.selected_languages, user.current_level,
                  user.total_chars_typed, user.total_correct_chars, user.total_time_spent,
                  user.lessons_completed, user.best_wpm, user.best_accuracy,
                  user.current_streak, user.max_streak, user.last_active_date,
                  user.updated_at, user.user_id))
            conn.commit()

    def save_lesson_result(self, result: LessonResult) -> int:
        """Save lesson result and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lesson_results (user_id, language, level, chars_typed,
                correct_chars, time_spent, wpm, accuracy, errors, completed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (result.user_id, result.language, result.level, result.chars_typed,
                  result.correct_chars, result.time_spent, result.wpm, result.accuracy,
                  result.errors, result.completed, result.created_at))
            conn.commit()
            return cursor.lastrowid

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_lessons,
                    SUM(chars_typed) as total_chars,
                    SUM(correct_chars) as total_correct,
                    SUM(time_spent) as total_time,
                    AVG(wpm) as avg_wpm,
                    MAX(wpm) as max_wpm,
                    AVG(accuracy) as avg_accuracy,
                    MAX(accuracy) as max_accuracy
                FROM lesson_results WHERE user_id = ? AND completed = 1
            """, (user_id,))
            row = cursor.fetchone()

            stats = dict(row) if row else {}

            # Stats by language
            cursor.execute("""
                SELECT language, COUNT(*) as lessons,
                SUM(chars_typed) as chars, AVG(wpm) as avg_wpm,
                AVG(accuracy) as avg_accuracy
                FROM lesson_results WHERE user_id = ? AND completed = 1
                GROUP BY language
            """, (user_id,))
            stats["by_language"] = [dict(r) for r in cursor.fetchall()]

            # Recent results (last 10)
            cursor.execute("""
                SELECT * FROM lesson_results
                WHERE user_id = ? AND completed = 1
                ORDER BY created_at DESC LIMIT 10
            """, (user_id,))
            stats["recent"] = [dict(r) for r in cursor.fetchall()]

            return stats

    def get_daily_stats(self, user_id: int, days: int = 30) -> List[Dict]:
        """Get daily stats for the last N days."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM daily_stats
                WHERE user_id = ?
                ORDER BY stat_date DESC LIMIT ?
            """, (user_id, days))
            return [dict(r) for r in cursor.fetchall()]

    def update_daily_stats(self, user_id: int, chars_typed: int, correct_chars: int,
                           time_spent: int, wpm: float, accuracy: float):
        """Update daily statistics."""
        today = date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_stats (user_id, stat_date, chars_typed, correct_chars,
                time_spent, lessons_completed, avg_wpm, avg_accuracy)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id, stat_date) DO UPDATE SET
                chars_typed = chars_typed + excluded.chars_typed,
                correct_chars = correct_chars + excluded.correct_chars,
                time_spent = time_spent + excluded.time_spent,
                lessons_completed = lessons_completed + 1,
                avg_wpm = (avg_wpm * (lessons_completed - 1) + excluded.avg_wpm) / lessons_completed,
                avg_accuracy = (avg_accuracy * (lessons_completed - 1) + excluded.avg_accuracy) / lessons_completed
            """, (user_id, today, chars_typed, correct_chars, time_spent, wpm, accuracy))
            conn.commit()

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by WPM."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, best_wpm, best_accuracy,
                lessons_completed, total_chars_typed
                FROM users
                WHERE lessons_completed > 0
                ORDER BY best_wpm DESC, best_accuracy DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None