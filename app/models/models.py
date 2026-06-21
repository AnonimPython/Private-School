#/ =====================================================================================
#/  SQLModel table definitions — all DB tables in one place
#/  PostgreSQL schema for the school portal: users, classes, subjects,
#/  schedules, grades, homework, news
#/ =====================================================================================

from sqlmodel import SQLModel, Field, Relationship, Column, UniqueConstraint
from datetime import datetime, date, time
from typing import Optional, List, TYPE_CHECKING
import uuid

#* ════════════════════════════════════════════════════════════════════════════════════
#*  USER — user (director, admin, teacher, student)
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── User — user account (director, admin, teacher, student) / Учётная запись пользователя ───
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: Optional[str] = Field(default=None, unique=True, index=True)  #* Student login name
    password_hash: str = Field(nullable=False)
    #? Role: director, admin, teacher, student, other
    role: str = Field(nullable=False)
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    middle_name: Optional[str] = Field(default=None)       #* Patronymic
    phone: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    photo_url: Optional[str] = Field(default=None)         #* Profile photo path

    #* ─── Teacher-specific fields ────────────────────────────────────────
    labor_book_number: Optional[str] = Field(default=None)  #* Трудовая книжка
    experience_years: Optional[int] = Field(default=None)   #* Стаж работы (лет)
    salary_monthly: Optional[float] = Field(default=None, description="Monthly salary in rubles")
    hours_per_week: Optional[float] = Field(default=None, description="Weekly working hours")

    #* ─── Other Staff fields ─────────────────────────────────────────────
    staff_position: Optional[str] = Field(default=None)     #* e.g. охранник, уборщица, кухарка

    #* ─── Personal data (student's personal data) ────────────────────────────────────────
    #! This data is visible only to the student and their teachers (data protection)
    date_of_birth: Optional[date] = Field(default=None)     #* Date of birth
    address: Optional[str] = Field(default=None)            #* Residential address
    mother_name: Optional[str] = Field(default=None)        #* Mother's full name
    mother_phone: Optional[str] = Field(default=None)       #* Mother's phone
    father_name: Optional[str] = Field(default=None)        #* Father's full name
    father_phone: Optional[str] = Field(default=None)       #* Father's phone
    emergency_contact: Optional[str] = Field(default=None)  #* Emergency contact
    medical_info: Optional[str] = Field(default=None)       #* Medical information (allergies, etc.)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    homeroom_classes: List["Class"] = Relationship(
        back_populates="homeroom_teacher",
        sa_relationship_kwargs={"foreign_keys": "Class.homeroom_teacher_id"}
    )
    teacher_assignments: List["TeacherAssignment"] = Relationship(back_populates="teacher")
    grades_given: List["Grade"] = Relationship(
        back_populates="teacher",
        sa_relationship_kwargs={"foreign_keys": "Grade.teacher_id"}
    )
    grades_received: List["Grade"] = Relationship(
        back_populates="student",
        sa_relationship_kwargs={"foreign_keys": "Grade.student_id"}
    )
    enrollments: List["Enrollment"] = Relationship(back_populates="student")
    schedules: List["Schedule"] = Relationship(back_populates="teacher")
    homework_created: List["Homework"] = Relationship(back_populates="teacher")
    sent_messages: List["ChatMessage"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.sender_id"}
    )
    received_messages: List["ChatMessage"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.receiver_id"}
    )
    news_posts: List["News"] = Relationship(back_populates="author")
    library_items: List["LibraryItem"] = Relationship(back_populates="uploader")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  CLASS — class (e.g., "10А")
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Class — school class (e.g. "10А") / Школьный класс ───
class Class(SQLModel, table=True):
    __tablename__ = "classes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)                       #* "10А", "7Б"
    grade_level: int = Field(nullable=False)                #* Grades 1-11
    homeroom_teacher_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    academic_year: str = Field(default="2024/2025")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    homeroom_teacher: Optional["User"] = Relationship(back_populates="homeroom_classes")
    enrollments: List["Enrollment"] = Relationship(back_populates="class_")
    schedules: List["Schedule"] = Relationship(back_populates="class_")
    assignments: List["TeacherAssignment"] = Relationship(back_populates="class_")
    homeworks: List["Homework"] = Relationship(back_populates="class_")
    library_items: List["LibraryItem"] = Relationship(back_populates="class_")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  SUBJECT — academic subject (Mathematics, Russian, ...)
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Subject — academic subject / Учебный предмет ───
class Subject(SQLModel, table=True):
    __tablename__ = "subjects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    code: Optional[str] = Field(default=None)               #* Short code (MATH, RUS)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    schedules: List["Schedule"] = Relationship(back_populates="subject")
    grades: List["Grade"] = Relationship(back_populates="subject")
    assignments: List["TeacherAssignment"] = Relationship(back_populates="subject")
    homeworks: List["Homework"] = Relationship(back_populates="subject")
    library_items: List["LibraryItem"] = Relationship(back_populates="subject")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  TEACHER ASSIGNMENT — which teacher teaches which subject in which class
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── TeacherAssignment — teacher-subject-class mapping / Назначение учителя на предмет ───
class TeacherAssignment(SQLModel, table=True):
    __tablename__ = "teacher_assignments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    teacher_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    subject_id: uuid.UUID = Field(foreign_key="subjects.id", nullable=False)
    class_id: uuid.UUID = Field(foreign_key="classes.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    teacher: "User" = Relationship(back_populates="teacher_assignments")
    subject: "Subject" = Relationship(back_populates="assignments")
    class_: "Class" = Relationship(back_populates="assignments")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  SCHEDULE — schedule (lessons in a specific class)
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Schedule — class schedule / Расписание занятий ───
class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    class_id: uuid.UUID = Field(foreign_key="classes.id", nullable=False)
    subject_id: uuid.UUID = Field(foreign_key="subjects.id", nullable=False)
    teacher_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    day_of_week: int = Field(nullable=False)                #* 1=Mon ... 7=Sun
    lesson_number: int = Field(nullable=False)              #* Lesson sequence number
    start_time: Optional[time] = Field(default=None)
    end_time: Optional[time] = Field(default=None)
    classroom: Optional[str] = Field(default=None)          #* Classroom
    valid_from: Optional[date] = Field(default=None)
    valid_until: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    class_: "Class" = Relationship(back_populates="schedules")
    subject: "Subject" = Relationship(back_populates="schedules")
    teacher: "User" = Relationship(back_populates="schedules")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  GRADE — student grade by subject
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Grade — student grade / Оценка ученика ───
class Grade(SQLModel, table=True):
    __tablename__ = "grades"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    subject_id: uuid.UUID = Field(foreign_key="subjects.id", nullable=False)
    teacher_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    value: Optional[float] = Field(default=None)              #* 2, 3, 4, 5 (or fractional)
    #? Grade type: regular, exam, quarterly, yearly
    grade_type: str = Field(default="regular")
    term: Optional[int] = Field(default=None)               #* Term: 1-4
    attendance_status: Optional[str] = Field(default=None)   #* "absent" = Н, "sick" = Б
    comment: Optional[str] = Field(default=None)
    grade_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    student: "User" = Relationship(
        back_populates="grades_received",
        sa_relationship_kwargs={"foreign_keys": "Grade.student_id"}
    )
    subject: "Subject" = Relationship(back_populates="grades")
    teacher: "User" = Relationship(
        back_populates="grades_given",
        sa_relationship_kwargs={"foreign_keys": "Grade.teacher_id"}
    )


#* ════════════════════════════════════════════════════════════════════════════════════
#*  HOMEWORK — homework assignment
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Homework — homework assignment / Домашнее задание ───
class Homework(SQLModel, table=True):
    __tablename__ = "homework"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subject_id: uuid.UUID = Field(foreign_key="subjects.id", nullable=False)
    class_id: uuid.UUID = Field(foreign_key="classes.id", nullable=False)
    teacher_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    lesson_date: date = Field(nullable=False)
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    subject: "Subject" = Relationship(back_populates="homeworks")
    class_: "Class" = Relationship(back_populates="homeworks")
    teacher: "User" = Relationship(back_populates="homework_created")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  NEWS — news, announcements, holidays, events
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── News — news, announcements, events / Новости, объявления, события ───
class News(SQLModel, table=True):
    __tablename__ = "news"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False)
    content: Optional[str] = Field(default=None)
    #? Type: news, holiday, announcement, event
    news_type: str = Field(default="news")
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    is_pinned: bool = Field(default=False)                  #* Pinned announcement
    author_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    author: "User" = Relationship(back_populates="news_posts")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  ENROLLMENT — student's class enrollment
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── Enrollment — student-class enrollment / Зачисление ученика в класс ───
class Enrollment(SQLModel, table=True):
    __tablename__ = "enrollments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    class_id: uuid.UUID = Field(foreign_key="classes.id", nullable=False)
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    student: "User" = Relationship(back_populates="enrollments")
    class_: "Class" = Relationship(back_populates="enrollments")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  LIBRARY ITEM — uploaded PDF textbooks/materials for students
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── LibraryItem — uploaded textbook / Загруженный учебник ───
class LibraryItem(SQLModel, table=True):
    __tablename__ = "library_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    class_id: Optional[uuid.UUID] = Field(foreign_key="classes.id", default=None)
    subject_id: Optional[uuid.UUID] = Field(foreign_key="subjects.id", default=None)
    file_path: str = Field(nullable=False)
    uploaded_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class_: Optional["Class"] = Relationship(back_populates="library_items")
    subject: Optional["Subject"] = Relationship(back_populates="library_items")
    uploader: "User" = Relationship(back_populates="library_items")


#* ════════════════════════════════════════════════════════════════════════════════════
#*  CHAT MESSAGE — message between student and teacher (text only, no photos)
#* ════════════════════════════════════════════════════════════════════════════════════

#/ ─── ChatMessage — message between users / Сообщение между пользователями ───
class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sender_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    receiver_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    message: str = Field(nullable=False)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #* ─── Relationships ──────────────────────────────────────────────────────────────
    sender: "User" = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.sender_id"}
    )
    receiver: "User" = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "ChatMessage.receiver_id"}
    )
