
#/ =====================================================================================
#/  Configuration file — application settings
#/  =====================================================================================
#/
#/  HOW TO USE:
#/    1. Copy .env.example → .env
#/    2. Edit .env to match your school (database, school name, etc.)
#/    3. For Docker: all defaults work out of the box
#/    4. For manual setup: change DATABASE_URL to your local PostgreSQL
#/
#/  All settings can be overridden via environment variables.
#/  In production, set everything via env vars (never commit .env to git).
#/
#/  ═══════════════════════════════════════════════════════════════════════════════
#/  QUICK START:
#/    Docker:         docker compose -p school up -d
#/    Manual (venv):  python -m venv venv && source venv/bin/activate &&
#/                    pip install -r requirements.txt &&
#/                    uvicorn app.main:app --reload
#/  ═══════════════════════════════════════════════════════════════════════════════
#/
#/ =====================================================================================

import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

#! Load .env only in development. In production, use real environment variables.
load_dotenv()


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  DATABASE — PostgreSQL + MongoDB  /  БАЗА ДАННЫХ
#/ ═══════════════════════════════════════════════════════════════════════════════

#! PostgreSQL — main DB connection (users, grades, schedules, homework)
#! PostgreSQL — основная БД (пользователи, оценки, расписание, д/з)
#! Format: postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB_NAME
#! Docker: postgresql+asyncpg://school:school_pass@postgres:5432/school_db
#! Local:  postgresql+asyncpg://school:school_pass@localhost:5432/school_db
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://school:school_pass@localhost:5432/school_db")

#! MongoDB — action logging (user actions, admin logs) / Логирование действий
#! Format: mongodb://HOST:PORT
#! Docker: mongodb://mongo:27017
#! Local:  mongodb://localhost:27017
#? Optional: empty string disables logging (not recommended) / Не рекомендуется отключать
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  JWT AUTH — token-based authentication  /  АВТОРИЗАЦИЯ JWT
#/ ═══════════════════════════════════════════════════════════════════════════════

#! CHANGE THIS in production — use a long random string / СМЕНИТЕ в продакшене!
#! Example: openssl rand -hex 64
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")

#* JWT signing algorithm (HS256, HS384, HS512) / Алгоритм подписи JWT
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

#* Token expiration hours / Срок действия токена (часы). Default: 24h
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  APP — general settings  /  ОБЩИЕ НАСТРОЙКИ
#/ ═══════════════════════════════════════════════════════════════════════════════

#* App name in browser tab / Название приложения (вкладка браузера)
APP_NAME = os.getenv("APP_NAME", "Электронный дневник")

#* Base URL / Базовый URL приложения (для ссылок)
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

#! Debug mode — detailed errors / Режим отладки (отключить в продакшене!)
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  SCHOOL INFO — customize for your school  /  ИНФОРМАЦИЯ О ШКОЛЕ
#/ ═══════════════════════════════════════════════════════════════════════════════

#* School name / Название школы (отображается на всех страницах)
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Частная школа")

#* School city / Город школы
SCHOOL_CITY = os.getenv("SCHOOL_CITY", "Москва")


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  FILE UPLOADS — library books, avatars, etc.  /  ЗАГРУЗКА ФАЙЛОВ
#/ ═══════════════════════════════════════════════════════════════════════════════

#* Upload directory / Директория загрузки файлов (относительно корня проекта)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "app/static/uploads")


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  SCHEDULE / TIMETABLE — lesson timing  /  РАСПИСАНИЕ УРОКОВ
#/ ═══════════════════════════════════════════════════════════════════════════════

#* First lesson start time / Время начала первого урока (HH:MM)
LESSON_START_TIME = os.getenv("LESSON_START_TIME", "09:00")

#* Lesson duration in minutes / Длительность урока (мин). Default: 45
LESSON_DURATION_MINUTES = int(os.getenv("LESSON_DURATION_MINUTES", "45"))

#* Max lessons per day / Макс. уроков в день. Default: 8
#* Used by get_lesson_times()
MAX_LESSONS_PER_DAY = int(os.getenv("MAX_LESSONS_PER_DAY", "8"))

#* Working days (0=Mon…6=Sun) / Рабочие дни. Default: 0-5 (Mon-Sat)
#* Used by get_school_dates()
WORKING_DAYS = [int(x) for x in os.getenv("WORKING_DAYS", "0,1,2,3,4,5").split(",")]


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  ACADEMIC YEAR — school calendar  /  УЧЕБНЫЙ ГОД
#/ ═══════════════════════════════════════════════════════════════════════════════

#* Academic year start month / Месяц начала уч. года. Default: 9 (September)
ACADEMIC_YEAR_START_MONTH = int(os.getenv("ACADEMIC_YEAR_START_MONTH", "9"))

#* Academic year end month / Месяц окончания уч. года. Default: 5 (May)
ACADEMIC_YEAR_END_MONTH = int(os.getenv("ACADEMIC_YEAR_END_MONTH", "5"))

#* Academic year end day / День окончания уч. года. Default: 31
ACADEMIC_YEAR_END_DAY = int(os.getenv("ACADEMIC_YEAR_END_DAY", "31"))

