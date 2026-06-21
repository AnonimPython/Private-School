
#/ =====================================================================================
#/  Authentication module — authentication and authorization
#/  JWT in HTTP-only cookies, password hashing via bcrypt
#/  Roles: director > admin > teacher > student
#/ =====================================================================================

#/ ─── Imports / Импорты ───
import config
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import async_session, get_session
from app.models.models import User

#* ─── Password hashing ───
#! bcrypt — recommended for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#* ─── hash_password / Хеширование пароля ───
def hash_password(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)

#* ─── verify_password / Проверка пароля ───
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


#* ─── JWT ───
def create_token(data: dict) -> str:
    """Create JWT token with expiration."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRATION_HOURS)
    payload.update({"exp": expire})
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def decode_token(token: str) -> dict | None:
    """Decode JWT token. Return payload or None."""
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        return None


#* ─── Role-based helpers ───
#? Hierarchy: lower number = higher access level
#? admin has full site access, director can manage users+homework,
#? secretary only edits schedules, teacher teaches+homework
ROLE_HIERARCHY = {
    "admin": 0,
    "director": 1,
    "secretary": 2,
    "teacher": 3,
    "student": 4,
}

def role_ge(required: str) -> bool:
    """Decorator/check: user role >= required (higher or equal in hierarchy)."""
    def checker(user_role: str) -> bool:
        return ROLE_HIERARCHY.get(user_role, 99) <= ROLE_HIERARCHY.get(required, 99)
    return checker


#* ─── Dependencies for FastAPI ───

async def get_current_user(
    request: Request,
    session: AsyncSession | None = None,
) -> Optional[User]:
    """Extract the current user from JWT cookie. Returns None if not authenticated."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None

    async def _fetch(s: AsyncSession) -> User | None:
        result = await s.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        return u if (u and u.is_active) else None

    if session is not None:
        return await _fetch(session)
    async with async_session() as s:
        return await _fetch(s)


async def get_current_user_dep(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """FastAPI dependency wrapper for get_current_user."""
    return await get_current_user(request, session)


async def require_auth(user: Optional[User] = Depends(get_current_user_dep)) -> User:
    """Check that the user is authenticated. Otherwise 401."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,         detail="Необходима авторизация")
    return user


def require_role(required_role: str):
    """Dependency factory: check that user role >= required_role."""
    async def role_checker(user: User = Depends(require_auth)) -> User:
        if ROLE_HIERARCHY.get(user.role, 99) > ROLE_HIERARCHY.get(required_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для этого действия"
            )
        return user
    return role_checker


async def require_homework_access(user: User = Depends(require_auth)) -> User:
    """Admin, director and teacher can manage homework (not secretary)."""
    if user.role not in ("admin", "director", "teacher"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления домашними заданиями"
        )
    return user


#* ─── Template context processor ───
#? Adds user to the context of all Jinja2 templates
async def add_user_to_context(request: Request) -> dict:
    user = await get_current_user(request)
    return {"user": user}
