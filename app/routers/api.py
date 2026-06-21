#/ =====================================================================================
#/  API router — JSON endpoints for Chart.js graphs and AJAX requests
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import User, Grade, Subject, Enrollment
from app.auth import require_auth, get_current_user
from datetime import date, datetime
from collections import defaultdict

router = APIRouter(prefix="/api", tags=["api"])


#* ─── Student grade stats ─────────────────────────────────────────────────────────────
#/ ─── GET /api/student/grade-stats — student grade chart data / Данные для графиков успеваемости ───
@router.get("/student/grade-stats")
async def student_grade_stats(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Returns JSON with student grade statistics for Chart.js."""
    if user.role != "student":
        return JSONResponse({"error": "Только для учеников"}, status_code=403)

    grades = await session.execute(
        select(Grade).where(Grade.student_id == user.id, Grade.grade_type == "regular")
        .options(selectinload(Grade.subject))
        .order_by(Grade.grade_date)
    )
    grades = grades.scalars().all()

    #* By month
    monthly = defaultdict(list)
    for g in grades:
        if g.grade_date:
            if g.value is not None:
                monthly[g.grade_date.strftime("%Y-%m")].append(g.value)
    monthly_chart = {
        "labels": sorted(monthly.keys()),
        "values": [round(sum(v)/len(v), 2) for k, v in sorted(monthly.items())],
    }

    #* By subject
    subjects = defaultdict(list)
    for g in grades:
        if g.value is not None:
            subjects[g.subject.name].append(g.value)
    subjects_chart = {
        "labels": list(subjects.keys()),
        "values": [round(sum(v)/len(v), 2) for v in subjects.values()],
    }

    return JSONResponse({
        "monthly": monthly_chart,
        "subjects": subjects_chart,
    })


#* ─── Teacher analytics data ──────────────────────────────────────────────────────────
#/ ─── GET /api/teacher/class/{class_id}/subject/{subject_id} — teacher analytics / Аналитика для учителя ───
@router.get("/teacher/class/{class_id}/subject/{subject_id}")
async def teacher_analytics_api(
    request: Request, class_id: str, subject_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Returns data for teacher charts by class/subject."""
    students = await session.execute(
        select(User).join(Enrollment).where(
            Enrollment.class_id == class_id, User.role == "student"
        ).order_by(User.last_name)
    )
    students = students.scalars().all()

    result = []
    for student in students:
        grades = await session.execute(
            select(Grade).where(
                Grade.student_id == student.id,
                Grade.subject_id == subject_id,
                Grade.grade_type == "regular",
            )
        )
        grades = grades.scalars().all()
        grades_with_val = [g for g in grades if g.value is not None]
        avg = round(sum(g.value for g in grades_with_val) / len(grades_with_val), 2) if grades_with_val else 0
        result.append({
            "name": f"{student.last_name} {student.first_name[0]}.",
            "average": avg,
            "count": len(grades_with_val),
            "all_grades": [g.value for g in grades_with_val],
        })

    return JSONResponse(result)


#* ─── Search users by name (autocomplete) ─────────────────────────────────────────────
#/ ─── GET /api/users/search — search users by name (autocomplete) / Поиск пользователей ───
@router.get("/users/search")
async def search_users(
    request: Request,
    q: str = "",
    role: str = "",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Search users by last_name or first_name, filtered by optional role."""
    if not q or len(q) < 1:
        return JSONResponse([])
    stmt = select(User).where(
        User.last_name.ilike(f"{q}%") | User.first_name.ilike(f"{q}%")
    )
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.order_by(User.last_name, User.first_name).limit(20)
    results = (await session.execute(stmt)).scalars().all()
    return JSONResponse([
        {"id": str(u.id), "name": f"{u.last_name} {u.first_name}"}
        for u in results
    ])

#* ─── Current user info ────────────────────────────────────────────────────────────────
#/ ─── GET /api/me — current user info / Информация о текущем пользователе ───
@router.get("/me")
async def api_me(request: Request, user: User = Depends(require_auth)):
    return JSONResponse({
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": f"{user.last_name} {user.first_name}",
    })
