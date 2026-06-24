#/ =====================================================================================
#/  Teacher router — teacher panel
#/  Schedule, grades, homework, analytics
#/  Full control over the academic performance of their class/subject
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import User, Class, Subject, TeacherAssignment, Schedule, Grade, Homework, Enrollment
from app.auth import require_role, require_homework_access, get_current_user
from app.logger import log_action, CREATE_GRADE, UPDATE_GRADE, DELETE_GRADE, GENERATE_YEARLY_GRADES, CREATE_HOMEWORK, UPDATE_HOMEWORK, DELETE_HOMEWORK
from app.main import templates
from datetime import date, timedelta, datetime
from calendar import weekday, day_name, monthrange
import math

router = APIRouter(prefix="/teacher", tags=["teacher"])


#* ─── Helper: days of week ───────────────────────────────────────────────────────────────
DAYS_RU = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


#/ ─── Dashboard / Панель учителя ──────────────────────────────────────────────────────
#/ Teacher's classes and subjects overview
#/ Обзор классов и предметов учителя
@router.get("/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Get teacher's assignments
    assignments = await session.execute(
        select(TeacherAssignment)
        .options(selectinload(TeacherAssignment.subject), selectinload(TeacherAssignment.class_))
        .where(TeacherAssignment.teacher_id == user.id)
    )
    assignments = assignments.scalars().all()

    #* Group by classes
    classes_dict = {}
    for a in assignments:
        cls = a.class_
        if cls.id not in classes_dict:
            classes_dict[cls.id] = {"class": cls, "subjects": []}
        classes_dict[cls.id]["subjects"].append(a.subject)

    return templates.TemplateResponse("dashboard/teacher.html", {
        "request": request, "user": user, "classes": classes_dict.values()
    })


#/ ─── Schedule / Расписание учителя ─────────────────────────────────────────────────────
#/ Weekly schedule grouped by day
#/ Расписание на неделю, сгруппированное по дням
@router.get("/schedule", response_class=HTMLResponse)
async def teacher_schedule(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    schedules = await session.execute(
        select(Schedule)
        .options(selectinload(Schedule.class_), selectinload(Schedule.subject))
        .where(Schedule.teacher_id == user.id, Schedule.valid_until.is_(None))
        .order_by(Schedule.day_of_week, Schedule.lesson_number)
    )
    schedule_list = schedules.scalars().all()

    #* Group by days of week (normalize 0-based → 1-based for compatibility with old seed data)
    is_zero_based = any(s.day_of_week == 0 for s in schedule_list)
    week = {d: [] for d in range(1, 8)}
    for s in schedule_list:
        week[(s.day_of_week + 1) if is_zero_based else s.day_of_week].append(s)

    return templates.TemplateResponse("teacher/schedule.html", {
        "request": request, "user": user, "week": week, "days": DAYS_RU
    })


#/ ─── My Classes (with subjects) / Мои классы (с предметами) ────────────────────────────
#/ List of classes the teacher teaches, grouped
#/ Список классов, которые ведёт учитель, с группировкой
@router.get("/classes", response_class=HTMLResponse)
async def teacher_classes(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    assignments = await session.execute(
        select(TeacherAssignment)
        .options(selectinload(TeacherAssignment.subject), selectinload(TeacherAssignment.class_))
        .where(TeacherAssignment.teacher_id == user.id)
    )
    assignments = assignments.scalars().all()

    #* Group by classes
    classes_dict = {}
    for a in assignments:
        cls = a.class_
        key = str(cls.id)
        if key not in classes_dict:
            classes_dict[key] = {"class": cls, "subjects": []}
        classes_dict[key]["subjects"].append({"subject": a.subject, "assignment_id": a.id})

    return templates.TemplateResponse("teacher/classes.html", {
        "request": request, "user": user, "classes": classes_dict.values()
    })


#/ ─── Class overview / Обзор класса (ученики + предметы) ────────────────────────────────
#/ Students list, subjects taught in class, access check
#/ Список учеников, предметы, проверка доступа
@router.get("/class/{class_id}", response_class=HTMLResponse)
async def class_overview(
    request: Request, class_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Get class
    class_ = (await session.execute(select(Class).where(Class.id == class_id))).scalar_one_or_none()
    if not class_:
        raise HTTPException(status_code=404)

    #* Check access (teacher must teach this class, admin/director always)
    if user.role not in ("admin", "director"):
        assignment_check = await session.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == user.id,
                TeacherAssignment.class_id == class_id,
            )
        )
        if not assignment_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="У вас нет доступа к этому классу")

    #* Get students
    students = await session.execute(
        select(User).join(Enrollment).where(
            Enrollment.class_id == class_id, User.role == "student", User.is_active == True
        )
    )
    students = students.scalars().all()
    students.sort(key=lambda u: (u.last_name or "", u.first_name or ""))
    subjects = await session.execute(
        select(Subject)
        .join(TeacherAssignment)
        .where(TeacherAssignment.class_id == class_id)
        .distinct().order_by(Subject.name)
    )
    subjects = subjects.scalars().all()

    return templates.TemplateResponse("teacher/class_detail.html", {
        "request": request, "user": user,
        "class_": class_, "students": students, "subjects": subjects,
    })


#/ ─── Grade table / Таблица оценок ──────────────────────────────────────────────────────
#/ Students + date columns + existing grades + averages
#/ Ученики + столбцы дат + существующие оценки + средние
@router.get("/class/{class_id}/subject/{subject_id}", response_class=HTMLResponse)
async def class_students(
    request: Request, class_id: str, subject_id: str,
    term: int = 0,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Check that teacher teaches this subject in this class
    if user.role not in ("admin", "director"):
        assignment = await session.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == user.id,
                TeacherAssignment.class_id == class_id,
                TeacherAssignment.subject_id == subject_id,
            )
        )
        if not assignment.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="У вас нет доступа к этому классу/предмету")

    #* Get class students
    students = await session.execute(
        select(User)
        .join(Enrollment)
        .where(Enrollment.class_id == class_id, User.role == "student", User.is_active == True)
    )
    students = students.scalars().all()
    students.sort(key=lambda u: (u.last_name or "", u.first_name or ""))

    #* Get subject and class
    subject = (await session.execute(select(Subject).where(Subject.id == subject_id))).scalar_one()
    class_ = (await session.execute(select(Class).where(Class.id == class_id))).scalar_one()

    #* Get all schedule versions for this class+subject (to determine which days had lessons)
    schedule_entries = await session.execute(
        select(Schedule).where(
            Schedule.class_id == class_id,
            Schedule.subject_id == subject_id,
        )
    )
    schedule_entries = schedule_entries.scalars().all()

    #* Generate school date columns based on schedule
    from config import get_schedule_school_dates, weekday_to_schedule_day
    all_dates = get_schedule_school_dates()

    #* For each date, check if a schedule entry was valid (matched day_of_week + valid range)
    date_columns = []
    for d in all_dates:
        dow = weekday_to_schedule_day(d)
        for s in schedule_entries:
            if s.day_of_week != dow:
                continue
            if s.valid_from and s.valid_from > d:
                continue
            if s.valid_until and s.valid_until < d:
                continue
            date_columns.append(d)
            break

    #* Get existing grades
    grade_query = select(Grade).where(
        Grade.subject_id == subject_id,
        Grade.student_id.in_([s.id for s in students]),
    )
    if term > 0:
        grade_query = grade_query.where(Grade.term == term)
    grade_query = grade_query.order_by(Grade.grade_date.desc())
    grades_result = await session.execute(grade_query)
    grades = grades_result.scalars().all()

    #* Group grades by student
    grades_by_student = {}
    for g in grades:
        sid = str(g.student_id)
        if sid not in grades_by_student:
            grades_by_student[sid] = []
        grades_by_student[sid].append(g)

    #* Calculate average grade for each student
    averages = {}
    for sid, g_list in grades_by_student.items():
        regular = [g for g in g_list if g.grade_type == "regular" and g.value is not None]
        if regular:
            avg = sum(g.value for g in regular) / len(regular)
            averages[sid] = round(avg, 2)

    #* Build date→grade map per student [{date: grade_or_none}, ...]
    grade_map = {}
    for g in grades:
        dk = g.grade_date.isoformat() if g.grade_date else ""
        key = f"{g.student_id}|{dk}"
        grade_map[key] = g

    any_grades = len(grades) > 0
    today_str = date.today().isoformat()

    #* Determine current term
    current_term = term if term > 0 else _get_current_term()

    return templates.TemplateResponse("teacher/grades.html", {
        "request": request, "user": user,
        "students": students, "subject": subject, "class_": class_,
        "grades_by_student": grades_by_student, "averages": averages,
        "term": current_term, "terms": range(1, 4),
        "date_columns": date_columns, "grade_map": grade_map,
        "any_grades": any_grades, "today": today_str,
    })


