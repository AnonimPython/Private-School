"""
Seed script — generates test data: classes, subjects, teachers, students,
enrollments, homework entries, and grades.

Run:  python seed_data.py
"""

import asyncio
import random
import sys
sys.path.insert(0, ".")

from datetime import date, datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select
from app.models.models import User, Class, Subject, Enrollment, TeacherAssignment, Schedule, Homework, Grade, News, ChatMessage, SQLModel
from app.auth import hash_password
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        #* ─── Subjects ────────────────────────────────────────────────────
        subjects_data = [
            "Математика", "Русский язык", "Литература", "Английский язык",
            "Физика", "Химия", "Биология", "История",
            "Обществознание", "География", "Информатика", "Физкультура",
        ]
        result = await session.execute(select(Subject))
        existing_names = {s.name for s in result.scalars().all()}
        for name in subjects_data:
            if name not in existing_names:
                session.add(Subject(name=name))
        await session.commit()

        result = await session.execute(select(Subject))
        subjects = result.scalars().all()

        #* ─── Classes ─────────────────────────────────────────────────────
        from config import get_academic_year
        ac_year = get_academic_year()
        ac_year_str = f"{ac_year[0]}/{ac_year[1]}"
        classes_data = [
            ("5А", 5), ("5Б", 5), ("6А", 6), ("6Б", 6),
            ("7А", 7), ("7Б", 7), ("8А", 8), ("8Б", 8),
        ]
        result = await session.execute(select(Class))
        existing_class_names = {c.name for c in result.scalars().all()}
        for name, level in classes_data:
            if name not in existing_class_names:
                session.add(Class(name=name, grade_level=level, academic_year=ac_year_str))
        await session.commit()

        result = await session.execute(select(Class))
        classes = result.scalars().all()

        #* ─── Teachers (1 teacher = 1 subject) ────────────────────────────
        teacher_data = [
            ("Иван", "Петров", "Сергеевич", "ivan.petrov", "Учитель математики"),
            ("Мария", "Сидорова", "Алексеевна", "maria.sidorova", "Учитель русского языка"),
            ("Алексей", "Иванов", "Николаевич", "aleksey.ivanov", "Учитель физики"),
            ("Елена", "Козлова", "Дмитриевна", "elena.kozlova", "Учитель химии"),
            ("Дмитрий", "Соколов", "Олегович", "dmitry.sokolov", "Учитель истории"),
            ("Ольга", "Новикова", "Павловна", "olga.novikova", "Учитель английского языка"),
            ("Сергей", "Морозов", "Владимирович", "sergey.morozov", "Учитель географии"),
            ("Анна", "Волкова", "Игоревна", "anna.volkova", "Учитель физкультуры"),
            ("Наталья", "Белова", "Михайловна", "natalya.belova", "Учитель литературы"),
            ("Павел", "Зайцев", "Викторович", "pavel.zaytsev", "Учитель биологии"),
            ("Светлана", "Григорьева", "Андреевна", "svetlana.grigoreva", "Учитель обществознания"),
            ("Максим", "Тимофеев", "Игоревич", "maksim.timofeev", "Учитель информатики"),
        ]
        result = await session.execute(select(User).where(User.role == "teacher"))
        existing_teachers = {t.username for t in result.scalars().all()}
        teachers = []
        for first, last, middle, username, position in teacher_data:
            if username not in existing_teachers:
                t = User(
                    first_name=first, last_name=last, middle_name=middle,
                    email=f"{username}@school.local",
                    username=username, role="teacher",
                    password_hash=hash_password("teacher123"),
                    staff_position=position,
                    is_active=True,
                )
                session.add(t)
        await session.commit()

        result = await session.execute(select(User).where(User.role == "teacher"))
        teachers = result.scalars().all()

        #* ─── Secretary ────────────────────────────────────────────────────
        result = await session.execute(select(User).where(User.role == "secretary"))
        if not result.scalar_one_or_none():
            session.add(User(
                email="secretary@school.local",
                username="secretary",
                first_name="Секретарь", last_name="Школы",
                role="secretary",
                password_hash=hash_password("secretary123"),
                is_active=True,
            ))
            await session.commit()

        #* ─── Students ────────────────────────────────────────────────────
        result = await session.execute(select(User).where(User.role == "student"))
        existing_students = {s.username for s in result.scalars().all()}

        student_data = []
        for class_ in classes:
            for i in range(5):
                first = random.choice(["Александр", "Максим", "Артём", "Даниил", "Дмитрий",
                                        "Кирилл", "Никита", "Илья", "Матвей", "Роман",
                                        "Анастасия", "Дарья", "Полина", "Виктория", "София",
                                        "Алиса", "Екатерина", "Ксения", "Валерия", "Ульяна"])
                last = random.choice(["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
                                       "Попов", "Лебедев", "Козлов", "Новиков", "Морозов",
                                       "Волков", "Зайцев", "Соловьёв", "Васильев", "Павлов",
                                       "Семёнов", "Голубев", "Виноградов", "Белов", "Тимофеев"])
                middle = random.choice(["Алексеевич", "Дмитриевич", "Сергеевич", "Иванович",
                                         "Андреевич", "Максимович", "Павловна", "Сергеевна",
                                         "Алексеевна", "Дмитриевна"])
                username = f"{last.lower()}.{first.lower()}.{i+1}"
                student_data.append((first, last, middle, username, class_))

        students = []
        for first, last, middle, username, class_ in student_data:
            result = await session.execute(select(User).where(User.username == username))
            s = result.scalar_one_or_none()
            if not s:
                s = User(
                    first_name=first, last_name=last, middle_name=middle,
                    email=f"{username}@school.local",
                    username=username, role="student",
                    password_hash=hash_password("student123"),
                    is_active=True,
                )
                session.add(s)
                await session.flush()

            result = await session.execute(
                select(Enrollment).where(Enrollment.student_id == s.id, Enrollment.class_id == class_.id)
            )
            if not result.scalar_one_or_none():
                session.add(Enrollment(student_id=s.id, class_id=class_.id))
            students.append(s)
        await session.commit()

        #* ─── Assign teachers to subjects (1 teacher = 1 subject) ─────────
        subject_teacher_map = {
            "Математика": "ivan.petrov",
            "Русский язык": "maria.sidorova",
            "Литература": "natalya.belova",
            "Английский язык": "olga.novikova",
            "Физика": "aleksey.ivanov",
            "Информатика": "maksim.timofeev",
            "Химия": "elena.kozlova",
            "Биология": "pavel.zaytsev",
            "История": "dmitry.sokolov",
            "Обществознание": "svetlana.grigoreva",
            "География": "sergey.morozov",
            "Физкультура": "anna.volkova",
        }
        teacher_by_username = {t.username: t for t in teachers}

        #* ─── Teacher Assignments + Schedule ─────────────────────────────
        days_of_week = list(range(1, 7))  #* 1=Mon ... 6=Sat
        lesson_numbers = [1, 2, 3, 4, 5, 6]
        for class_ in classes:
            class_subjects = random.sample(subjects, min(8, len(subjects)))
            for subject in class_subjects:
                teacher_username = subject_teacher_map.get(subject.name)
                if not teacher_username:
                    continue
                teacher = teacher_by_username.get(teacher_username)
                if not teacher:
                    continue

                result = await session.execute(
                    select(TeacherAssignment).where(
                        TeacherAssignment.class_id == class_.id,
                        TeacherAssignment.subject_id == subject.id,
                    )
                )
                if not result.scalar_one_or_none():
                    session.add(TeacherAssignment(
                        teacher_id=teacher.id, class_id=class_.id, subject_id=subject.id,
                    ))

                for _ in range(random.randint(1, 2)):
                    dow = random.choice(days_of_week)
                    lesson_num = random.choice(lesson_numbers)
                    dup = await session.execute(
                        select(Schedule).where(
                            Schedule.class_id == class_.id,
                            Schedule.subject_id == subject.id,
                            Schedule.day_of_week == dow,
                            Schedule.lesson_number == lesson_num,
                        )
                    )
                    if dup.scalar_one_or_none():
                        continue
                    #* Don't double-book a teacher
                    teacher_busy = await session.execute(
                        select(Schedule).where(
                            Schedule.teacher_id == teacher.id,
                            Schedule.day_of_week == dow,
                            Schedule.lesson_number == lesson_num,
                        )
                    )
                    if teacher_busy.scalar_one_or_none():
                        continue
                    session.add(Schedule(
                        class_id=class_.id, subject_id=subject.id,
                        teacher_id=teacher.id,
                        day_of_week=dow, lesson_number=lesson_num,
                        valid_from=date(ac_year[0], 9, 1),
                    ))
        await session.commit()

        #* ─── Homework ────────────────────────────────────────────────────
        homework_titles = [
            "Параграф 10, вопросы 1–5",
            "Упражнение 45, стр. 32",
            "Подготовка к контрольной работе",
            "Решить задачи 5–10",
            "Написать сочинение",
            "Выучить стихотворение",
            "Подготовить доклад",
            "Повторить материал темы",
            "Сделать конспект",
            "Рабочая тетрадь стр. 20–25",
        ]
        today = date.today()
        for class_ in classes:
            result = await session.execute(
                select(TeacherAssignment).where(TeacherAssignment.class_id == class_.id)
                .options(selectinload(TeacherAssignment.teacher), selectinload(TeacherAssignment.subject))
            )
            for ta in result.scalars().all():
                for _ in range(random.randint(3, 6)):
                    days_ago = random.randint(1, 30)
                    lesson_date = today - timedelta(days=days_ago)
                    if lesson_date.weekday() >= 5:
                        continue
                    title = random.choice(homework_titles)
                    result = await session.execute(
                        select(Homework).where(
                            Homework.class_id == class_.id,
                            Homework.subject_id == ta.subject_id,
                            Homework.lesson_date == lesson_date,
                        )
                    )
                    if result.scalar_one_or_none():
                        continue
                    hw = Homework(
                        class_id=class_.id,
                        subject_id=ta.subject_id,
                        teacher_id=ta.teacher_id,
                        title=title,
                        description=f"Задание на {lesson_date.strftime('%d.%m.%Y')}: {title}",
                        lesson_date=lesson_date,
                        due_date=lesson_date + timedelta(days=random.randint(1, 7)),
                    )
                    session.add(hw)
        await session.commit()

        #* ─── Grades (full year, current academic year) ────────────────────
        def get_term_for_date(d: date) -> int:
            """Autodetect term: 1=Sep-Dec, 2=Jan-Mar, 3=Apr-May"""
            if d.month >= 9:
                return 1
            if d.month <= 3:
                return 2
            return 3

        school_year_start = date(ac_year[0], 9, 1)
        school_year_end = date(ac_year[1], 5, 31)
        current = school_year_start
        school_dates = []
        while current <= school_year_end:
            if current.weekday() < 6:
                school_dates.append(current)
            current += timedelta(days=1)

        for student in students:
            result = await session.execute(
                select(Enrollment).where(Enrollment.student_id == student.id)
                .options(selectinload(Enrollment.class_))
            )
            enrolls = result.scalars().all()
            enroll = enrolls[0] if enrolls else None
            if not enroll:
                continue

            result = await session.execute(
                select(TeacherAssignment).where(TeacherAssignment.class_id == enroll.class_id)
                .options(selectinload(TeacherAssignment.subject), selectinload(TeacherAssignment.teacher))
            )
            for ta in result.scalars().all():
                n_grades = random.randint(len(school_dates) // 30, len(school_dates) // 20)
                grade_dates = random.sample(school_dates, min(n_grades, len(school_dates)))
                for gd in grade_dates:
                    #* 8% absent, 5% sick, rest regular grades
                    att = random.choices(
                        ["absent", "sick", None],
                        weights=[8, 5, 87],
                    )[0]
                    value = None
                    if att is None:
                        value = random.choices([2, 3, 4, 5], weights=[1, 3, 4, 2])[0]
                    session.add(Grade(
                        student_id=student.id,
                        subject_id=ta.subject_id,
                        teacher_id=ta.teacher_id,
                        value=value,
                        grade_type="regular",
                        term=get_term_for_date(gd),
                        grade_date=gd,
                        attendance_status=att,
                        comment=random.choice(["", "Молодец!", "Старайся лучше", "Хорошо", "Отлично", ""]),
                    ))
        await session.commit()

        print("✅ Seed data created successfully!")
        print(f"  Teachers: {len(teachers)}")
        print(f"  Students: {len(students)}")
        print(f"  Classes: {len(classes)}")
        print(f"  Subjects: {len(subjects)}")

        hw_count = await session.execute(select(Homework))
        print(f"  Homework: {len(hw_count.scalars().all())}")
        grade_count = await session.execute(select(Grade))
        print(f"  Grades: {len(grade_count.scalars().all())}")

        #* ─── News ──────────────────────────────────────────────────────────
        news_data = [
            {
                "title": "С 1 сентября! День знаний",
                "content": "Дорогие ученики, учителя и родители! Поздравляем всех с началом нового учебного года! "
                           "Торжественная линейка состоится 1 сентября в 10:00 во дворе школы. "
                           "Форма одежды — парадная. После линейки — классные часы.",
                "news_type": "event",
                "start_date": date(2024, 9, 1),
                "end_date": date(2024, 9, 1),
                "is_pinned": True,
            },
            {
                "title": "Осенние каникулы",
                "content": "Осенние каникулы продлятся с 28 октября по 4 ноября. "
                           "Желаем всем хорошо отдохнуть и набраться сил перед второй четвертью! "
                           "Выход на занятия — 5 ноября.",
                "news_type": "holiday",
                "start_date": date(2024, 10, 28),
                "end_date": date(2024, 11, 4),
                "is_pinned": False,
            },
            {
                "title": "Зимние каникулы",
                "content": "Зимние каникулы с 30 декабря по 12 января. "
                           "Ёлка в школе состоится 28 декабря в 14:00. "
                           "Приглашаются все ученики начальной и средней школы!",
                "news_type": "holiday",
                "start_date": date(2024, 12, 30),
                "end_date": date(2025, 1, 12),
                "is_pinned": False,
            },
            {
                "title": "Весенние каникулы",
                "content": "Весенние каникулы с 24 марта по 31 марта. "
                           "Последний учебный день перед каникулами — 23 марта.",
                "news_type": "holiday",
                "start_date": date(2025, 3, 24),
                "end_date": date(2025, 3, 31),
                "is_pinned": False,
            },
            {
                "title": "Дополнительные каникулы для 1 класса",
                "content": "Для учеников 1 класса установлены дополнительные каникулы "
                           "с 17 февраля по 24 февраля.",
                "news_type": "holiday",
                "start_date": date(2025, 2, 17),
                "end_date": date(2025, 2, 24),
                "is_pinned": False,
            },
            {
                "title": "Школьная олимпиада по математике",
                "content": "Приглашаем всех желающих принять участие в школьной олимпиаде по математике! "
                           "Олимпиада пройдёт 15 ноября в 14:00 в кабинете 301. "
                           "Записаться можно у своего учителя математики до 10 ноября.",
                "news_type": "event",
                "start_date": date(2024, 11, 15),
                "end_date": date(2024, 11, 15),
                "is_pinned": False,
            },
            {
                "title": "Родительское собрание",
                "content": "Общешкольное родительское собрание состоится 20 сентября в 18:00 в актовом зале. "
                           "Повестка: итоги прошлого учебного года, планы на новый учебный год, "
                           "вопросы безопасности. Явка обязательна!",
                "news_type": "announcement",
                "start_date": date(2024, 9, 20),
                "end_date": None,
                "is_pinned": False,
            },
            {
                "title": "Изменение в расписании",
                "content": "Уважаемые ученики и родители! Обратите внимание на изменения в расписании:\n"
                           "- Уроки физкультуры для 5А и 5Б переносятся на среду\n"
                           "- Вторник теперь начинается с урока английского языка для 7-х классов\n"
                           "Актуальное расписание доступно в разделе «Расписание».",
                "news_type": "announcement",
                "start_date": None,
                "end_date": None,
                "is_pinned": True,
            },
            {
                "title": "Конкурс чтецов «Золотая осень»",
                "content": "Школьный конкурс чтецов среди 5–8 классов. "
                           "Тема: стихи русских поэтов об осени. "
                           "Приём заявок до 25 октября. Конкурс состоится 30 октября в актовом зале.",
                "news_type": "event",
                "start_date": date(2024, 10, 30),
                "end_date": date(2024, 10, 30),
                "is_pinned": False,
            },
            {
                "title": "Новогодний концерт",
                "content": "Приглашаем всех на новогодний концерт, который состоится 27 декабря в 12:00. "
                           "В программе: песни, танцы, стихи и сюрпризы от учителей! "
                           "Приветствуются новогодние костюмы.",
                "news_type": "event",
                "start_date": date(2024, 12, 27),
                "end_date": date(2024, 12, 27),
                "is_pinned": False,
            },
            {
                "title": "Соревнования по футболу",
                "content": "Товарищеский матч по футболу между сборными 5–6 и 7–8 классов. "
                           "Матч состоится на школьном стадионе в пятницу в 15:00. "
                           "Приходите болеть!",
                "news_type": "event",
                "start_date": date(2025, 4, 18),
                "end_date": None,
                "is_pinned": False,
            },
            {
                "title": "День открытых дверей",
                "content": "Приглашаем будущих учеников и их родителей на День открытых дверей! "
                           "Вы сможете познакомиться с учителями, посмотреть классы и задать все вопросы. "
                           "Начало в 11:00. Предварительная запись по телефону не требуется.",
                "news_type": "announcement",
                "start_date": date(2025, 3, 15),
                "end_date": date(2025, 3, 15),
                "is_pinned": False,
            },
            {
                "title": "Последний звонок",
                "content": "Праздник Последнего звонка для выпускников 9 и 11 классов. "
                           "Торжественная линейка в 10:00. Приглашаются все ученики, учителя и родители. "
                           "После линейки — праздничный концерт и чаепитие.",
                "news_type": "event",
                "start_date": date(2025, 5, 24),
                "end_date": date(2025, 5, 24),
                "is_pinned": False,
            },
        ]

        result = await session.execute(select(User).where(User.role == "director"))
        director = result.scalar_one_or_none()
        result = await session.execute(select(User).where(User.role == "admin"))
        admin = result.scalar_one_or_none()
        author = director or admin

        if author:
            for nd in news_data:
                result = await session.execute(
                    select(News).where(News.title == nd["title"])
                )
                if not result.scalar_one_or_none():
                    session.add(News(
                        title=nd["title"],
                        content=nd["content"],
                        news_type=nd["news_type"],
                        start_date=nd["start_date"],
                        end_date=nd["end_date"],
                        is_pinned=nd["is_pinned"],
                        author_id=author.id,
                    ))
        await session.commit()

        #* ─── Chat messages ────────────────────────────────────────────────
        result = await session.execute(
            select(User).where(User.role.in_(["teacher", "director", "admin"]))
        )
        chat_users = result.scalars().all()

        result = await session.execute(select(User).where(User.role == "student"))
        all_students = result.scalars().all()

        chat_topics = [
            "Добрый день! Подскажите, когда будет совещание?",
            "Здравствуйте! Завтра урок будет по расписанию?",
            "Коллеги, напоминаю о педсовете в пятницу в 15:00.",
            "Проверьте, пожалуйста, контрольные работы 7А класса.",
            "Спасибо за подготовку к олимпиаде!",
            "Когда будут готовы журналы за триместр?",
            "Прошу сдать планы уроков на следующую неделю.",
            "Напоминаю о заполнении электронного журнала.",
            "Здравствуйте! Мой ребёнок сегодня не придет, заболел.",
            "Спасибо за проведённый открытый урок!",
        ]

        if len(chat_users) >= 2:
            existing_pairs = set()
            for _ in range(20):
                sender = random.choice(chat_users)
                receiver = random.choice([u for u in chat_users if u.id != sender.id])
                pair = (sender.id, receiver.id)
                if pair in existing_pairs:
                    continue
                existing_pairs.add(pair)
                existing_pairs.add((receiver.id, sender.id))
                message = random.choice(chat_topics)
                days_ago = random.randint(1, 30)
                created = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago, hours=random.randint(0, 12))
                session.add(ChatMessage(
                    sender_id=sender.id, receiver_id=receiver.id,
                    message=message,
                    is_read=random.choice([True, True, False]),
                    created_at=created,
                ))
        await session.commit()



        #* ─── Print summary ────────────────────────────────────────────────
        news_count = await session.execute(select(News))
        chat_count = await session.execute(select(ChatMessage))
        print(f"  News: {len(news_count.scalars().all())}")
        print(f"  Chat messages: {len(chat_count.scalars().all())}")


if __name__ == "__main__":
    asyncio.run(seed())
