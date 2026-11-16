"""Main Telegram bot for typing practice - Duolingo style with Web App."""
import asyncio
import time
import json
import random
import os
from datetime import datetime, date
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

from config import config, SUPPORTED_LANGUAGES, DIFFICULTY_LEVELS, LESSON_SETTINGS
from database import DatabaseManager, User, LessonResult
from lessons import LessonGenerator


# Conversation states
SELECTING_LANGUAGE, SELECTING_LEVEL, TYPING_LESSON, SHOWING_RESULTS = range(4)

# User session storage
user_sessions: Dict[int, "TypingSession"] = {}


@dataclass
class TypingSession:
    """Active typing session data."""
    user_id: int
    lesson_text: str
    language: str
    level: int
    start_time: float
    chars_typed: int = 0
    correct_chars: int = 0
    errors: List[int] = field(default_factory=list)
    current_position: int = 0
    hearts: int = 5
    xp_earned: int = 0
    streak: int = 0
    perfect_chars: int = 0  # consecutive correct chars


class TypingBot:
    """Main bot class - Duolingo style."""

    # XP rewards
    XP_PER_CORRECT_CHAR = 2
    XP_PER_PERFECT_WORD = 10
    XP_LESSON_COMPLETE = 50
    XP_ACCURACY_BONUS = {  # accuracy thresholds -> bonus XP
        100: 30,
        95: 20,
        90: 10,
        80: 5,
    }
    HEART_LOSS_ON_ERROR = 1
    MAX_HEARTS = 5

    # Web App URL - set via environment variable WEB_APP_URL
    WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://typeowl-production.up.railway.app")

    def __init__(self):
        self.db = DatabaseManager(config.db_path)
        self.lesson_generator = LessonGenerator()

    def get_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Generate a visual progress bar."""
        if total == 0:
            return "▱" * width
        filled = int((current / total) * width)
        return "▰" * filled + "▱" * (width - filled)

    def get_hearts_display(self, hearts: int, max_hearts: int = 5) -> str:
        """Generate hearts display."""
        return "❤️" * hearts + "🤍" * (max_hearts - hearts)

    def format_lesson_text_duolingo(self, text: str, position: int, errors: List[int], perfect_streak: int = 0) -> str:
        """Format lesson text in Duolingo style with character-by-character feedback."""
        result = []
        for i, char in enumerate(text):
            if i < position:
                if i in errors:
                    # Wrong character - show in red with strikethrough
                    result.append(f"<s><b>{self.escape_html(char)}</b></s>")
                elif i == position - 1:
                    # Just typed correctly - highlight with green
                    result.append(f"<b><u>{self.escape_html(char)}</u></b>")
                else:
                    # Correctly typed - subtle underline
                    result.append(f"<u>{self.escape_html(char)}</u>")
            elif i == position:
                # Current character to type - highlight with background
                result.append(f"<b><code>{self.escape_html(char)}</code></b>")
            else:
                # Upcoming characters - dim
                result.append(f"<i>{self.escape_html(char)}</i>")
        return "".join(result)

    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return text.replace("&", "&").replace("<", "<").replace(">", ">")

    def get_xp_for_accuracy(self, accuracy: float) -> int:
        """Calculate XP bonus based on accuracy."""
        for threshold, bonus in sorted(self.XP_ACCURACY_BONUS.items(), reverse=True):
            if accuracy >= threshold:
                return bonus
        return 0

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        db_user = self.db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or "ru"
        )

        if not db_user.selected_langs_list:
            await self.show_language_selection(update, context)
            return SELECTING_LANGUAGE

        await self.show_main_menu(update, context)
        return ConversationHandler.END

    async def show_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show language selection menu - Duolingo style."""
        keyboard = []
        for code, lang in SUPPORTED_LANGUAGES.items():
            keyboard.append([InlineKeyboardButton(
                f"{lang['flag']}  {lang['name']}",
                callback_data=f"lang_{code}"
            )])

        keyboard.append([InlineKeyboardButton("✨  Начать обучение", callback_data="lang_done")])

        text = (
            "🦉 <b>Добро пожаловать в TypeOwl!</b>\n\n"
            "Выбери языки, на которых хочешь научиться печатать:\n"
            "<i>Можно выбрать несколько — будем чередовать</i>"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu - Duolingo style with XP, hearts, streak."""
        user = update.effective_user
        db_user = self.db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or "ru"
        )

        # Calculate total XP
        total_xp = db_user.lessons_completed * self.XP_LESSON_COMPLETE + db_user.total_correct_chars * self.XP_PER_CORRECT_CHAR
        level_info = DIFFICULTY_LEVELS[db_user.current_level]

        # Progress to next level
        chars_for_next = db_user.current_level * LESSON_SETTINGS["chars_per_level"]
        progress_pct = min(100, int((db_user.total_chars_typed / chars_for_next) * 100)) if chars_for_next > 0 else 0
        progress_bar = self.get_progress_bar(db_user.total_chars_typed % chars_for_next, chars_for_next, 15)

        langs_text = "  ".join([
            f"{SUPPORTED_LANGUAGES[code]['flag']}"
            for code in db_user.selected_langs_list
        ])

        keyboard = [
            [InlineKeyboardButton("▶️  Продолжить урок", callback_data="start_lesson")],
            [InlineKeyboardButton("📊  Профиль", callback_data="show_profile"),
             InlineKeyboardButton("🏆  Лига", callback_data="leaderboard")],
            [InlineKeyboardButton("⚙️  Настройки", callback_data="settings"),
             InlineKeyboardButton("💡  Советы", callback_data="help")],
        ]

        text = (
            f"🦉 <b>Привет, {db_user.first_name or 'друже'}!</b>\n\n"
            f"{'🌟' * min(5, db_user.current_level)}  Уровень {db_user.current_level}: {level_info['name']}\n"
            f"{progress_bar}  {progress_pct}% до следующего уровня\n\n"
            f"💎 <b>XP:</b> {total_xp:,}  |  ❤️ <b>Сердц:</b> {self.MAX_HEARTS}  |  🔥 <b>Стрик:</b> {db_user.current_streak} дн.\n"
            f"📚 <b>Уроков:</b> {db_user.lessons_completed}  |  ⚡ <b>Лучший WPM:</b> {db_user.best_wpm:.0f}\n\n"
            f"🎯 <b>Языки:</b> {langs_text}"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed profile - Duolingo style."""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        db_user = self.db.get_or_create_user(user_id=user_id)
        stats = self.db.get_user_stats(user_id)

        total_xp = db_user.lessons_completed * self.XP_LESSON_COMPLETE + db_user.total_correct_chars * self.XP_PER_CORRECT_CHAR
        level_info = DIFFICULTY_LEVELS[db_user.current_level]
        next_level_info = DIFFICULTY_LEVELS.get(db_user.current_level + 1, level_info)

        by_lang = stats.get("by_language", [])
        recent = stats.get("recent", [])

        # Achievements
        achievements = []
        if db_user.lessons_completed >= 1: achievements.append("🥇 Первый урок")
        if db_user.lessons_completed >= 10: achievements.append("🥈 10 уроков")
        if db_user.lessons_completed >= 50: achievements.append("🥉 50 уроков")
        if db_user.lessons_completed >= 100: achievements.append("🏆 100 уроков!")
        if db_user.best_wpm >= 40: achievements.append("⚡ Скорость 40+ WPM")
        if db_user.best_wpm >= 60: achievements.append("🚀 Скорость 60+ WPM")
        if db_user.best_accuracy >= 95: achievements.append("🎯 Точность 95%+")
        if db_user.current_streak >= 7: achievements.append("🔥 Неделя подряд")
        if db_user.current_streak >= 30: achievements.append("💎 Месяц подряд!")

        text = (
            f"👤 <b>Профиль: {db_user.first_name or 'Игрок'}</b>\n\n"
            f"🌟 Уровень {db_user.current_level}: {level_info['name']}\n"
            f"💎 XP: {total_xp:,} / {db_user.current_level * 1000:,}\n"
            f"{self.get_progress_bar(db_user.total_chars_typed % (db_user.current_level * 100), db_user.current_level * 100, 20)}\n\n"
            f"❤️ Сердца: {self.MAX_HEARTS}/{self.MAX_HEARTS}\n"
            f"🔥 Стрик: {db_user.current_streak} дн. (макс: {db_user.max_streak})\n"
            f"📚 Уроков пройдено: {db_user.lessons_completed}\n"
            f"⚡ Лучший WPM: {db_user.best_wpm:.1f}\n"
            f"🎯 Лучшая точность: {db_user.best_accuracy:.1f}%\n"
            f"✍️ Всего знаков: {db_user.total_chars_typed:,}\n\n"
        )

        if achievements:
            text += "<b>🏅 Достижения:</b>\n" + "\n".join(f"  {a}" for a in achievements) + "\n\n"

        if by_lang:
            text += "<b>📊 По языкам:</b>\n"
            for ls in by_lang:
                li = SUPPORTED_LANGUAGES.get(ls['language'], {})
                text += f"  {li.get('flag','')} {li.get('name',ls['language'])}: {ls['lessons']} уроков, {ls['avg_wpm']:.0f} WPM, {ls['avg_accuracy']:.0f}%\n"

        keyboard = [[InlineKeyboardButton("🔙  Назад", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id

        if data.startswith("lang_"):
            await self.handle_language_callback(query, context, data)
        elif data == "lang_done":
            await self.handle_language_done(query, context)
        elif data == "start_lesson":
            await self.handle_start_lesson(query, context)
        elif data.startswith("level_"):
            await self.handle_level_callback(query, context, data)
        elif data == "show_profile":
            await self.show_profile(update, context)
        elif data == "show_stats":
            await self.show_detailed_stats(query, context)
        elif data == "leaderboard":
            await self.show_leaderboard(query, context)
        elif data == "settings":
            await self.show_settings(query, context)
        elif data == "help":
            await self.show_help(query, context)
        elif data.startswith("setlang_"):
            await self.handle_settings_language(query, context, data)
        elif data == "back_main":
            await self.show_main_menu(update, context)
        elif data == "retry_lesson":
            # Retry the same level - we need to know the level from context
            # For now, go back to level selection
            await self.handle_start_lesson(query, context)
        elif data == "next_lesson":
            await self.handle_start_lesson(query, context)

    async def handle_language_callback(self, query, context, data):
        """Handle language selection."""
        user_id = query.from_user.id
        lang_code = data.replace("lang_", "")

        db_user = self.db.get_or_create_user(user_id=user_id)
        selected = db_user.selected_langs_list

        if lang_code in selected:
            selected.remove(lang_code)
        else:
            selected.append(lang_code)

        db_user.selected_languages = json.dumps(selected)
        self.db.update_user(db_user)

        keyboard = []
        for code, lang in SUPPORTED_LANGUAGES.items():
            mark = "✅ " if code in selected else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{lang['flag']}  {lang['name']}",
                callback_data=f"lang_{code}"
            )])
        keyboard.append([InlineKeyboardButton("✨  Начать обучение", callback_data="lang_done")])

        await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))

    async def handle_language_done(self, query, context):
        """Handle language selection done."""
        user_id = query.from_user.id
        db_user = self.db.get_or_create_user(user_id=user_id)

        if not db_user.selected_langs_list:
            await query.answer("Выбери хотя бы один язык! 🦉", show_alert=True)
            return

        await self.show_main_menu(query, context)

    async def handle_start_lesson(self, query, context):
        """Handle start lesson - show level selection."""
        user_id = query.from_user.id
        db_user = self.db.get_or_create_user(user_id=user_id)

        keyboard = []
        for level, info in DIFFICULTY_LEVELS.items():
            if level <= db_user.current_level:
                # Calculate stars for this level (based on completion)
                stars = "⭐" * min(3, max(0, db_user.current_level - level + 1))
                keyboard.append([InlineKeyboardButton(
                    f"🔓  Уровень {level}: {info['name']}  {stars}",
                    callback_data=f"level_{level}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    f"🔒  Уровень {level}: {info['name']}  (нужен ур. {level})",
                    callback_data=f"level_{level}"
                )])

        keyboard.append([InlineKeyboardButton("🔙  Назад", callback_data="back_main")])

        await query.edit_message_text(
            "📚 <b>Выбери урок</b>\n\n"
            "🔓 — доступен\n"
            "🔒 — разблокируется позже\n"
            "⭐ — твои звёзды за прохождение",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    async def handle_level_callback(self, query, context, data):
        """Handle level selection and open web app for typing lesson."""
        user_id = query.from_user.id
        level = int(data.replace("level_", ""))

        db_user = self.db.get_or_create_user(user_id=user_id)

        if level > db_user.current_level:
            await query.answer("Этот урок пока заблокирован! 🔒", show_alert=True)
            return

        # Select language
        language = random.choice(db_user.selected_langs_list)

        # Create web app URL with parameters
        web_app_url = f"{self.WEB_APP_URL}/?user_id={user_id}&language={language}&level={level}"

        keyboard = [[InlineKeyboardButton(
            f"🎮 Открыть урок {level} в веб-приложении",
            web_app=WebAppInfo(url=web_app_url)
        )], [InlineKeyboardButton("🔙 Назад", callback_data="start_lesson")]]

        await query.edit_message_text(
            f"🦉 <b>Урок {level} готов!</b>\n\n"
            f"🌐 {SUPPORTED_LANGUAGES[language]['flag']} {SUPPORTED_LANGUAGES[language]['name']} • {DIFFICULTY_LEVELS[level]['name']}\n\n"
            f"Нажми кнопку ниже, чтобы открыть интерактивный урок с виртуальной клавиатурой, "
            f"подсветкой пальцев и отображением ошибок в реальном времени.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    async def show_typing_lesson(self, query, context, session: TypingSession):
        """Show the typing lesson - Duolingo style with big text and progress."""
        lang_info = SUPPORTED_LANGUAGES[session.language]
        level_info = DIFFICULTY_LEVELS[session.level]

        progress = session.current_position
        total = len(session.lesson_text)
        progress_pct = int((progress / total) * 100) if total > 0 else 0
        progress_bar = self.get_progress_bar(progress, total, 18)

        # Current and next characters
        current_char = session.lesson_text[progress] if progress < total else "✨"
        next_chars = session.lesson_text[progress:progress+3] if progress < total else ""

        # Format text with Duolingo-style highlighting
        display_text = self.format_lesson_text_duolingo(
            session.lesson_text, progress, session.errors, session.perfect_chars
        )

        # Accuracy so far
        accuracy = (session.correct_chars / session.chars_typed * 100) if session.chars_typed > 0 else 100

        # XP preview
        xp_preview = session.correct_chars * self.XP_PER_CORRECT_CHAR

        text = (
            f"🦉 <b>Урок {session.level}  •  {lang_info['flag']} {lang_info['name']}</b>\n"
            f"{progress_bar}  {progress}/{total}  ({progress_pct}%)\n\n"
            f"❤️ {self.get_hearts_display(session.hearts)}  "
            f"🎯 {accuracy:.0f}%  "
            f"💎 +{xp_preview} XP\n\n"
            f"<b>{display_text}</b>\n\n"
            f"👇 <b>Печатай здесь:</b> <code>{self.escape_html(next_chars)}</code>..."
        )

        keyboard = [
            [InlineKeyboardButton("⌫", callback_data="type_backspace"),
             InlineKeyboardButton("⏭ Пропуск", callback_data="type_skip"),
             InlineKeyboardButton("🏁 Завершить", callback_data="finish_lesson")],
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    async def handle_typing_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input during typing lesson - character by character with feedback."""
        user_id = update.effective_user.id

        if user_id not in user_sessions:
            return

        session = user_sessions[user_id]
        input_text = update.message.text

        # Delete the user's message to keep chat clean (optional - comment out if not desired)
        try:
            await update.message.delete()
        except:
            pass

        # Process each character
        for char in input_text:
            if session.current_position >= len(session.lesson_text):
                break

            expected_char = session.lesson_text[session.current_position]

            if char == expected_char:
                # Correct!
                session.correct_chars += 1
                session.perfect_chars += 1
                session.xp_earned += self.XP_PER_CORRECT_CHAR

                # Check for word completion bonus
                if expected_char == " " and session.perfect_chars >= 3:
                    session.xp_earned += self.XP_PER_PERFECT_WORD
            else:
                # Mistake!
                session.errors.append(session.current_position)
                session.perfect_chars = 0
                session.hearts -= self.HEART_LOSS_ON_ERROR

                if session.hearts <= 0:
                    # Out of hearts - lesson failed
                    await self.lesson_failed(update, context, session)
                    return

            session.chars_typed += 1
            session.current_position += 1

        # Check if lesson complete
        if session.current_position >= len(session.lesson_text):
            await self.finish_lesson(update, context, session)
        else:
            # Update display silently (edit the lesson message)
            await self.update_typing_display(update, context, session)

    async def update_typing_display(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session: TypingSession):
        """Update the typing lesson display by editing the message."""
        # We need to find the lesson message to edit it
        # For now, send a brief update - in production we'd track the message_id
        lang_info = SUPPORTED_LANGUAGES[session.language]
        progress = session.current_position
        total = len(session.lesson_text)
        progress_pct = int((progress / total) * 100) if total > 0 else 0
        progress_bar = self.get_progress_bar(progress, total, 18)
        current_char = session.lesson_text[progress] if progress < total else "✨"
        next_chars = session.lesson_text[progress:progress+3] if progress < total else ""

        display_text = self.format_lesson_text_duolingo(
            session.lesson_text, progress, session.errors, session.perfect_chars
        )
        accuracy = (session.correct_chars / session.chars_typed * 100) if session.chars_typed > 0 else 100
        xp_preview = session.correct_chars * self.XP_PER_CORRECT_CHAR

        text = (
            f"🦉 <b>Урок {session.level}  •  {lang_info['flag']} {lang_info['name']}</b>\n"
            f"{progress_bar}  {progress}/{total}  ({progress_pct}%)\n\n"
            f"❤️ {self.get_hearts_display(session.hearts)}  "
            f"🎯 {accuracy:.0f}%  "
            f"💎 +{xp_preview} XP\n\n"
            f"<b>{display_text}</b>\n\n"
            f"👇 <code>{self.escape_html(next_chars)}</code>..."
        )

        keyboard = [
            [InlineKeyboardButton("⌫", callback_data="type_backspace"),
             InlineKeyboardButton("⏭ Пропуск", callback_data="type_skip"),
             InlineKeyboardButton("🏁 Завершить", callback_data="finish_lesson")],
        ]

        # Try to edit the last bot message, or send new one
        try:
            # In real implementation, we'd store message_id in session
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id - 1,  # approximate
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        except:
            pass  # Ignore edit failures, user will see updates on next keystroke

    async def lesson_failed(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session: TypingSession):
        """Handle lesson failure (out of hearts)."""
        user_id = session.user_id
        del user_sessions[user_id]

        lang_info = SUPPORTED_LANGUAGES[session.language]

        text = (
            "💔 <b>Сердца закончились!</b>\n\n"
            f"🦉 Урок {session.level} • {lang_info['flag']} {lang_info['name']}\n"
            f"💎 Заработано XP: {session.xp_earned}\n"
            f"🎯 Точность: {(session.correct_chars/session.chars_typed*100) if session.chars_typed else 0:.0f}%\n\n"
            "Не расстраивайся! Ошибки — это часть обучения. 🦉\n"
            "Попробуй ещё раз, ты справишься!"
        )

        keyboard = [
            [InlineKeyboardButton("🔄  Попробовать снова", callback_data="retry_lesson")],
            [InlineKeyboardButton("🏠  В меню", callback_data="back_main")],
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def finish_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session: TypingSession):
        """Finish the typing lesson and show results with XP animation."""
        elapsed = time.time() - session.start_time
        time_spent = max(1, int(elapsed))

        total_chars = len(session.lesson_text)
        wpm = (session.correct_chars / 5) / (time_spent / 60) if time_spent > 0 else 0
        accuracy = (session.correct_chars / session.chars_typed * 100) if session.chars_typed > 0 else 0

        # Calculate XP
        base_xp = session.xp_earned
        accuracy_bonus = self.get_xp_for_accuracy(accuracy)
        completion_bonus = self.XP_LESSON_COMPLETE if accuracy >= 70 else 0
        perfect_bonus = 20 if accuracy == 100 else 0
        speed_bonus = 15 if wpm >= 40 else (10 if wpm >= 30 else 0)

        total_xp = base_xp + accuracy_bonus + completion_bonus + perfect_bonus + speed_bonus

        # Save to database
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
            completed=True
        )
        self.db.save_lesson_result(result)

        # Update user stats
        db_user = self.db.get_or_create_user(user_id=session.user_id)
        db_user.total_chars_typed += session.chars_typed
        db_user.total_correct_chars += session.correct_chars
        db_user.total_time_spent += time_spent
        db_user.lessons_completed += 1
        db_user.best_wpm = max(db_user.best_wpm, wpm)
        db_user.best_accuracy = max(db_user.best_accuracy, accuracy)

        # Level up check
        leveled_up = False
        if db_user.total_chars_typed >= db_user.current_level * LESSON_SETTINGS["chars_per_level"]:
            if db_user.current_level < max(DIFFICULTY_LEVELS.keys()):
                db_user.current_level += 1
                leveled_up = True

        self.db.update_user(db_user)
        self.db.update_daily_stats(
            session.user_id, session.chars_typed, session.correct_chars,
            time_spent, wpm, accuracy
        )

        # Clean up session
        del user_sessions[session.user_id]

        # Show results with XP breakdown
        lang_info = SUPPORTED_LANGUAGES[session.language]
        level_info = DIFFICULTY_LEVELS[session.level]

        # Determine rank
        if wpm >= LESSON_SETTINGS["wpm_threshold"]["expert"]:
            rank_emoji, rank_name = "🏆", "Эксперт"
        elif wpm >= LESSON_SETTINGS["wpm_threshold"]["advanced"]:
            rank_emoji, rank_name = "🥇", "Профессионал"
        elif wpm >= LESSON_SETTINGS["wpm_threshold"]["intermediate"]:
            rank_emoji, rank_name = "🥈", "Продвинутый"
        elif wpm >= LESSON_SETTINGS["wpm_threshold"]["beginner"]:
            rank_emoji, rank_name = "🥉", "Начинающий"
        else:
            rank_emoji, rank_name = "🌱", "Новичок"

        # Stars earned
        stars = 0
        if accuracy >= 95: stars += 1
        if wpm >= 30: stars += 1
        if session.hearts == self.MAX_HEARTS: stars += 1
        if accuracy == 100: stars = 3  # Perfect!

        text = (
            f"🎉 <b>Урок пройден!</b>  {'⭐' * stars}\n\n"
            f"🦉 {lang_info['flag']} {lang_info['name']}  •  Ур. {level_info['name']}\n"
            f"{rank_emoji} <b>{rank_name}</b>  •  ⚡ {wpm:.0f} WPM  •  🎯 {accuracy:.0f}%\n\n"
            f"💎 <b>XP:</b> +{total_xp}\n"
            f"  ✍️ Знаков: +{base_xp}\n"
        )

        if accuracy_bonus:
            text += f"  🎯 Точность {accuracy:.0f}%: +{accuracy_bonus}\n"
        if completion_bonus:
            text += f"  ✅ Завершение: +{completion_bonus}\n"
        if perfect_bonus:
            text += f"  💎 Идеально! +{perfect_bonus}\n"
        if speed_bonus:
            text += f"  🚀 Скорость {wpm:.0f} WPM: +{speed_bonus}\n"

        text += (
            f"\n📈 <b>Прогресс:</b>\n"
            f"  🌟 Ур. {db_user.current_level}  |  🔥 {db_user.current_streak} дн.  |  💎 {db_user.lessons_completed * self.XP_LESSON_COMPLETE + db_user.total_correct_chars * self.XP_PER_CORRECT_CHAR:,} XP"
        )

        if leveled_up:
            text += f"\n\n🌟 <b>НОВЫЙ УРОВЕНЬ {db_user.current_level}!</b> 🎉"

        keyboard = [
            [InlineKeyboardButton("🔄  Ещё раз", callback_data="retry_lesson"),
             InlineKeyboardButton("➡️  Далее", callback_data="next_lesson")],
            [InlineKeyboardButton("🏠  Меню", callback_data="back_main")],
        ]

        target = update.callback_query if update.callback_query else update.message
        if target:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_detailed_stats(self, query, context):
        """Show detailed statistics."""
        user_id = query.from_user.id
        db_user = self.db.get_or_create_user(user_id=user_id)
        stats = self.db.get_user_stats(user_id)

        by_lang = stats.get("by_language", [])
        recent = stats.get("recent", [])

        total_xp = db_user.lessons_completed * self.XP_LESSON_COMPLETE + db_user.total_correct_chars * self.XP_PER_CORRECT_CHAR

        text = (
            f"📊 <b>Статистика</b>\n\n"
            f"💎 XP: {total_xp:,}\n"
            f"📚 Уроков: {stats.get('total_lessons', 0)}\n"
            f"✍️ Знаков: {stats.get('total_chars', 0) or 0:,}\n"
            f"✅ Верно: {stats.get('total_correct', 0) or 0:,}\n"
            f"⏱ Время: {(stats.get('total_time', 0) or 0)//60} мин\n"
            f"⚡ Средний WPM: {stats.get('avg_wpm', 0) or 0:.1f}\n"
            f"🏆 Макс WPM: {stats.get('max_wpm', 0) or 0:.1f}\n"
            f"🎯 Средняя точность: {stats.get('avg_accuracy', 0) or 0:.1f}%\n"
        )

        if by_lang:
            text += "\n<b>По языкам:</b>\n"
            for ls in by_lang:
                li = SUPPORTED_LANGUAGES.get(ls['language'], {})
                text += f"  {li.get('flag','')} {li.get('name',ls['language'])}: {ls['lessons']} уроков, {ls['avg_wpm']:.0f} WPM\n"

        if recent:
            text += "\n<b>Последние:</b>\n"
            for i, ls in enumerate(recent[:5], 1):
                li = SUPPORTED_LANGUAGES.get(ls['language'], {})
                text += f"  {i}. {li.get('flag','')} Ур.{ls['level']} — {ls['wpm']:.0f} WPM, {ls['accuracy']:.0f}%\n"

        keyboard = [[InlineKeyboardButton("🔙  Назад", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_leaderboard(self, query, context):
        """Show leaderboard."""
        leaders = self.db.get_leaderboard(10)

        text = "🏆 <b>Лига лидеров</b>\n\n"
        for i, user in enumerate(leaders, 1):
            name = user['first_name'] or user['username'] or f"Player{user['user_id']}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            xp = user['lessons_completed'] * self.XP_LESSON_COMPLETE + user['total_chars_typed'] * self.XP_PER_CORRECT_CHAR // 100
            text += f"{medal} <b>{name}</b> — {user['best_wpm']:.0f} WPM, {user['best_accuracy']:.0f}% ({xp:,} XP)\n"

        keyboard = [[InlineKeyboardButton("🔙  Назад", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def show_settings(self, query, context):
        """Show settings."""
        user_id = query.from_user.id
        db_user = self.db.get_or_create_user(user_id=user_id)

        keyboard = []
        for code, lang in SUPPORTED_LANGUAGES.items():
            mark = "✅ " if code in db_user.selected_langs_list else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{lang['flag']}  {lang['name']}",
                callback_data=f"setlang_{code}"
            )])
        keyboard.append([InlineKeyboardButton("🔙  Назад", callback_data="back_main")])

        text = "⚙️ <b>Настройки</b>\n\nВыбери языки для уроков:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    async def handle_settings_language(self, query, context, data):
        """Handle language toggle."""
        user_id = query.from_user.id
        lang_code = data.replace("setlang_", "")

        db_user = self.db.get_or_create_user(user_id=user_id)
        selected = db_user.selected_langs_list

        if lang_code in selected:
            if len(selected) == 1:
                await query.answer("Нужен хотя бы один язык! 🦉", show_alert=True)
                return
            selected.remove(lang_code)
        else:
            selected.append(lang_code)

        db_user.selected_languages = json.dumps(selected)
        self.db.update_user(db_user)
        await self.show_settings(query, context)

    async def show_help(self, query, context):
        """Show tips."""
        text = (
            "💡 <b>Советы от TypeOwl</b>\n\n"
            "🎯 <b>Правила слепой печати:</b>\n"
            "• Пальцы на базовой позиции: ФЫВА / OЛДЖ\n"
            "• Каждый палец — свои клавиши\n"
            "• Смотри в экран, не на клавиатуру\n"
            "• Возвращай пальцы на базу после каждого нажатия\n\n"
            "⚡ <b>Как прогрессировать:</b>\n"
            "1. Точность важнее скорости\n"
            "2. 15 мин в день > 2 часа раз в неделю\n"
            "3. Не спеши — скорость придёт сама\n"
            "4. Ошибки нормальны, учись на них\n\n"
            "💎 <b>XP система:</b>\n"
            "• +2 XP за каждый верный символ\n"
            "• +10 XP за слово без ошибок\n"
            "• +50 XP за завершение урока\n"
            "• Бонусы за точность 80%+/90%+/95%+/100%\n"
            "• Бонус за скорость 30+/40+ WPM\n\n"
            "❤️ <b>Сердца:</b>\n"
            "• 5 сердец на урок\n"
            "• -1 за ошибку\n"
            "• 0 сердец = урок провален\n"
            "• Можно попробовать снова\n\n"
            "🌟 <b>Уровни:</b> 30 → 50 → 80 → 120 → 200 знаков"
        )

        keyboard = [[InlineKeyboardButton("🔙  Назад", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    print(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "🦉 Упс, ошибка! Попробуй /start"
        )


def main():
    """Main entry point."""
    if config.token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Токен не настроен!")
        return

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )
    application = Application.builder().token(config.token).request(request).build()

    bot = TypingBot()

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("menu", lambda u, c: bot.show_main_menu(u, c)))
    application.add_handler(CommandHandler("profile", lambda u, c: bot.show_profile(u, c)))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_typing_input))
    application.add_error_handler(error_handler)

    print("🦉 TypeOwl запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()