#! POST /teacher/grade/add — Add single grade + log action
#! Добавление одной оценки + логирование
@router.post("/grade/add")
async def add_grade(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    form = await request.form()
    student_id = form.get("student_id")
    subject_id = form.get("subject_id")
    class_id = form.get("class_id")
    value = float(form.get("value", 0))
    grade_type = form.get("grade_type", "regular")
    term = int(form.get("term", _get_current_term()))
    comment = form.get("comment", "").strip() or None

    if not student_id or not subject_id or not class_id or value <= 0:
        return RedirectResponse(url=f"/teacher/class/{class_id}/subject/{subject_id}", status_code=302)

    grade = Grade(
        student_id=student_id, subject_id=subject_id, teacher_id=user.id,
        value=value, grade_type=grade_type, term=term, comment=comment,
    )
    session.add(grade)
    await session.commit()

    log_action(user_id=str(user.id), action=CREATE_GRADE,
               details={"student_id": student_id, "subject_id": subject_id, "value": value, "term": term},
               ip_address=request.client.host if request.client else None)

    return RedirectResponse(url=f"/teacher/class/{class_id}/subject/{subject_id}?term={term}", status_code=302)


#! POST /teacher/grade/{grade_id}/edit — Edit grade value/attendance
#! Редактирование оценки или отметки посещаемости
@router.post("/grade/{grade_id}/edit")
async def edit_grade(
    request: Request, grade_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(Grade).where(Grade.id == grade_id))
    grade = result.scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404)

    form = await request.form()
    val = form.get("value", "").strip().lower()
    if val == "н":
        grade.value = 0
        grade.attendance_status = "absent"
    elif val == "б":
        grade.value = 0
        grade.attendance_status = "sick"
    else:
        try:
            grade.value = float(val)
        except (ValueError, TypeError):
            grade.value = None
        grade.attendance_status = None
    grade.comment = form.get("comment", "").strip() or None

    await session.commit()
    log_action(user_id=str(user.id), action=UPDATE_GRADE, details={"grade_id": grade_id, "new_value": grade.value})

    class_id = form.get("class_id")
    subject_id = form.get("subject_id")
    term = form.get("term", 0)
    return RedirectResponse(url=f"/teacher/class/{class_id}/subject/{subject_id}?term={term}", status_code=302)


