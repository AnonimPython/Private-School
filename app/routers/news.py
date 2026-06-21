#/ =====================================================================================
#/  News router — news, announcements, holidays, events
#/  Calendar: switching between months, highlighting events
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import News, User
from app.auth import require_role, require_auth, get_current_user
from app.logger import log_action, CREATE_NEWS, UPDATE_NEWS, DELETE_NEWS
from app.main import templates
from datetime import date, datetime, timedelta
from calendar import monthrange, day_name, month_name
import locale

router = APIRouter(prefix="/news", tags=["news"])

MONTHS_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Окторябрь", "Ноябрь", "Декабрь"]


#* ─── News list with calendar ──────────────────────────────────────────────────────────
#/ ─── GET /news — news list with calendar / Список новостей с календарём ───
@router.get("", response_class=HTMLResponse)
async def news_list(
    request: Request,
    month: int = 0,
    year: int = 0,
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request)
    today = date.today()

    if not month:
        month = today.month
    if not year:
        year = today.year

    #* Get news for selected month
    result = await session.execute(
        select(News)
        .options(selectinload(News.author))
        .order_by(News.is_pinned.desc(), News.created_at.desc())
    )
    all_news = result.scalars().all()

    #* Filter by month (by start date)
    month_news = [n for n in all_news if n.start_date and n.start_date.month == month and n.start_date.year == year]

    #* Calendar data
    _, days_in_month = monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  #* 0=Mon
    #* Convert to Mon=1 format
    first_weekday = first_weekday + 1 if first_weekday < 6 else 7

    #* Collect days with events
    event_days = {}
    for n in all_news:
        if n.start_date and n.start_date.year == year and n.start_date.month == month:
            day = n.start_date.day
            if day not in event_days:
                event_days[day] = []
            event_days[day].append(n)

    #* All news (not filtered by month — for the feed)
    all_news_sorted = sorted(all_news, key=lambda x: (0 if x.is_pinned else 1, x.created_at or datetime.min), reverse=True)

    #* Month navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return templates.TemplateResponse("news/list.html", {
        "request": request, "user": user,
        "news_list": all_news_sorted,
        "month_news": month_news,
        "month": month, "year": year,
        "month_name": MONTHS_RU[month],
        "days_in_month": days_in_month,
        "first_weekday": first_weekday,
        "event_days": event_days,
        "prev_month": prev_month, "prev_year": prev_year,
        "next_month": next_month, "next_year": next_year,
        "today": today,
    })

#* ─── Create news (admin/teacher) ──────────────────────────────────────────────────────
#/ ─── GET /news/create — create news form / Форма создания новости ───
@router.get("/create", response_class=HTMLResponse)
async def create_news_page(
    request: Request,
    user: User = Depends(require_role("teacher")),
):
    return templates.TemplateResponse("news/form.html", {
        "request": request, "user": user, "edit": False
    })


#! ─── POST /news/create — create news (teacher+) / Создание новости ───
@router.post("/create")
async def create_news(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    form = await request.form()
    title = form.get("title", "").strip()
    content = form.get("content", "").strip() or None
    news_type = form.get("news_type", "news")
    start_date_str = form.get("start_date", "").strip()
    end_date_str = form.get("end_date", "").strip()
    is_pinned = form.get("is_pinned", "off") == "on"

    if not title:
        return templates.TemplateResponse("news/form.html", {
            "request": request, "user": user, "edit": False,
            "error": "Заполните заголовок"
        }, status_code=400)

    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    news_item = News(
        title=title, content=content, news_type=news_type,
        start_date=start_date, end_date=end_date, is_pinned=is_pinned,
        author_id=user.id,
    )
    session.add(news_item)
    await session.commit()

    log_action(user_id=str(user.id), action=CREATE_NEWS,
               details={"title": title, "type": news_type})
    return RedirectResponse(url="/news", status_code=302)


#* ─── View single news ─────────────────────────────────────────────────────────────────
#/ ─── GET /news/{news_id} — single news detail / Просмотр новости ───
@router.get("/{news_id}", response_class=HTMLResponse)
async def news_detail(
    request: Request, news_id: str,
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request)
    result = await session.execute(
        select(News).where(News.id == news_id).options(selectinload(News.author))
    )
    news_item = result.scalar_one_or_none()
    if not news_item:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse("news/detail.html", {
        "request": request, "user": user, "news": news_item
    })


#* ─── Edit news ────────────────────────────────────────────────────────────────────────
#/ ─── GET /news/{news_id}/edit — edit news form / Форма редактирования новости ───
@router.get("/{news_id}/edit", response_class=HTMLResponse)
async def edit_news_page(
    request: Request, news_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(News).where(News.id == news_id))
    news_item = result.scalar_one_or_none()
    if not news_item:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("news/form.html", {
        "request": request, "user": user, "edit": True, "news": news_item
    })


#! ─── POST /news/{news_id}/edit — update news / Обновление новости ───
@router.post("/{news_id}/edit")
async def edit_news(
    request: Request, news_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(News).where(News.id == news_id))
    news_item = result.scalar_one_or_none()
    if not news_item:
        raise HTTPException(status_code=404)

    form = await request.form()
    news_item.title = form.get("title", news_item.title).strip()
    news_item.content = form.get("content", "").strip() or None
    news_item.news_type = form.get("news_type", news_item.news_type)
    news_item.is_pinned = form.get("is_pinned", "off") == "on"

    start_date_str = form.get("start_date", "").strip()
    if start_date_str:
        try:
            news_item.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    end_date_str = form.get("end_date", "").strip()
    if end_date_str:
        try:
            news_item.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    await session.commit()
    log_action(user_id=str(user.id), action=UPDATE_NEWS, details={"news_id": news_id})
    return RedirectResponse(url=f"/news/{news_id}", status_code=302)


#* ─── Delete news ──────────────────────────────────────────────────────────────────────
#! ─── POST /news/{news_id}/delete — delete news / Удаление новости ───
@router.post("/{news_id}/delete")
async def delete_news(
    request: Request, news_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(News).where(News.id == news_id))
    news_item = result.scalar_one_or_none()
    if news_item:
        await session.delete(news_item)
        await session.commit()
        log_action(user_id=str(user.id), action=DELETE_NEWS, details={"news_id": news_id})
    return RedirectResponse(url="/news", status_code=302)