#* Exam period start / Начало экзаменов (после этой даты таблица оценок не генерирует столбцы)
ACADEMIC_YEAR_EXAM_START = os.getenv("ACADEMIC_YEAR_EXAM_START", "2025-05-25")


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  GRADING SYSTEM  /  СИСТЕМА ОЦЕНИВАНИЯ
#/ ═══════════════════════════════════════════════════════════════════════════════

#* Number of trimesters / Количество триместров. Default: 3
TRIMESTER_COUNT = int(os.getenv("TRIMESTER_COUNT", "3"))

#* Grade scale min/max / Шкала оценок — минимум и максимум
GRADE_MIN = int(os.getenv("GRADE_MIN", "1"))
GRADE_MAX = int(os.getenv("GRADE_MAX", "5"))


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  SEED DATA — defaults for the test data generator  /  ТЕСТОВЫЕ ДАННЫЕ
#/ ═══════════════════════════════════════════════════════════════════════════════

#! Default passwords for test accounts / Пароли по умолчанию для тестовых аккаунтов
#! Used by seed_data.py / Используются в seed_data.py
SEED_TEACHER_PASSWORD = os.getenv("SEED_TEACHER_PASSWORD", "teacher123")
SEED_STUDENT_PASSWORD = os.getenv("SEED_STUDENT_PASSWORD", "student123")
SEED_SECRETARY_PASSWORD = os.getenv("SEED_SECRETARY_PASSWORD", "secretary123")

#! ═══════════════════════════════════════════════════════════════════════════════
#!  DEFAULT ACCOUNTS (created automatically on first startup):
#!    Director:  director@school.ru / director123
#!    Admin:     admin@school.ru / admin123
#!    Secretary: secretary@school.ru / secretary123
#!  CHANGE ALL PASSWORDS immediately after first login!
#! ═══════════════════════════════════════════════════════════════════════════════


#/ ═══════════════════════════════════════════════════════════════════════════════
#/  HELPER FUNCTIONS  /  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
#/ ═══════════════════════════════════════════════════════════════════════════════

def get_lesson_times():
    """
    Generate lesson time slots for the school day.

    Returns:
        list of tuples: [(lesson_number, start_time_str, end_time_str), ...]

    Example:
        >>> get_lesson_times()
        [(1, '09:00', '09:45'), (2, '09:45', '10:30'), ..., (8, '14:45', '15:30')]
    """
    start = datetime.strptime(LESSON_START_TIME, "%H:%M")
    times = []
    for i in range(1, MAX_LESSONS_PER_DAY + 1):
        s = (start + timedelta(minutes=(i - 1) * LESSON_DURATION_MINUTES)).strftime("%H:%M")
        e = (start + timedelta(minutes=(i - 1) * LESSON_DURATION_MINUTES + LESSON_DURATION_MINUTES)).strftime("%H:%M")
        times.append((i, s, e))
    return times


def get_academic_year() -> tuple:
    """
    Determine the current academic year based on today's date.

    Academic year runs from ACADEMIC_YEAR_START_MONTH to ACADEMIC_YEAR_END_MONTH.
    If today is >= start month, year = (this_year, next_year).
    Otherwise, year = (last_year, this_year).

    Returns:
        tuple: (start_year, end_year)

    Example (if today is 2026-06-18):
        >>> get_academic_year()
        (2025, 2026)  # because June < September
    """
    today = date.today()
    if today.month >= ACADEMIC_YEAR_START_MONTH:
        return (today.year, today.year + 1)
    return (today.year - 1, today.year)


def get_school_dates() -> list:
    """
    Generate all school days from Sep 1 to May 31 of the current academic year.

    Filters out weekends based on WORKING_DAYS setting (default: Mon-Sat).

    Returns:
        list of date objects

    Example:
        >>> len(get_school_dates())
        195  # approximately 195 school days per year
    """
    year_start, year_end = get_academic_year()
    start = date(year_start, ACADEMIC_YEAR_START_MONTH, 1)
    end = date(year_end, ACADEMIC_YEAR_END_MONTH, ACADEMIC_YEAR_END_DAY)
    dates = []
    current = start
    while current <= end:
        if current.weekday() in WORKING_DAYS:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def get_schedule_school_dates(query_date=None):
    """
    Return school dates up to a given date (default: today, capped at end of academic year).

    This is used by the grade table to generate columns only for past dates.

    Args:
        query_date: date to cap at (default: today)

    Returns:
        list of date objects (filtered to <= query_date)
    """
    today = query_date or date.today()
    all_dates = get_school_dates()
    return [d for d in all_dates if d <= today]


def weekday_to_schedule_day(d: date) -> int:
    """
    Convert Python weekday() number to schedule's day_of_week convention.

    Python weekday(): 0=Mon, 1=Tue, ..., 6=Sun
    Schedule convention: 1=Mon, 2=Tue, ..., 7=Sun

    Args:
        d: date object

    Returns:
        int: 1-7 (1=Monday, 7=Sunday)
    """
    return d.weekday() + 1
