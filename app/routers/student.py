#/ =====================================================================================
#/  Student router — student panel
#/  Grades, schedule, homework, analytics (performance chart)
#/  Personal profile card (full name, address, parents' phones — student and teachers only)
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import User, Class, Subject, Enrollment, Schedule, Grade, Homework, News
from app.auth import require_role, get_current_user, require_auth, hash_password, verify_password
from app.logger import log_action
from app.main import templates
from datetime import date, datetime, timedelta
from collections import defaultdict

router = APIRouter(prefix="/student", tags=["student"])

DAYS_RU = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


#/ ─── Dashboard / Панель ученика ───────────────────────────────────────────────────────
#/ Grades overview, homework, news, averages
#/ Обзор оценок, домашних заданий, новостей, средний балл
@router.get("/dashboard", response_class=HTMLResponse)
async def student_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get student's class
    enrollment = await session.execute(
        select(Enrollment).where(Enrollment.student_id == user.id)
        .options(selectinload(Enrollment.class_))
    )
    enrollment = enrollment.scalar_one_or_none()

    #* Get last 5 grades
    grades = await session.execute(
        select(Grade).where(Grade.student_id == user.id)
        .options(selectinload(Grade.subject), selectinload(Grade.teacher))
        .order_by(Grade.created_at.desc())
        .limit(10)
    )
    grades = grades.scalars().all()

    #* Average grade across all subjects
    all_grades = await session.execute(
        select(Grade).where(Grade.student_id == user.id, Grade.grade_type == "regular")
        .options(selectinload(Grade.subject))
    )
    all_grades = all_grades.scalars().all()
    subjects_avg = {}
    for g in all_grades:
        subj_name = g.subject.name
        if g.value is not None:
            if subj_name not in subjects_avg:
                subjects_avg[subj_name] = []
            subjects_avg[subj_name].append(g.value)
    for k in subjects_avg:
        subjects_avg[k] = round(sum(subjects_avg[k]) / len(subjects_avg[k]), 2)

    #* Homework (for today/tomorrow)
    today = date.today()
    homeworks = await session.execute(
        select(Homework).where(Homework.class_id == enrollment.class_id if enrollment else None)
        .options(selectinload(Homework.subject), selectinload(Homework.teacher))
        .order_by(Homework.created_at.desc())
        .limit(5)
    )
    homeworks = homeworks.scalars().all() if enrollment else []

    #* News (latest)
    news = await session.execute(
        select(News).where(News.news_type.in_(["news", "holiday", "announcement"]))
        .order_by(News.is_pinned.desc(), News.created_at.desc())
        .limit(5)
    )
    news = news.scalars().all()

    return templates.TemplateResponse("dashboard/student.html", {
        "request": request, "user": user,
        "enrollment": enrollment, "grades": grades,
        "subjects_avg": subjects_avg,
        "homeworks": homeworks, "news": news,
        "today": today,
    })


