
#/ =====================================================================================
#/  Application entry point — main application file / Точка входа приложения
#/  Creates FastAPI app, connects templates, static files, all routers
#/  Создаёт FastAPI приложение, подключает шаблоны, статику, все роутеры
#/  On startup, initializes the DB and creates default administrator
#/  При запуске инициализирует БД и создаёт администратора по умолчанию
#/ =====================================================================================

import config
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import hash_password, add_user_to_context
from app.database import init_db, get_session, async_session
from app.models.models import User

#* ─── App ───
app = FastAPI(
    title=config.APP_NAME,
    debug=config.DEBUG,
)

#* ─── Templates ───
templates = Jinja2Templates(directory="app/templates")
from markupsafe import Markup

class Icons:
    @staticmethod
    def _svg(path, size=16):
        return Markup(f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle">{path}</svg>')

    @staticmethod
    def user(size=16):
        return Icons._svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>', size)
    @staticmethod
    def users(size=16):
        return Icons._svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>', size)
    @staticmethod
    def building(size=16):
        return Icons._svg('<rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><line x1="8" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="16" y2="14"/>', size)
    @staticmethod
    def calendar(size=16):
        return Icons._svg('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>', size)
    @staticmethod
    def bar_chart(size=16):
        return Icons._svg('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>', size)
    @staticmethod
    def trending_up(size=16):
        return Icons._svg('<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>', size)
    @staticmethod
    def megaphone(size=16):
        return Icons._svg('<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>', size)
    @staticmethod
    def file_text(size=16):
        return Icons._svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>', size)
    @staticmethod
    def book(size=16):
        return Icons._svg('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>', size)
    @staticmethod
    def clipboard(size=16):
        return Icons._svg('<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="12" y2="14"/>', size)
    @staticmethod
    def trash(size=16):
        return Icons._svg('<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>', size)
    @staticmethod
    def edit(size=16):
        return Icons._svg('<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>', size)
    @staticmethod
    def check(size=16):
        return Icons._svg('<polyline points="20 6 9 17 4 12"/>', size)
    @staticmethod
    def x_mark(size=16):
        return Icons._svg('<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>', size)
    @staticmethod
    def plus(size=16):
        return Icons._svg('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>', size)
    @staticmethod
    def message(size=16):
        return Icons._svg('<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>', size)
    @staticmethod
    def unlock(size=16):
        return Icons._svg('<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>', size)
    @staticmethod
    def lock(size=16):
        return Icons._svg('<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>', size)
    @staticmethod
    def key(size=16):
        return Icons._svg('<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>', size)
    @staticmethod
    def search(size=16):
        return Icons._svg('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>', size)
    @staticmethod
    def printer(size=16):
        return Icons._svg('<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>', size)
    @staticmethod
    def trophy(size=16):
        return Icons._svg('<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 22V14"/><path d="M14 22V14"/><path d="M18 7V4H6v3a6 6 0 0 0 12 0z"/>', size)
    @staticmethod
    def graduation(size=16):
        return Icons._svg('<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c6 3 10 0 12-2v-5"/>', size)
    @staticmethod
    def eye(size=16):
        return Icons._svg('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>', size)
    @staticmethod
    def star(size=16):
        return Icons._svg('<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>', size)
    @staticmethod
    def shield(size=16):
        return Icons._svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>', size)
    @staticmethod
    def crown(size=16):
        return Icons._svg('<path d="M2 4l3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>', size)
    @staticmethod
    def tool(size=16):
        return Icons._svg('<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>', size)
    @staticmethod
    def file(size=16):
        return Icons._svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>', size)


#* ─── 403 handler — доступ запрещён ───
@app.exception_handler(403)
async def forbidden(request: Request, exc):
    return templates.TemplateResponse("errors/403.html", {"request": request, "detail": exc.detail or "Недостаточно прав"}, status_code=403)

#* ─── 404 handler — страница не найдена ───
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)

#! ─── 500 handler — внутренняя ошибка сервера ───
#! Показывает пользователю понятную страницу вместо traceback
@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    #* Логируем ошибку в консоль для разработчика
    import traceback
    print(f"#! 500 ERROR: {exc}")
    traceback.print_exc()
    #/ Возвращаем красивую страницу с предложением вернуться на главную
    return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)
templates.env.globals.update({
    "APP_NAME": config.APP_NAME,
    "SCHOOL_NAME": config.SCHOOL_NAME,
    "SCHOOL_CITY": config.SCHOOL_CITY,
    "DEBUG": config.DEBUG,
    "lesson_times": config.get_lesson_times,
    "school_dates": config.get_schedule_school_dates(),
    "get_school_dates": config.get_schedule_school_dates,
    "icons": Icons,
})

#* ─── Static files ───
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

#* ─── Startup ───
@app.on_event("startup")
async def on_startup():
    #! Create DB tables if they don't exist
    await init_db()

    #* Create default director and admin on first run
    async with async_session() as session:
        async with session.begin():
            existing = await session.execute(select(User).where(User.role.in_(["director", "admin", "secretary"])))
            if not existing.scalars().first():
                director = User(
                    email="director@school.ru",
                    password_hash=hash_password("director123"),
                    role="director",
                    first_name="Директор",
                    last_name="Школы",
                )
                admin = User(
                    email="admin@school.ru",
                    password_hash=hash_password("admin123"),
                    role="admin",
                    first_name="Администратор",
                    last_name="Системы",
                )
                secretary = User(
                    email="secretary@school.ru",
                    password_hash=hash_password("secretary123"),
                    role="secretary",
                    first_name="Секретарь",
                    last_name="Школы",
                )
                session.add_all([director, admin, secretary])


#* ─── Routers ───
from app.routers import auth, admin, teacher, student, news, api, chat, library
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(news.router)
app.include_router(api.router)
app.include_router(chat.router)
app.include_router(library.router)


#* ─── Redirect root ───
@app.get("/")
async def root(request: Request):
    user = await add_user_to_context(request)
    user = user.get("user")
    if not user:
        return RedirectResponse(url="/login")
    if user.role == "director":
        return RedirectResponse(url="/admin/dashboard")
    elif user.role == "admin":
        return RedirectResponse(url="/admin/dashboard")
    elif user.role == "secretary":
        return RedirectResponse(url="/admin/schedule")
    elif user.role == "teacher":
        return RedirectResponse(url="/teacher/dashboard")
    else:
        return RedirectResponse(url="/student/dashboard")