#! POST /teacher/grade/batch — Batch add grades for whole class
#! Массовое выставление оценок для всего класса
@router.post("/grade/batch")
async def batch_add_grades(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    form = await request.form()
    class_id = form.get("class_id")
    subject_id = form.get("subject_id")
    term = int(form.get("term", _get_current_term()))
    grade_date_str = form.get("grade_date", "")
    batch_comment = form.get("batch_comment", "").strip()

    try:
        grade_date = datetime.strptime(grade_date_str, "%Y-%m-%d").date() if grade_date_str else date.today()
    except ValueError:
        grade_date = date.today()

    added = 0
    for key, value in form.multi_items():
        if key.startswith("grade_"):
            student_id = key[6:]  # remove "grade_" prefix
            grade_val_str = value.strip().lower()
            attendance_status = None
            grade_val = None

            if grade_val_str == "н":
                attendance_status = "absent"
                grade_val = 0
            elif grade_val_str == "б":
                attendance_status = "sick"
                grade_val = 0
            else:
                try:
                    grade_val = int(grade_val_str)
                except (ValueError, TypeError):
                    continue
                if grade_val < 1 or grade_val > 5:
                    continue

            grade = Grade(
                student_id=student_id, subject_id=subject_id,
                teacher_id=user.id, value=grade_val,
                attendance_status=attendance_status,
                grade_type="regular", term=term,
                comment=batch_comment or None, grade_date=grade_date,
            )
            session.add(grade)
            added += 1

            log_action(user_id=str(user.id), action=CREATE_GRADE,
                       details={"student_id": student_id, "subject_id": subject_id,
                               "value": grade_val or attendance_status, "term": term, "date": grade_date_str})

    await session.commit()

    return RedirectResponse(
        url=f"/teacher/class/{class_id}/subject/{subject_id}?term={term}",
        status_code=302
    )


#! POST /teacher/grade/{grade_id}/delete — Delete grade from DB
#! Удаление оценки из БД
@router.post("/grade/{grade_id}/delete")
async def delete_grade(
    request: Request, grade_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(Grade).where(Grade.id == grade_id))
    grade = result.scalar_one_or_none()
    class_id = request.query_params.get("class_id")
    subject_id = request.query_params.get("subject_id")
    if grade:
        await session.delete(grade)
        await session.commit()
        log_action(user_id=str(user.id), action=DELETE_GRADE, details={"grade_id": grade_id})

    return RedirectResponse(url=f"/teacher/class/{class_id}/subject/{subject_id}", status_code=302)


#! ─── Generate yearly grades (one click) / Годовые оценки (в один клик) ─────────────────
#! Calculates average from trimester grades, creates yearly records
#! Вычисляет среднее из триместровых оценок, создаёт годовые записи
@router.post("/class/{class_id}/subject/{subject_id}/generate-yearly")
async def generate_yearly_grades(
    request: Request, class_id: str, subject_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Get class students
    students = await session.execute(
        select(User).join(Enrollment).where(Enrollment.class_id == class_id, User.role == "student")
    )
    students = students.scalars().all()

    generated = 0
    for student in students:
        #* Calculate average across all terms (quarterly grades)
        trimester_grades = await session.execute(
            select(Grade).where(
                Grade.student_id == student.id,
                Grade.subject_id == subject_id,
                Grade.grade_type == "trimester",
            )
        )
        trimester_grades = trimester_grades.scalars().all()

        trimester_with_value = [g for g in trimester_grades if g.value is not None]
        if trimester_with_value:
            avg = sum(g.value for g in trimester_with_value) / len(trimester_with_value)
            yearly_value = round(avg)

            #* Check if yearly grade already exists
            existing = await session.execute(
                select(Grade).where(
                    Grade.student_id == student.id,
                    Grade.subject_id == subject_id,
                    Grade.grade_type == "yearly",
                )
            )
            if not existing.scalar_one_or_none():
                grade = Grade(
                    student_id=student.id, subject_id=subject_id, teacher_id=user.id,
                    value=yearly_value, grade_type="yearly", term=0,
                    comment="Годовая оценка (сформирована автоматически)",
                )
                session.add(grade)
                generated += 1

    await session.commit()

    log_action(user_id=str(user.id), action=GENERATE_YEARLY_GRADES,
               details={"class_id": class_id, "subject_id": subject_id, "generated": generated})

    return RedirectResponse(url=f"/teacher/class/{class_id}/subject/{subject_id}", status_code=302)


#/ ─── Homework / Домашние задания (календарь) ───────────────────────────────────────────
#/ Calendar view + homeworks list + schedule lookup for auto-fill
#/ Календарь + список ДЗ + подгрузка расписания для автозаполнения
@router.get("/homework", response_class=HTMLResponse)
async def teacher_homework(
    request: Request,
    month: int = 0,
    year: int = 0,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_homework_access),
):
    today = date.today()
    if not month:
        month = today.month
    if not year:
        year = today.year

    #* ── Calendar data ──
    _, days_in_month = monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()
    first_weekday = first_weekday + 1 if first_weekday < 6 else 7

    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1

    #* ── Homework for this teacher ──
    result = await session.execute(
        select(Homework)
        .options(selectinload(Homework.subject), selectinload(Homework.class_))
        .where(Homework.teacher_id == user.id)
        .order_by(Homework.lesson_date.desc(), Homework.created_at.desc())
    )
    homeworks = result.scalars().all()

    #* ── Schedule lookup by day_of_week for auto-population ──
    is_teacher_role = user.role == "teacher"
    schedule_by_dow = {}

    if is_teacher_role:
        sched_result = await session.execute(
            select(Schedule)
            .options(selectinload(Schedule.class_), selectinload(Schedule.subject))
            .where(Schedule.teacher_id == user.id)
            .order_by(Schedule.day_of_week, Schedule.lesson_number)
        )
        seen = set()
        for s in sched_result.scalars().all():
            key = (s.day_of_week, str(s.class_id), str(s.subject_id))
            if key not in seen:
                seen.add(key)
                schedule_by_dow.setdefault(s.day_of_week, []).append({
                    "class_id": str(s.class_id),
                    "class_name": s.class_.name,
                    "subject_id": str(s.subject_id),
                    "subject_name": s.subject.name,
                })

        # If no schedule entries, fall back to TeacherAssignments (available for any day)
        if not schedule_by_dow:
            assign_result = await session.execute(
                select(TeacherAssignment)
                .options(selectinload(TeacherAssignment.class_), selectinload(TeacherAssignment.subject))
                .where(TeacherAssignment.teacher_id == user.id)
            )
            seen = set()
            all_pairs = []
            for a in assign_result.scalars().all():
                key = (str(a.class_id), str(a.subject_id))
                if key not in seen:
                    seen.add(key)
                    all_pairs.append({
                        "class_id": str(a.class_id), "class_name": a.class_.name,
                        "subject_id": str(a.subject_id), "subject_name": a.subject.name,
                    })
            for dow in range(1, 8):
                schedule_by_dow[dow] = all_pairs
    else:
        # Director/admin: all classes + subjects on every day
        classes = (await session.execute(select(Class).order_by(Class.name))).scalars().all()
        subjects = (await session.execute(select(Subject).order_by(Subject.name))).scalars().all()
        all_pairs = []
        seen = set()
        for c in classes:
            for s in subjects:
                key = (str(c.id), str(s.id))
                if key not in seen:
                    seen.add(key)
                    all_pairs.append({
                        "class_id": str(c.id), "class_name": c.name,
                        "subject_id": str(s.id), "subject_name": s.name,
                    })
        for dow in range(1, 8):
            schedule_by_dow[dow] = all_pairs

    return templates.TemplateResponse("teacher/homework.html", {
        "request": request, "user": user,
        "today": today, "month": month, "year": year,
        "days_in_month": days_in_month, "first_weekday": first_weekday,
        "prev_month": prev_m, "prev_year": prev_y,
        "next_month": next_m, "next_year": next_y,
        "homeworks": homeworks,
        "schedule_by_dow": schedule_by_dow,
        "month_name": MONTHS_RU[month],
        "is_teacher": is_teacher_role,
    })


#! POST /teacher/homework/create — Create homework entry
#! Создание записи домашнего задания
@router.post("/homework/create")
async def create_homework(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_homework_access),
):
    form = await request.form()
    date_str = form.get("date")
    class_id = form.get("class_id")
    subject_id = form.get("subject_id")
    title = form.get("title", "").strip()
    description = form.get("description", "").strip() or None

    if not title or not subject_id or not class_id or not date_str:
        return RedirectResponse(url="/teacher/homework", status_code=302)

    hw = Homework(
        lesson_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
        title=title, description=description,
        subject_id=subject_id, class_id=class_id,
        teacher_id=user.id,
    )
    session.add(hw)
    await session.commit()

    log_action(user_id=str(user.id), action=CREATE_HOMEWORK,
               details={"title": title, "class_id": class_id, "subject_id": subject_id, "date": date_str})

    return RedirectResponse(url=f"/teacher/homework?month={date_str[:7].split('-')[1]}&year={date_str[:4]}", status_code=302)


