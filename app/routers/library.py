#/ =====================================================================================
#/  Library router — file storage for teachers (PDF materials)
#/  Библиотека — хранилище файлов для учителей (PDF материалы)
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import User, Class, Subject, LibraryItem, Enrollment, TeacherAssignment
from app.auth import require_role, require_auth
from app.logger import log_action
from app.main import templates
import config
import aiofiles
import os
import uuid as uuid_lib

router = APIRouter(prefix="/library", tags=["library"])


#/ GET /library — List/search library items
#/ Список/поиск материалов в библиотеке
@router.get("", response_class=HTMLResponse)
async def library_list(
    request: Request,
    q: str = "",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    query = select(LibraryItem).options(
        selectinload(LibraryItem.uploader),
        selectinload(LibraryItem.class_),
        selectinload(LibraryItem.subject),
    )

    #* Search filter
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where(
            or_(LibraryItem.title.ilike(like), LibraryItem.description.ilike(like))
        )

    if user.role == "student":
        enrollment = await session.execute(
            select(Enrollment).where(Enrollment.student_id == user.id)
        )
        enroll = enrollment.scalar_one_or_none()
        if enroll:
            query = query.where(
                or_(LibraryItem.class_id == enroll.class_id, LibraryItem.class_id.is_(None))
            )
    elif user.role == "teacher":
        assignments = await session.execute(
            select(TeacherAssignment).where(TeacherAssignment.teacher_id == user.id)
        )
        class_ids = list({a.class_id for a in assignments.scalars().all()})
        if class_ids:
            query = query.where(
                or_(LibraryItem.class_id.in_(class_ids), LibraryItem.class_id.is_(None))
            )

    query = query.order_by(LibraryItem.created_at.desc())
    result = await session.execute(query)
    items = result.scalars().all()

    return templates.TemplateResponse("library/list.html", {
        "request": request, "user": user, "items": items, "q": q,
    })


#/ GET /library/upload — Upload form (teachers only)
#/ Форма загрузки файла (только для учителей)
@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    classes = await session.execute(select(Class).order_by(Class.name))
    subjects = await session.execute(select(Subject).order_by(Subject.name))
    return templates.TemplateResponse("library/upload.html", {
        "request": request, "user": user,
        "classes": classes.scalars().all(),
        "subjects": subjects.scalars().all(),
    })


#! POST /library/upload — Upload PDF file + save to DB
#! Загрузка PDF-файла + сохранение в БД
@router.post("/upload")
async def upload_file(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
    title: str = Form(...),
    description: str = Form(""),
    class_id: str = Form(""),
    subject_id: str = Form(""),
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        return templates.TemplateResponse("library/upload.html", {
            "request": request, "user": user, "error": "Можно загружать только PDF файлы",
        }, status_code=400)

    lib_dir = os.path.join(config.UPLOAD_DIR, "library")
    os.makedirs(lib_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid_lib.uuid4()}{ext}"
    filepath = os.path.join(lib_dir, filename)

    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    db_path = f"/uploads/library/{filename}"

    item = LibraryItem(
        title=title,
        description=description.strip() or None,
        class_id=class_id if class_id else None,
        subject_id=subject_id if subject_id else None,
        file_path=db_path,
        uploaded_by=user.id,
    )
    session.add(item)
    await session.commit()

    log_action(user_id=str(user.id), action="library_upload",
               details={"title": title, "file": filename})

    return RedirectResponse(url="/library", status_code=302)


#/ GET /library/{item_id} — View single item details
#/ Просмотр деталей одного материала
@router.get("/{item_id}", response_class=HTMLResponse)
async def view_item(
    request: Request, item_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    result = await session.execute(
        select(LibraryItem).where(LibraryItem.id == item_id)
        .options(
            selectinload(LibraryItem.uploader),
            selectinload(LibraryItem.class_),
            selectinload(LibraryItem.subject),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse("library/view.html", {
        "request": request, "user": user, "item": item,
    })


#! POST /library/{item_id}/delete — Delete item (owner or admin only)
#! Удаление материала (только владелец или администратор)
@router.post("/{item_id}/delete")
async def delete_item(
    request: Request, item_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("teacher")),
):
    result = await session.execute(select(LibraryItem).where(LibraryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404)
    if str(item.uploaded_by) != str(user.id) and user.role not in ("admin", "director"):
        raise HTTPException(status_code=403)

    #* Delete file from disk
    rel_path = item.file_path.replace("/uploads/", "")
    full_path = os.path.join(config.UPLOAD_DIR, rel_path)
    if os.path.exists(full_path):
        os.remove(full_path)

    await session.delete(item)
    await session.commit()

    log_action(user_id=str(user.id), action="library_delete",
               details={"title": item.title})

    return RedirectResponse(url="/library", status_code=302)
