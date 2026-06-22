# School Portal — Electronic Diary

> **Русская версия:** [README-RU.md](README-RU.md)

A full-featured school management system for private schools: schedules, grades, homework, chat, library, analytics, reports.

Fully **mobile-responsive** — works on phones, tablets, and desktops out of the box.

## Why this project?

Most school management systems are either expensive SaaS (thousands of $/year), outdated, or require proprietary licenses. This project is:

- **100% free and open-source** (MIT) — no hidden fees, no per-student pricing
- **Self-hosted** — your data stays on your servers, full privacy control
- **Docker one-command deploy** — no DevOps skills needed
- **Offline-capable** — no internet dependency after setup
- **Fully customizable** — any trimester system, grading scale, lesson times, school branding

### How it helps private schools

| Problem | Solution |
|---------|----------|
| Teachers waste hours calculating grades | Auto-averages, term totals, printable reports |
| Parents can't track progress | Student analytics with Chart.js visualizations |
| Schedule conflicts | Built-in conflict detection per teacher/class |
| Paper homework gets lost | Digital assignments with due dates and filters |
| Communication chaos | Role-based chat with unread indicators |
| Expensive accounting software | Salary reports, PDF slips via ReportLab |
| Student onboarding hassle | Bulk account generation + printable login cards |

## Screenshots

![main page](screenshots/main_page.png)
*Main page*

![dark theme](screenshots/dark_theme_main_page.png)
*Dark theme*

![marks](screenshots/marks.png)
*Marks calendar*

![marks detail](screenshots/marks_detail.png)
*Marks detail view*

![schedule](screenshots/schedule.png)
*Schedule*

![homework](screenshots/home_work.png)
*Homework*

![library](screenshots/library.png)
*Library*

![library info](screenshots/library_info.png)
*Library material info*

![chat](screenshots/online_chat.png)
*Online chat*

![salary report](screenshots/salary.png)
*Salary report PDF*

![users management](screenshots/users.png)
*Users management*

![classes](screenshots/classes.png)
*Classes*

![teachers list](screenshots/teachers_list.png)
*Teachers list*

![subjects](screenshots/subject.png)
*Subject management*

![generate accounts](screenshots/generate_accounts.png)
*Generate accounts*

![pdf with logins](screenshots/generate_pdf_file_with_logins.png)
*PDF with logins*

![news](screenshots/news.png)
*News*

![assignment](screenshots/assignment.png)
*Assignment*

![all marks](screenshots/marks_detail_all.png)
*All marks*

## Features

- **Role-based access** — Admin, Director, Secretary, Teacher, Student with granular permissions
- **Grade management** — Calendar-based entries, color coding (1–5), batch save, attendance tracking (absent/sick)
- **Schedule** — Versioned timetables with conflict detection, configurable lesson times, working days
- **Homework** — Subject-tagged assignments with due dates, overdue indicators, class-wide filtering
- **Chat** — Role-based contacts, unread badges, mobile-adaptive sidebar
- **Library** — Upload PDF textbooks, inline browser viewer without download
- **Student analytics** — Chart.js (line, bar, radar, doughnut) with responsive mobile layout
- **Trimester system** — 1–4 configurable trimesters with auto-term detection
- **Reports** — School summary, class averages, salary slips with PDF export via ReportLab
- **Credentials** — Generate and print student login cards, export to DOCX
- **News** — Pinned posts, multi-type (holiday, announcement, event), start/end dates
- **Dark theme** — CSS custom properties, system-wide light/dark toggle
- **Mobile-first responsive** — Bottom navigation, touch-friendly targets (≥44px), iOS safe-area, tables → cards on small screens. Works perfectly on phones, no app store needed
- **Docker-ready** — One-command deployment with PostgreSQL + MongoDB

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/your-org/school-portal.git
cd school-portal
cp .env.example .env
docker compose -p school up -d
docker exec school-app-1 python seed_data.py
open http://localhost:8000
```

### Initial Accounts

| Role      | Email                    | Password        |
|-----------|--------------------------|-----------------|
| Director  | director@school.ru       | director123     |
| Admin     | admin@school.ru          | admin123        |
| Secretary | secretary@school.ru      | secretary123    |

**Change all passwords immediately after first login!**

### Configuration

All settings in [`config.py`](config.py) — override via `.env` or environment variables.

| Variable                  | Default       | Description                   |
|---------------------------|---------------|-------------------------------|
| `DATABASE_URL`            | PostgreSQL    | Main database                 |
| `MONGO_URL`               | MongoDB       | Action logging                |
| `JWT_SECRET`              | (change me!)  | Token signing key             |
| `SCHOOL_NAME`             | Частная школа | Display name                  |
| `LESSON_START_TIME`       | 09:00         | First lesson start            |
| `LESSON_DURATION_MINUTES` | 45            | Lesson duration               |
| `WORKING_DAYS`            | 0,1,2,3,4,5   | Mon–Sat                       |
| `TRIMESTER_COUNT`         | 3             | Number of trimesters          |

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── auth.py              # JWT + bcrypt auth
│   ├── database.py          # SQLModel + engine
│   ├── logger.py            # MongoDB action logging
│   ├── models/models.py     # 10 SQLModel tables
│   ├── routers/             # 9 route modules
│   │   ├── admin.py         # Users, classes, subjects, reports, credentials
│   │   ├── teacher.py       # Grades, homework, analytics
│   │   ├── student.py       # Student dashboard, grades, schedule
│   │   ├── auth.py          # Login/register
│   │   ├── chat.py          # Messaging
│   │   ├── library.py       # PDF upload/view
│   │   ├── news.py          # News CRUD
│   │   └── api.py           # REST endpoints
│   ├── templates/           # 40+ Jinja2 templates
│   └── static/              # CSS, JS, uploads
├── config.py                # All configuration
├── seed_data.py             # Test data generator
├── docker-compose.yml       # Docker services
├── Dockerfile               # App image
└── .env.example             # Environment template
```