#! POST /teacher/homework/{hw_id}/edit — Edit homework title/description/due date
#! Редактирование заголовка/описания/срока ДЗ
@router.post("/homework/{hw_id}/edit")
async def edit_homework(
    request: Request, hw_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_homework_access),
):
    result = await session.execute(select(Homework).where(Homework.id == hw_id))
    hw = result.scalar_one_or_none()
    if not hw:
        return RedirectResponse(url="/teacher/homework", status_code=302)

    form = await request.form()
    hw.title = form.get("title", hw.title).strip()
    hw.description = form.get("description", "").strip() or None
    due_str = form.get("due_date")
    hw.due_date = datetime.strptime(due_str, "%Y-%m-%d").date() if due_str else None

    await session.commit()
    log_action(user_id=str(user.id), action=UPDATE_HOMEWORK,
               details={"homework_id": hw_id, "title": hw.title})
    return RedirectResponse(url=f"/teacher/homework?month={hw.lesson_date.month}&year={hw.lesson_date.year}", status_code=302)


#! POST /teacher/homework/{hw_id}/delete — Delete homework
#! Удаление домашнего задания
@router.post("/homework/{hw_id}/delete")
async def delete_homework(
    request: Request, hw_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_homework_access),
):
    result = await session.execute(select(Homework).where(Homework.id == hw_id))
    hw = result.scalar_one_or_none()
    month_param = ""
    if hw:
        month_param = f"?month={hw.lesson_date.month}&year={hw.lesson_date.year}"
        await session.delete(hw)
        await session.commit()
        log_action(user_id=str(user.id), action=DELETE_HOMEWORK, details={"homework_id": hw_id})
    return RedirectResponse(url=f"/teacher/homework{month_param}", status_code=302)


