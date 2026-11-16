from lessons import LessonGenerator
gen = LessonGenerator()
for level in range(1, 6):
    lesson = gen.get_lesson('ru', level)
    print(f'RU Level {level}: {len(lesson.text)} chars: "{lesson.text[:50]}..."')