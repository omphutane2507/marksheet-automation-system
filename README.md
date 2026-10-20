# 📊 Marksheet Automation System

A web application that automates school exam mark sheets. Teachers enter or upload Excel marks, and grades, result analysis, and a live Chart.js dashboard update automatically.

---

## 🚀 Features

- **Multi-Tenant Architecture** — Each school is an independent organization. Admins create the school, teachers join it using the admin's username.
- **Role-Based Access** — Two roles: `Administrator` (manages the school) and `Teacher` (manages classes and marks).
- **Class & Student Management** — Create classes (e.g., Std III A), add students and subjects per class.
- **Marks Entry** — Subject-wise marks entry with absent checkbox, real-time grade preview, and validation.
- **Excel Import** — Upload a `.xlsx` file to bulk-import student marks.
- **Excel Export** — Download a fully formatted result analysis sheet per class.
- **Live Analytics Dashboard** — Chart.js powered charts:
  - Grade distribution per subject (Bar Chart)
  - Pass vs Fail ratio (Donut Chart)
  - Average marks per subject (Bar Chart)
  - Toppers list & Students needing attention
- **Configurable Grade Rules** — Edit grade boundaries (A/B/C/D/E) from the settings page.
- **REST API** — JSON endpoints for Power BI and external integrations.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 6.0+ |
| Database | PostgreSQL (SQLite fallback for dev) |
| Frontend Charts | Chart.js |
| REST API | Django REST Framework |
| Excel | openpyxl |
| Environment Config | python-dotenv |

---

## ⚙️ Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (already present — do not commit to Git):

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

DB_NAME=school_marks_db
DB_USER=school_marks_user
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```

> If `DB_NAME` is not set, the app automatically falls back to **SQLite** (`db.sqlite3`).

### 3. Set Up PostgreSQL (first time only)

Make sure PostgreSQL is running, then create the database and user:

```sql
CREATE DATABASE school_marks_db;
CREATE USER school_marks_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE school_marks_db TO school_marks_user;
```

### 4. Apply Migrations (first time only)

Creates all the required database tables:

```bash
python manage.py migrate
```

### 5. Create a Superuser (optional — for Django admin panel)

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

Open your browser at **http://127.0.0.1:8000**

---

## 📁 Project Structure

```
Main Project/
├── school_marks/          # Django project settings & URL config
│   ├── settings.py
│   └── urls.py
├── marks/                 # Core app
│   ├── models.py          # Database models
│   ├── views.py           # Page views & logic
│   ├── api_views.py       # REST API views
│   ├── urls.py            # URL routes
│   ├── forms.py           # Django forms
│   ├── serializers.py     # DRF serializers
│   ├── services/
│   │   ├── calculations.py   # Grade & result calculations
│   │   ├── excel_import.py   # Excel upload processing
│   │   └── excel_export.py   # Excel download generation
│   ├── migrations/        # Database migrations
│   └── tests/             # Unit tests
├── templates/             # HTML templates
│   ├── landing.html
│   ├── marks/             # App templates
│   └── registration/      # Login & Register templates
├── static/css/            # Stylesheet
├── manage.py
├── requirements.txt
└── .env                   # Environment variables (never commit)
```

---

## 🌐 URL Reference

| URL | Page | Auth Required |
|-----|------|:---:|
| `/` | Landing Page | ❌ |
| `/register/` | Register (Admin or Teacher) | ❌ |
| `/login/` | Login | ❌ |
| `/dashboard/` | Analytics Dashboard | ✅ |
| `/classes/` | Class List & Create | ✅ |
| `/classes/<id>/` | Class Detail & Mark Sheet | ✅ |
| `/classes/<id>/marks/` | Marks Entry Form | ✅ |
| `/classes/<id>/export/` | Download Excel Report | ✅ |
| `/upload/` | Excel Import | ✅ |
| `/settings/grade-rules/` | Grade Rule Settings | ✅ |
| `/admin/` | Django Admin Panel | ✅ (superuser) |

### REST API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/marks/flat/` | All marks as flat rows (for Power BI) |
| `GET /api/marks/students/` | Per-student summary |
| `GET /api/marks/subjects/` | Per-subject analysis |

---

## 🧩 Data Models

```
Organization  ──< UserProfile >── User
     │
     └──< ClassRoom >── AcademicYear
              │
              ├──< Student >──< Mark >──< Subject
              └──< Subject
```

- **Organization** — A school (owned by one admin)
- **UserProfile** — Extends Django's User with role (`admin` / `teacher`) and org link
- **AcademicYear** — e.g., `2022-23`
- **ClassRoom** — A class division, e.g., `Std III A (2022-23)`
- **Student** — Belongs to a ClassRoom (roll number + name)
- **Subject** — Belongs to a ClassRoom (name + max marks)
- **Mark** — A student's score in a subject (supports absent flag)
- **GradeRule** — Configurable grade boundaries (A: 90–100, B: 80–90, etc.)

---

## 📊 Grade System (Default)

| Grade | Range | Description |
|-------|-------|-------------|
| A | 90% – 100% | Excellent |
| B | 80% – 90% | Very Good |
| C | 60% – 80% | Good |
| D | 33% – 60% | Satisfactory / Pass |
| E | 0% – 33% | Needs Improvement / Fail |

Grade boundaries are fully configurable from `/settings/grade-rules/`.

---

## 👤 User Roles

### Administrator
- Registers first and creates the school (Organization)
- Shares their username with teachers
- Manages all classes, students, subjects, and grade rules

### Teacher
- Registers by entering the admin's username to join the school
- Can enter and edit marks for any class in the organization
- Can import/export Excel sheets

---

## 📝 Notes

- The `.env` file is excluded from Git via `.gitignore` — never commit it.
- `db.sqlite3` is also gitignored; only PostgreSQL data is persistent in production.
- Run `python manage.py migrate` again only when model files change.