#/ ─── Analytics / Аналитика успеваемости ────────────────────────────────────────────────
#/ Per-student average grade chart for a class+subject
#/ Средний балл каждого ученика по классу+предмету (график)
@router.get("/analytics/{class_id}/{subject_id}", response_class=HTMLResponse)
async def teacher_analytics(
    request: Request, class_id: str, subject_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Access check
    if user.role not in ("admin", "director"):
        assignment = await session.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == user.id,
                TeacherAssignment.class_id == class_id,
                TeacherAssignment.subject_id == subject_id,
            )
        )
        if not assignment.scalar_one_or_none():
            raise HTTPException(status_code=403)

    students = await session.execute(
        select(User).join(Enrollment).where(Enrollment.class_id == class_id, User.role == "student")
    )
    students = students.scalars().all()
    students.sort(key=lambda u: u.last_name or "")

    class_ = (await session.execute(select(Class).where(Class.id == class_id))).scalar_one()
    subject = (await session.execute(select(Subject).where(Subject.id == subject_id))).scalar_one()

    #* Chart data (average grade of each student)
    chart_data = []
    for student in students:
        grades = await session.execute(
            select(Grade).where(Grade.student_id == student.id, Grade.subject_id == subject_id, Grade.grade_type == "regular")
        )
        grades = grades.scalars().all()
        grades_with_val = [g for g in grades if g.value is not None]
        avg = round(sum(g.value for g in grades_with_val) / len(grades_with_val), 2) if grades_with_val else 0
        chart_data.append({
            "name": f"{student.last_name} {student.first_name[0]}.",
            "avg": avg,
            "count": len(grades),
        })

    return templates.TemplateResponse("teacher/analytics.html", {
        "request": request, "user": user,
        "class_": class_, "subject": subject,
        "chart_data": chart_data, "students": students,
    })


