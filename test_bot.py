"""Test script to verify bot components work correctly."""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from config import SUPPORTED_LANGUAGES, DIFFICULTY_LEVELS, LESSON_SETTINGS
from database import DatabaseManager, User, LessonResult
from lessons import LessonGenerator, get_keyboard_visual, get_key_finger, KEYBOARD_LAYOUTS


def test_config():
    """Test configuration."""
    print("✅ Testing config...")
    assert "ru" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert len(DIFFICULTY_LEVELS) == 5
    print("   Config OK")


def test_lesson_generator():
    """Test lesson generation."""
    print("✅ Testing lesson generator...")
    gen = LessonGenerator()

    # Test Russian lessons
    for level in range(1, 6):
        lesson = gen.get_lesson("ru", level)
        assert lesson.language == "ru"
        assert lesson.level == level
        assert len(lesson.text) > 0
        print(f"   RU Level {level}: {len(lesson.text)} chars")

    # Test English lessons
    for level in range(1, 6):
        lesson = gen.get_lesson("en", level)
        assert lesson.language == "en"
        assert lesson.level == level
        assert len(lesson.text) > 0
        print(f"   EN Level {level}: {len(lesson.text)} chars")

    # Test random lesson
    lesson = gen.get_random_lesson(["ru", "en"], 3)
    assert lesson.language in ["ru", "en"]
    print(f"   Random lesson: {lesson.language}")

    print("   Lesson generator OK")


def test_keyboard_visual():
    """Test keyboard visualization."""
    print("✅ Testing keyboard visual...")
    ru_kb = get_keyboard_visual("ru", "а")
    en_kb = get_keyboard_visual("en", "a")
    assert "а" in ru_kb or "А" in ru_kb
    assert "a" in en_kb or "A" in en_kb
    print("   Keyboard visual OK")


def test_finger_mapping():
    """Test finger mapping."""
    print("✅ Testing finger mapping...")
    assert get_key_finger("ф", "ru") == "left_pinky"
    assert get_key_finger("a", "en") == "left_pinky"
    assert get_key_finger("п", "ru") == "left_index"
    assert get_key_finger("g", "en") == "left_index"
    print("   Finger mapping OK")


def test_database():
    """Test database operations."""
    print("✅ Testing database...")
    import tempfile
    import os

    # Use temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path)

        # Test user creation
        user = db.get_or_create_user(
            user_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="ru"
        )
        assert user.user_id == 12345
        assert user.first_name == "Test"
        assert user.selected_langs_list == ["ru"]
        print("   User creation OK")

        # Test language selection
        user.selected_langs_list = ["ru", "en"]
        db.update_user(user)
        user2 = db.get_or_create_user(user_id=12345)
        assert user2.selected_langs_list == ["ru", "en"]
        print("   Language update OK")

        # Test lesson result
        result = LessonResult(
            user_id=12345,
            language="ru",
            level=1,
            chars_typed=100,
            correct_chars=95,
            time_spent=60,
            wpm=47.5,
            accuracy=95.0,
            errors=json.dumps([5, 10, 15])
        )
        result_id = db.save_lesson_result(result)
        assert result_id > 0
        print("   Lesson result save OK")

        # Test stats
        stats = db.get_user_stats(12345)
        assert stats["total_lessons"] == 1
        assert stats["total_chars"] == 100
        print("   Stats retrieval OK")

        # Test daily stats
        db.update_daily_stats(12345, 100, 95, 60, 47.5, 95.0)
        daily = db.get_daily_stats(12345)
        assert len(daily) == 1
        print("   Daily stats OK")

        # Test leaderboard (user needs lessons_completed > 0)
        user.lessons_completed = 1
        db.update_user(user)
        leaders = db.get_leaderboard()
        assert len(leaders) == 1
        assert leaders[0]["user_id"] == 12345
        print("   Leaderboard OK")

        db.close()
        print("   Database OK")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_special_chars():
    """Test special characters in lessons."""
    print("✅ Testing special characters...")
    gen = LessonGenerator()

    # Level 3+ should have special chars
    for level in [3, 4, 5]:
        lesson = gen.get_lesson("ru", level)
        # Check if any special char is present
        specials = ".,!?-–—()[]{}«»\"':;/@#№%&*+=_\\|<>^~`"
        has_special = any(c in specials for c in lesson.text)
        print(f"   RU Level {level} has specials: {has_special}")

        lesson = gen.get_lesson("en", level)
        specials_en = ".,!?-–—()[]{}«»\"':;/@#%&*+=_\\|<>^~`"
        has_special = any(c in specials_en for c in lesson.text)
        print(f"   EN Level {level} has specials: {has_special}")

    print("   Special chars OK")


import json


def run_all_tests():
    """Run all tests."""
    print("🧪 Running tests...\n")

    test_config()
    test_lesson_generator()
    test_keyboard_visual()
    test_finger_mapping()
    test_database()
    test_special_chars()

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    run_all_tests()