## Setup & Deployment

### 1. Clone & Configure

```bash
git clone https://github.com/AnonimPython/Private-School.git
cp .env.example .env
```

Edit `.env` — set your school name, city, JWT secret, and database passwords.

### 2. Docker Deploy (any server)

```bash
docker compose -p school up -d
```

This starts 3 containers: app (FastAPI), PostgreSQL, MongoDB.

To seed test data after first launch:

```bash
docker exec school-app-1 python seed_data.py
```

### 3. Deploy to a Remote Hosting Server

**Option A — VPS with Docker (recommended)**

Connect via SSH, then:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone project
git clone https://github.com/your-org/school-portal.git
cd school-portal

# Configure
cp .env.example .env
nano .env   # set strong JWT_SECRET, DB passwords

# Launch
docker compose -p school up -d
```

Open `http://your-server-ip:8000` — done.

**Option B — Caddy / Nginx reverse proxy (for domain + HTTPS)**

Create `Caddyfile`:

```
your-school.ru {
    reverse_proxy school-app-1:8000
}
```

Then run Caddy in Docker network:

```bash
docker network ls  # find "school_default"
docker run -d --network school_default -p 80:80 -p 443:443 \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data caddy
```

**Option C — Using Docker databases locally (for development)**

The `docker-compose.yml` already includes PostgreSQL and MongoDB — your local app can connect to them as if they were installed natively.

Default connection strings for your `.env`:

```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/school_db
MONGO_URL=mongodb://localhost:27017
```

Ports are mapped to `localhost` automatically — no need to install PostgreSQL or MongoDB on your machine.

**Option D — Production hardening**

- Set `DEBUG=false` in `.env`
- Use strong `JWT_SECRET` (run `openssl rand -hex 32`)
- Set `MONGO_URL` and `DATABASE_URL` with credentials
- Restart: `docker compose -p school restart`

### 4. Docker Maintenance

```bash
# View logs
docker compose -p school logs -f app

# Rebuild after code changes
docker compose -p school up -d --build

# Reset all data (⚠️ deletes everything)
docker compose -p school down -v
docker compose -p school up -d
docker exec school-app-1 python seed_data.py

# Backup database
docker exec school-db-1 pg_dump -U postgres school_db > backup.sql
```

### 5. Manual Deploy (no Docker)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Requirements: PostgreSQL 14+ and MongoDB 6+ running locally.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLModel, SQLAlchemy async
- **Frontend:** Jinja2, custom CSS (light/dark theme), Chart.js, ReportLab (PDF)
- **Databases:** PostgreSQL (main), MongoDB (action logs)
- **Auth:** JWT (HTTP-only cookies), bcrypt
- **Deployment:** Docker, Docker Compose

## Test Accounts

After seeding (`docker exec school-app-1 python seed_data.py`), these accounts are available:

| Role      | Email                     | Password      |
|-----------|---------------------------|---------------|
| Director  | director@school.ru        | director123   |
| Admin     | admin@school.ru           | admin123      |
| Teacher   | петр.петров@school.local  | teacher123    |
| Student   | иван.иванов@school.local  | student123    |

First teacher and first student from seed data — useful for quick testing.

## License

[MIT](LICENSE)