#/ ─── Student profile (for teacher/director) / Профиль ученика ─────────────────────────
#/ Full student info: grades by subject, enrollment, age
#/ Полная информация об ученике: оценки по предметам, класс, возраст
@router.get("/student/{student_id}/profile", response_class=HTMLResponse)
async def teacher_view_student_profile(
    request: Request, student_id: str,
    term: int = 0,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    #* Get student
    result = await session.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student or student.role != "student":
        raise HTTPException(status_code=404)

    #* Get enrollment
    enrollment = await session.execute(
        select(Enrollment).where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.class_))
    )
    enrollment = enrollment.scalar_one_or_none()

    #* Check that teacher/director has relation to this student
    if user.role not in ("admin", "director") and enrollment:
        assignment_check = await session.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == user.id,
                TeacherAssignment.class_id == enrollment.class_id,
            )
        )
        if not assignment_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="У вас нет доступа к этому ученику")

    #* Get all subjects for this student's class
    subjects = []
    if enrollment:
        result = await session.execute(
            select(Subject)
            .join(TeacherAssignment)
            .where(TeacherAssignment.class_id == enrollment.class_id)
            .distinct().order_by(Subject.name)
        )
        subjects = result.scalars().all()

    #* Get all grades for this student
    grades_result = await session.execute(
        select(Grade).where(Grade.student_id == student.id)
        .options(selectinload(Grade.subject))
        .order_by(Grade.grade_date)
    )
    all_grades = grades_result.scalars().all()

    #* Trimester filter helper
    def _grade_in_term(g: Grade, t: int) -> bool:
        if t == 0:
            return True
        m = g.grade_date.month
        if t == 1:
            return 9 <= m <= 11
        elif t == 2:
            return 12 <= m or m <= 2
        elif t == 3:
            return 3 <= m <= 5
        return True

    #* Group grades by subject
    subject_grades = []
    for subj in subjects:
        sg = [g for g in all_grades if str(g.subject_id) == str(subj.id)]
        filtered = [g for g in sg if _grade_in_term(g, term)]
        regular = [g for g in filtered if g.grade_type == "regular" and g.value is not None]
        avg = round(sum(g.value for g in regular) / len(regular), 2) if regular else 0
        subject_grades.append({
            "subject": subj,
            "grades": filtered,
            "average": avg,
            "count": len(filtered),
        })

    log_action(user_id=str(user.id), action="view_student_profile", details={"student_id": student_id})

    return templates.TemplateResponse("teacher/student_profile.html", {
        "request": request, "user": user,
        "student": student, "enrollment": enrollment,
        "subject_grades": subject_grades,
        "current_term": term,
        "age": _calc_age(student.date_of_birth) if student.date_of_birth else None,
    })


#/ ─── Helpers / Вспомогательные функции ──────────────────────────────────────────────────
def _get_current_term() -> int:
    """Determine trimester number by current date (1-3)."""
    month = date.today().month
    if 9 <= month <= 11:
        return 1
    elif 12 <= month <= 2:
        return 2
    else:
        return 3  #* March-May

def _calc_age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
