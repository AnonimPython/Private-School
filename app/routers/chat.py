#/ =====================================================================================
#/  Chat router — internal chat between students and teachers
#/  Text only, no photos or files. Sound notifications via Web Audio API
#/  Student → teacher (by subjects), teacher → student (reply)
#/ =====================================================================================

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.models import User, ChatMessage, TeacherAssignment, Enrollment
from app.auth import require_role, require_auth, get_current_user
from app.logger import log_action
from app.main import templates
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])


#* ─── Main chat page ───────────────────────────────────────────────────────────────────
#/ ─── GET /chat — main chat page with conversations / Главная страница чата ───
@router.get("", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get all user conversations (unique interlocutors)
    sent = await session.execute(
        select(ChatMessage).where(ChatMessage.sender_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .options(selectinload(ChatMessage.receiver))
    )
    received = await session.execute(
        select(ChatMessage).where(ChatMessage.receiver_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .options(selectinload(ChatMessage.sender))
    )

    #* Collect unique interlocutors with last message
    conversations = {}
    for msg in sent.scalars().all():
        uid = str(msg.receiver_id)
        if uid not in conversations:
            conversations[uid] = {
                "user": msg.receiver,
                "last_message": msg.message[:80],
                "last_time": msg.created_at,
                "unread": 0,
            }

    for msg in received.scalars().all():
        uid = str(msg.sender_id)
        if uid not in conversations:
            conversations[uid] = {
                "user": msg.sender,
                "last_message": msg.message[:80],
                "last_time": msg.created_at,
                "unread": 0,
            }
        #* Count unread
        if not msg.is_read:
            conversations[uid]["unread"] = conversations[uid].get("unread", 0) + 1
        #* Update time if newer
        if msg.created_at > conversations[uid]["last_time"]:
            conversations[uid]["last_message"] = msg.message[:80]
            conversations[uid]["last_time"] = msg.created_at

    #* Sort by last message time
    conversations = dict(sorted(
        conversations.items(),
        key=lambda x: x[1]["last_time"],
        reverse=True,
    ))

    #* For teacher: list of students from their classes
    students_list = []
    if user.role in ("teacher", "admin", "director"):
        if user.role == "teacher":
            assignments = await session.execute(
                select(TeacherAssignment).where(TeacherAssignment.teacher_id == user.id)
            )
            class_ids = [a.class_id for a in assignments.scalars().all()]
            if class_ids:
                students = await session.execute(
                    select(User).join(Enrollment).where(
                        Enrollment.class_id.in_(class_ids),
                        User.role == "student",
                        User.is_active == True,
                    ).distinct().order_by(User.last_name)
                )
                students_list = students.scalars().all()
        else:
            #* Admin/director: all students
            students = await session.execute(
                select(User).where(User.role == "student", User.is_active == True)
                .order_by(User.last_name)
            )
            students_list = students.scalars().all()

    #* For student: list of their teachers; for admin/director: all teachers
    teachers_list = []
    if user.role == "student":
        enrollment = await session.execute(
            select(Enrollment).where(Enrollment.student_id == user.id)
        )
        enrollment = enrollment.scalar_one_or_none()
        if enrollment:
            assignments = await session.execute(
                select(TeacherAssignment).where(TeacherAssignment.class_id == enrollment.class_id)
                .options(selectinload(TeacherAssignment.teacher), selectinload(TeacherAssignment.subject))
            )
            seen = set()
            for a in assignments.scalars().all():
                if a.teacher_id not in seen:
                    seen.add(a.teacher_id)
                    teachers_list.append({"teacher": a.teacher, "subject": a.subject})
    elif user.role in ("admin", "director"):
        teachers = await session.execute(
            select(User).where(User.role == "teacher", User.is_active == True)
            .order_by(User.last_name)
        )
        for t in teachers.scalars().all():
            teachers_list.append({"teacher": t, "subject": None})

    chat_tab = "students" if user.role in ("admin", "director") else None

    return templates.TemplateResponse("chat/conversations.html", {
        "request": request, "user": user,
        "conversations": conversations,
        "students_list": students_list,
        "teachers_list": teachers_list,
        "chat_tab": chat_tab,
    })


#* ─── Chat with specific user ──────────────────────────────────────────────────────────
#/ ─── GET /chat/{user_id} — chat with specific user / Чат с конкретным пользователем ───
@router.get("/{user_id}", response_class=HTMLResponse)
async def chat_with_user(
    request: Request, user_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get interlocutor
    result = await session.execute(select(User).where(User.id == user_id))
    companion = result.scalar_one_or_none()
    if not companion:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    #* Get messages between users
    messages = await session.execute(
        select(ChatMessage)
        .where(
            or_(
                and_(ChatMessage.sender_id == user.id, ChatMessage.receiver_id == user_id),
                and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == user.id),
            )
        )
        .options(selectinload(ChatMessage.sender))
        .order_by(ChatMessage.created_at)
    )
    messages = messages.scalars().all()

    #* Mark messages as read
    unread = await session.execute(
        select(ChatMessage).where(
            ChatMessage.receiver_id == user.id,
            ChatMessage.sender_id == user_id,
            ChatMessage.is_read == False,
        )
    )
    for msg in unread.scalars().all():
        msg.is_read = True
    await session.commit()

    #* Also get conversation list for sidebar (like on main chat page)
    #* (so you can switch between them)
    sent = await session.execute(
        select(ChatMessage).where(ChatMessage.sender_id == user.id).order_by(ChatMessage.created_at.desc())
        .options(selectinload(ChatMessage.receiver))
    )
    received = await session.execute(
        select(ChatMessage).where(ChatMessage.receiver_id == user.id).order_by(ChatMessage.created_at.desc())
        .options(selectinload(ChatMessage.sender))
    )
    conversations = {}
    for msg in sent.scalars().all():
        uid = str(msg.receiver_id)
        if uid not in conversations:
            conversations[uid] = {"user": msg.receiver, "last_message": msg.message[:80], "last_time": msg.created_at, "unread": 0}
    for msg in received.scalars().all():
        uid = str(msg.sender_id)
        if uid not in conversations:
            conversations[uid] = {"user": msg.sender, "last_message": msg.message[:80], "last_time": msg.created_at, "unread": 0}
        if not msg.is_read and msg.sender_id != user.id:
            conversations[uid]["unread"] = conversations[uid].get("unread", 0) + 1

    #* Contacts for new conversation
    students_list = []
    teachers_list = []
    if user.role in ("teacher", "admin", "director"):
        if user.role == "teacher":
            assignments = await session.execute(select(TeacherAssignment).where(TeacherAssignment.teacher_id == user.id))
            class_ids = [a.class_id for a in assignments.scalars().all()]
            if class_ids:
                students = await session.execute(select(User).join(Enrollment).where(
                    Enrollment.class_id.in_(class_ids), User.role == "student", User.is_active == True).distinct().order_by(User.last_name))
                students_list = students.scalars().all()
        else:
            students = await session.execute(select(User).where(User.role == "student", User.is_active == True).order_by(User.last_name))
            students_list = students.scalars().all()
    if user.role == "student":
        enrollment = await session.execute(select(Enrollment).where(Enrollment.student_id == user.id))
        enrollment = enrollment.scalar_one_or_none()
        if enrollment:
            assignments = await session.execute(select(TeacherAssignment).where(
                TeacherAssignment.class_id == enrollment.class_id).options(selectinload(TeacherAssignment.teacher), selectinload(TeacherAssignment.subject)))
            seen = set()
            for a in assignments.scalars().all():
                if a.teacher_id not in seen:
                    seen.add(a.teacher_id)
                    teachers_list.append({"teacher": a.teacher, "subject": a.subject})
    elif user.role in ("admin", "director"):
        teachers = await session.execute(select(User).where(User.role == "teacher", User.is_active == True).order_by(User.last_name))
        for t in teachers.scalars().all():
            teachers_list.append({"teacher": t, "subject": None})

    chat_tab = "students" if user.role in ("admin", "director") else None

    return templates.TemplateResponse("chat/conversations.html", {
        "request": request, "user": user,
        "conversations": conversations,
        "messages": messages,
        "companion": companion,
        "students_list": students_list,
        "teachers_list": teachers_list,
        "chat_tab": chat_tab,
    })


#* ─── Send message ─────────────────────────────────────────────────────────────────────
#! ─── POST /chat/{user_id}/send — send a message / Отправка сообщения ───
@router.post("/{user_id}/send")
async def send_message(
    request: Request, user_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    form = await request.form()
    message_text = form.get("message", "").strip()

    if not message_text:
        return RedirectResponse(url=f"/chat/{user_id}", status_code=302)

    msg = ChatMessage(
        sender_id=user.id,
        receiver_id=user_id,
        message=message_text,
    )
    session.add(msg)
    await session.commit()

    log_action(user_id=str(user.id), action="send_message",
               details={"receiver_id": user_id, "preview": message_text[:50]})

    return RedirectResponse(url=f"/chat/{user_id}", status_code=302)


#* ─── API: get new messages (for polling) ─────────────────────────────────────
#/ ─── GET /chat/api/messages/new — polling endpoint for new messages / Получение новых сообщений ───
@router.get("/api/messages/new")
async def get_new_messages(
    request: Request,
    after: str = "",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    #* Get unread messages
    query = select(ChatMessage).where(
        ChatMessage.receiver_id == user.id,
        ChatMessage.is_read == False,
    ).options(selectinload(ChatMessage.sender)).order_by(ChatMessage.created_at)

    if after:
        try:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.where(ChatMessage.created_at > after_dt)
        except ValueError:
            pass

    result = await session.execute(query)
    messages = result.scalars().all()

    #* Mark as read (but not immediately, so sound can play)
    #* Mark them in the next request

    return JSONResponse([
        {
            "id": str(m.id),
            "sender_id": str(m.sender_id),
            "sender_name": f"{m.sender.first_name} {m.sender.last_name}",
            "message": m.message,
            "time": m.created_at.isoformat(),
            "is_read": m.is_read,
        }
        for m in messages
    ])


#* ─── API: unread count ────────────────────────────────────────────────────
#/ ─── GET /chat/api/unread-count — unread messages count / Количество непрочитанных ───
@router.get("/api/unread-count")
async def unread_count(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    count = await session.execute(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.receiver_id == user.id,
            ChatMessage.is_read == False,
        )
    )
    return JSONResponse({"unread": count.scalar() or 0})


#* ─── API: mark as read ───────────────────────────────────────────────────
#! ─── POST /chat/api/mark-read/{sender_id} — mark messages as read / Отметить как прочитанные ───
@router.post("/api/mark-read/{sender_id}")
async def mark_as_read(
    request: Request, sender_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    await session.execute(
        select(ChatMessage).where(
            ChatMessage.receiver_id == user.id,
            ChatMessage.sender_id == sender_id,
            ChatMessage.is_read == False,
        )
    )
    #! SQLModel update — use execute with update
    from sqlalchemy import update
    await session.execute(
        update(ChatMessage)
        .where(
            ChatMessage.receiver_id == user.id,
            ChatMessage.sender_id == sender_id,
        )
        .values(is_read=True)
    )
    await session.commit()
    return JSONResponse({"ok": True})