#/ ─── Profile (personal card) / Профиль (личная карточка) ────────────────────────────
#/ Name, class, age, contact info
#/ Имя, класс, возраст, контактные данные
@router.get("/profile", response_class=HTMLResponse)
async def student_profile(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get student's class
    enrollment = await session.execute(
        select(Enrollment).where(Enrollment.student_id == user.id)
        .options(selectinload(Enrollment.class_))
    )
    enrollment = enrollment.scalar_one_or_none()

    return templates.TemplateResponse("student/profile.html", {
        "request": request, "user": user,
        "enrollment": enrollment,
        "age": _calc_age(user.date_of_birth) if user.date_of_birth else None,
    })


#/ ─── My Grades / Мои оценки ──────────────────────────────────────────────────────────
#/ All grades grouped by subject, averages, trimester filter
#/ Все оценки по предметам, средние, фильтр по триместру
@router.get("/grades", response_class=HTMLResponse)
async def student_grades(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    trimester = request.query_params.get("trimester", 0)
    try:
        trimester = int(trimester)
    except ValueError:
        trimester = 0

    #* Get all grades with subjects
    grade_query = select(Grade).where(Grade.student_id == user.id)
    if trimester > 0:
        grade_query = grade_query.where(Grade.term == trimester)
    grade_query = grade_query.options(
        selectinload(Grade.subject), selectinload(Grade.teacher)
    ).order_by(Grade.subject_id, Grade.grade_date.desc())

    grades = await session.execute(grade_query)
    grades = grades.scalars().all()

    #* Group by subjects
    subjects_grades = defaultdict(list)
    for g in grades:
        subjects_grades[g.subject.name].append({
            "id": str(g.id),
            "value": g.value,
            "type": g.grade_type,
            "date": g.grade_date.strftime("%d.%m.%Y") if g.grade_date else "",
            "teacher": f"{g.teacher.last_name} {g.teacher.first_name[0]}." if g.teacher else "",
            "comment": g.comment,
        })

    #* Average grade per subject
    averages = {}
    subject_objs = {}
    for g in grades:
        subj_name = g.subject.name
        subj_id = str(g.subject_id)
        if subj_name not in subject_objs:
            subject_objs[subj_name] = {"id": subj_id, "name": subj_name}
        regular = [gg for gg in grades if str(gg.subject_id) == subj_id and gg.grade_type == "regular" and gg.value is not None]
        if regular:
            avg = sum(gg.value for gg in regular) / len(regular)
            averages[subj_name] = round(avg, 2)

    #* Overall average grade
    all_regular = [g for g in grades if g.grade_type == "regular" and g.value is not None]
    overall_avg = round(sum(g.value for g in all_regular) / len(all_regular), 2) if all_regular else 0

    current_trimester = trimester if trimester > 0 else _get_current_trimester()

    return templates.TemplateResponse("student/grades.html", {
        "request": request, "user": user,
        "subjects_grades": dict(subjects_grades),
        "averages": averages,
        "overall_avg": overall_avg,
        "trimester": trimester,
        "trimesters": range(1, 4),
    })


#/ ─── Schedule / Расписание ────────────────────────────────────────────────────────────
#/ Weekly schedule for student's class
#/ Расписание на неделю для класса ученика
@router.get("/schedule", response_class=HTMLResponse)
async def student_schedule(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    enrollment = await session.execute(
        select(Enrollment).where(Enrollment.student_id == user.id)
    )
    enrollment = enrollment.scalar_one_or_none()

    week = {d: [] for d in range(1, 8)}  #* 1=Mon ... 7=Sun
    if enrollment:
        schedules = await session.execute(
            select(Schedule).where(Schedule.class_id == enrollment.class_id, Schedule.valid_until.is_(None))
            .options(selectinload(Schedule.subject), selectinload(Schedule.teacher))
            .order_by(Schedule.day_of_week, Schedule.lesson_number)
        )
        schedule_list = schedules.scalars().all()
        is_zero_based = any(s.day_of_week == 0 for s in schedule_list)
        for s in schedule_list:
            week[(s.day_of_week + 1) if is_zero_based else s.day_of_week].append(s)

    return templates.TemplateResponse("student/schedule.html", {
        "request": request, "user": user,
        "week": week, "days": DAYS_RU,
    })


#/ ─── Homework / Домашние задания ──────────────────────────────────────────────────────
#/ Current week view + full list grouped by weeks
#/ Текущая неделя + полный список, сгруппированный по неделям
@router.get("/homework", response_class=HTMLResponse)
async def student_homework(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    enrollment = await session.execute(
        select(Enrollment).where(Enrollment.student_id == user.id)
        .options(selectinload(Enrollment.class_))
    )
    enrollment = enrollment.scalar_one_or_none()

    homeworks = []
    class_id = None
    if enrollment:
        class_id = enrollment.class_id
        result = await session.execute(
            select(Homework).where(Homework.class_id == class_id)
            .options(selectinload(Homework.subject), selectinload(Homework.teacher))
            .order_by(Homework.lesson_date.desc(), Homework.created_at.desc())
        )
        homeworks = result.scalars().all()

    today = date.today()
    #* Current week Monday-Saturday
    current_monday = today - timedelta(days=today.weekday())  # Monday of current week
    current_saturday = current_monday + timedelta(days=5)

    #* Get schedule for the class
    schedule_items = []
    if class_id:
        sched_result = await session.execute(
            select(Schedule).where(Schedule.class_id == class_id)
            .options(selectinload(Schedule.subject))
            .order_by(Schedule.day_of_week, Schedule.lesson_number)
        )
        schedule_items = sched_result.scalars().all()

    #* Index homeworks by (date, subject_id) for fast lookup
    hw_by_day_subj = {}
    for hw in homeworks:
        if hw.lesson_date:
            hw_by_day_subj[(hw.lesson_date, hw.subject_id)] = hw

    #* Build current week days
    current_week_days = []
    for dow in range(0, 6):  # Mon=0 ... Sat=5
        day_date = current_monday + timedelta(days=dow)
        grades_today = []
        if enrollment:
            g_res = await session.execute(
                select(Grade).where(
                    Grade.student_id == user.id,
                    Grade.grade_date == day_date,
                ).options(selectinload(Grade.subject))
            )
            grades_today = g_res.scalars().all()

        #* Schedule for this day_of_week (Schedule: 1=Mon ... 7=Sun)
        day_schedule = [s for s in schedule_items if s.day_of_week == dow + 1]
        schedule_with_hw = []
        for s in day_schedule:
            hw = hw_by_day_subj.get((day_date, s.subject_id))
            schedule_with_hw.append({
                "lesson_number": s.lesson_number,
                "subject_id": s.subject_id,
                "subject_name": s.subject.name if s.subject else "",
                "homework": hw,
            })

        current_week_days.append({
            "dow": dow + 1,
            "date": day_date,
            "day_ru": DAYS_RU[dow + 1],
            "schedule": schedule_with_hw,
            "grades_today": grades_today,
            "is_today": day_date == today,
        })

    #* Old format grouping (same as before)
    weeks = defaultdict(lambda: defaultdict(list))
    for hw in homeworks:
        if hw.lesson_date:
            monday = hw.lesson_date - timedelta(days=hw.lesson_date.weekday())
            dow = hw.lesson_date.weekday()
            weeks[monday][dow].append(hw)

    sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)

    return templates.TemplateResponse("student/homework.html", {
        "request": request, "user": user,
        "current_week_days": current_week_days,
        "current_monday": current_monday,
        "current_saturday": current_saturday,
        "weeks": sorted_weeks,
        "today": today,
        "days_ru": DAYS_RU,
        "timedelta": timedelta,
        "class_id": class_id,
    })


#/ ─── Analytics (performance chart) / Аналитика (график успеваемости) ──────────────────
#/ Monthly average dynamics + per-subject bar chart
#/ Динамика среднего балла по месяцам + гистограмма по предметам
@router.get("/analytics", response_class=HTMLResponse)
async def student_analytics(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get all regular grades
    grades = await session.execute(
        select(Grade).where(Grade.student_id == user.id, Grade.grade_type == "regular")
        .options(selectinload(Grade.subject))
        .order_by(Grade.grade_date)
    )
    grades = grades.scalars().all()

    #* Chart data: average grade dynamics by month
    monthly_data = defaultdict(list)
    for g in grades:
        if g.grade_date:
            key = g.grade_date.strftime("%Y-%m")
            if g.value is not None:
                monthly_data[key].append(g.value)

    chart_labels = sorted(monthly_data.keys())
    chart_values = [round(sum(monthly_data[k]) / len(monthly_data[k]), 2) for k in chart_labels]

    #* Average grade by subject (for bar chart)
    subjects_data = defaultdict(list)
    for g in grades:
        if g.value is not None:
            subjects_data[g.subject.name].append(g.value)

    radar_labels = list(subjects_data.keys())
    radar_values = [round(sum(subjects_data[k]) / len(subjects_data[k]), 2) for k in radar_labels]
    subject_grades_count = [len(subjects_data[k]) for k in radar_labels]

    return templates.TemplateResponse("student/analytics.html", {
        "request": request, "user": user,
        "chart_labels": chart_labels, "chart_values": chart_values,
        "radar_labels": radar_labels, "radar_values": radar_values,
        "subject_grades_count": subject_grades_count,
        "overall_avg": round(sum(g.value for g in grades if g.value is not None) / len([g for g in grades if g.value is not None]), 2) if grades else 0,
    })


#/ ─── Settings (change password) / Настройки (смена пароля) ────────────────────────────
#/ Password change form
#/ Форма смены пароля
@router.get("/settings", response_class=HTMLResponse)
async def student_settings_page(
    request: Request,
    user: User = Depends(require_auth),
):
    return templates.TemplateResponse("student/settings.html", {
        "request": request, "user": user
    })


#! POST /student/settings — Save new password (with validation)
#! Сохранение нового пароля (с проверкой совпадения и длины)
@router.post("/settings")
async def student_settings_save(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    form = await request.form()
    new_password = form.get("new_password", "").strip()
    confirm = form.get("confirm_password", "").strip()

    if new_password:
        if new_password != confirm:
            return templates.TemplateResponse("student/settings.html", {
                "request": request, "user": user, "error": "Пароли не совпадают"
            }, status_code=400)
        if len(new_password) < 4:
            return templates.TemplateResponse("student/settings.html", {
                "request": request, "user": user, "error": "Пароль должен быть минимум 4 символа"
            }, status_code=400)
        user.password_hash = hash_password(new_password)

    session.add(user)
    await session.commit()

    log_action(user_id=str(user.id), action="update_settings",
               details={"updated": "password" if new_password else "nothing"})

    return templates.TemplateResponse("student/settings.html", {
        "request": request, "user": user, "success": "Настройки сохранены"
    })


#/ ─── Helper functions / Вспомогательные функции ────────────────────────────────────
def _calc_age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def _get_current_trimester() -> int:
    """Determine current trimester by date."""
    month = date.today().month
    if 9 <= month <= 11:
        return 1
    elif 12 <= month <= 2:
        return 2
    else:
        return 3  #* March-May
