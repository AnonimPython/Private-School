#/ =====================================================================================
#/  Auth router — authentication and registration
#/  Login by email and password, logout, first account creation
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.models import User
from app.auth import (
    verify_password, create_token, hash_password,
    get_current_user, require_auth, require_role
)
from app.logger import log_action, LOGIN, LOGOUT
from app.main import templates
from pydantic import BaseModel
import config

router = APIRouter(prefix="", tags=["auth"])


#* ─── Login page ───────────────────────────────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


#! ─── Login POST — authenticate user / Аутентификация пользователя ───
@router.post("/login")
async def login(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    login_str = form.get("email", "").strip().lower()
    password = form.get("password", "")

    if not login_str or not password:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Заполните все поля"},
            status_code=400
        )

    #* Try email first, then username
    user = None
    result = await session.execute(select(User).where(User.email == login_str))
    user = result.scalar_one_or_none()
    if not user:
        result = await session.execute(select(User).where(User.username == login_str))
        user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=400
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Аккаунт деактивирован"},
            status_code=400
        )

    #* Successful login — create JWT / Успешный вход — создание JWT
    #! Store token in HTTP-only cookie / Сохранение токена в HTTP-only cookie
    token = create_token({
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
    })

    log_action(
        user_id=str(user.id),
        action=LOGIN,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400 * 30,  #* 30 days
        samesite="lax",
    )
    return response


#! ─── Demo login — instant role switch (DEMO_MODE only) ────────────────────
@router.get("/demo/login/{role}")
async def demo_login(
    role: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if not config.DEMO_MODE:
        raise HTTPException(status_code=404)
    email_map = {
        "director": "director@school.ru",
        "admin": "admin@school.ru",
        "teacher": "ivan.petrov@school.local",
        "secretary": "secretary@school.local",
    }
    email = email_map.get(role)
    if role == "student":
        result = await session.execute(select(User).where(User.role == "student"))
        student = result.scalars().first()
        if not student:
            return templates.TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "Нет демо-ученика"},
                status_code=400,
            )
        email = student.email
    if not email:
        raise HTTPException(status_code=404)
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": f"Демо-пользователь {role} не найден"},
            status_code=400,
        )
    token = create_token({
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
    })
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400 * 30,
        samesite="lax",
    )
    return response


#* ─── Logout ────────────────────────────────────────────────────────────────────────────
@router.get("/logout")
async def logout(request: Request, user: User = Depends(require_auth)):
    log_action(
        user_id=str(user.id),
        action=LOGOUT,
        ip_address=request.client.host if request.client else None,
    )
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response


#! ─── Register (admin/director only) ──────────────────────────────────────────────
class RegisterForm(BaseModel):
    email: str
    password: str
    role: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str | None = None

@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    user: User = Depends(require_role("director")),
):
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "user": user}
    )


#! ─── Register POST — create new user / Создание нового пользователя ───
@router.post("/register")
async def register(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("director")),
):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    role = form.get("role", "student")
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    middle_name = form.get("middle_name", "").strip() or None
    phone = form.get("phone", "").strip() or None

    #* Validation
    if not all([email, password, first_name, last_name]):
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "user": user, "error": "Заполните обязательные поля"},
            status_code=400
        )

    #* Check for duplicate
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "user": user, "error": "Пользователь с таким email уже существует"},
            status_code=400
        )

    #* Successful registration / Успешная регистрация
    new_user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        phone=phone,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    log_action(
        user_id=str(user.id),
        action="create_user",
        details={"target_user_id": str(new_user.id), "role": role},
        ip_address=request.client.host if request.client else None,
    )

    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "user": user, "success": f"Пользователь {email} создан"}
    )
