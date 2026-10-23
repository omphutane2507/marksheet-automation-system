# EduMarks AI — Power BI Integration Guide

> **For the dashboard designer:** Everything you need to build all 5 dashboards is in this file.
> The person running the server will send you a live URL — replace `BASE_URL` everywhere below with that URL.

---

## 1. How Data Gets Into This Project

Data enters the system through **3 methods**:

### Method A — Excel File Upload (main method)
The admin or teacher uploads a `.xlsx` file from the app's **Excel Import** page.

The Excel file must have these columns:
```
Roll Number | Student Name | Subject 1 | Subject 2 | Subject 3 | ...
```
- Each column after the name is a subject
- Value = marks obtained (number) or `AB` for absent
- The system auto-creates students, subjects, and marks from the file

### Method B — Manual Entry (subject by subject)
Teachers use the **Enter Marks** page:
- Select a class → select a subject → fill in each student's marks → save

### Method C — Demo Data (for testing/Power BI)
The developer ran this command to generate sample data:
```bash
python manage.py seed_demo_data
```
This created:
- **3 Academic Years:** 2022-23, 2023-24, 2024-25
- **8 Classes:** Std III A, Std III B, Std IV A, Std IV B, Std V A, Std V B, Std VI A, Std VI B
- **30 students per class** with Indian names
- **5-6 subjects per class** (English, Hindi, Maths, Science, Social Studies, Computer)
- **Realistic marks** using statistical profiles (excellent / good / average / struggling / weak students)
- **1,170+ mark records** total

---

## 2. Data Architecture

```
Organization (School)
    |
    +-- AcademicYear (2022-23, 2023-24, 2024-25)
    |
    +-- ClassRoom (Std III A / 2024-25)
            |
            +-- Subject (Maths, 100 marks)
            |
            +-- Student (Roll 1 - Aarav Sharma)
                    |
                    +-- Mark (78.5 obtained, Grade B, Pass)
```

Each **Mark** record = one student x one subject.

---

## 3. API Endpoints (your data source for Power BI)

All endpoints require **Basic Authentication** (username + password of any registered account).

> Replace `BASE_URL` with the URL the server owner sends you.

---

### Endpoint 1 — Flat Marks (MAIN FACT TABLE)
```
GET BASE_URL/api/marks/flat/
```
**One row per student x subject** — use this as your primary data source.

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| `academic_year` | text | `2024-25` | Academic year |
| `class_name` | text | `Std IV` | Class standard |
| `division` | text | `A` | Section |
| `roll_number` | number | `12` | Student roll number |
| `student_name` | text | `Priya Sharma` | Student full name |
| `subject_name` | text | `Maths` | Subject |
| `out_of_marks` | number | `100` | Maximum marks for subject |
| `marks_obtained` | number | `78.5` | Marks scored (null if absent) |
| `is_absent` | boolean | `false` | Was student absent? |
| `percentage` | number | `78.5` | Marks as percentage |
| `grade` | text | `B` | Grade (A/B/C/D/E) |

**Filters you can add to the URL:**
```
BASE_URL/api/marks/flat/?academic_year=2024-25
BASE_URL/api/marks/flat/?class_name=Std+IV
BASE_URL/api/marks/flat/?division=A
```

---

### Endpoint 2 — Student Summary
```
GET BASE_URL/api/marks/students/
```
**One row per student (totals across all subjects).**

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| `academic_year` | text | `2024-25` | Academic year |
| `class_name` | text | `Std IV` | Class |
| `division` | text | `A` | Division |
| `roll_number` | number | `12` | Roll number |
| `student_name` | text | `Priya Sharma` | Student name |
| `total_obtained` | number | `412.5` | Sum of all subject marks |
| `total_out_of` | number | `500` | Total maximum marks |
| `overall_percentage` | number | `82.5` | Overall percentage |
| `overall_grade` | text | `B` | Overall grade |
| `is_pass` | boolean | `true` | Passed or failed |
| `present_count` | number | `5` | Subjects appeared in |
| `absent_count` | number | `0` | Subjects absent in |

---

### Endpoint 3 — Subject Analysis
```
GET BASE_URL/api/marks/subjects/
```
**One row per subject per class — grade distribution and averages.**

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| `academic_year` | text | `2024-25` | Academic year |
| `class_name` | text | `Std IV` | Class |
| `division` | text | `A` | Division |
| `subject_name` | text | `Maths` | Subject name |
| `out_of_marks` | number | `100` | Max marks |
| `total_students` | number | `30` | Total students |
| `present_count` | number | `29` | Students present |
| `absent_count` | number | `1` | Students absent |
| `pass_count` | number | `24` | Students who passed |
| `fail_count` | number | `5` | Students who failed |
| `subject_avg_marks` | number | `67.4` | Average marks |
| `subject_avg_percentage` | number | `67.4` | Average percentage |
| `subject_pass_percent` | number | `82.8` | Pass percentage |
| `grade_A` | number | `4` | Count of Grade A |
| `grade_B` | number | `7` | Count of Grade B |
| `grade_C` | number | `9` | Count of Grade C |
| `grade_D` | number | `6` | Count of Grade D |
| `grade_E` | number | `3` | Count of Grade E |
| `grade_AB` | number | `1` | Count of Absent |

---

## 4. Power BI — How to Connect

### Step 1 — Load each endpoint
In **Power BI Desktop**:
1. `Home` -> `Get Data` -> `Web`
2. Click **Advanced**
3. Enter URL (e.g. `BASE_URL/api/marks/students/`)
4. Click **OK** -> Choose **Basic** auth
   - Username: *(server owner gives you)*
   - Password: *(server owner gives you)*
5. In the navigator, click `results` -> `Convert to Table` -> expand all columns
6. Set correct data types for each column

### Step 2 — Load all 3 endpoints as separate queries
- Name them: `flat_marks`, `student_summary`, `subject_analysis`

### Step 3 — Create relationships (Model view)
```
flat_marks[student_name] ---> student_summary[student_name]
flat_marks[subject_name] ---> subject_analysis[subject_name]
```

---

## 5. The 5 Dashboards — Full Specification

---

### Dashboard 1 — School Overview
**Data source:** `student_summary`

| Visual | Type | Fields |
|--------|------|--------|
| Total Students | Card | COUNT(roll_number) |
| Overall Pass % | Card | AVERAGE(is_pass) x 100 |
| School Average % | Card | AVERAGE(overall_percentage) |
| Total Classes | Card | DISTINCTCOUNT(class_name) |
| Grade Distribution | Donut chart | overall_grade -> COUNT |
| Pass vs Fail | Donut chart | is_pass (True / False) |
| Grade bar chart | Clustered bar | X=overall_grade, Y=COUNT |
| Top 10 Students | Table | student_name, class_name, overall_percentage DESC |
| Students by class | Bar | X=class_name+division, Y=COUNT |

**Slicers:** Academic Year, Class Name, Division

---

### Dashboard 2 — Class-wise Performance
**Data source:** `student_summary`

| Visual | Type | Fields |
|--------|------|--------|
| Average % per class | Clustered bar | X=class+division, Y=AVG(overall_percentage) |
| Pass % per class | Bar | X=class+division, Y=pass rate |
| Grade breakdown | 100% Stacked bar | X=class+division, Legend=overall_grade |
| Class comparison matrix | Matrix | Rows=class_name, Cols=overall_grade, Values=COUNT |
| Lowest performing classes | Table | class_name, division, avg%, pass% ASC |

**Slicers:** Academic Year, Division

---

### Dashboard 3 — Subject Analysis
**Data source:** `subject_analysis`

| Visual | Type | Fields |
|--------|------|--------|
| Subject average % | Horizontal bar | Y=subject_name, X=subject_avg_percentage |
| Subject pass % | Bar | Y=subject_name, X=subject_pass_percent |
| Grade heatmap | Matrix | Rows=subject_name, Cols=grade_A..grade_E |
| Weakest subjects | Table | subject_name, avg%, pass% ASC |
| Present vs Absent | Stacked bar | subject_name, present_count, absent_count |

**Slicers:** Academic Year, Class Name, Division

---

### Dashboard 4 — Student Drill-Through
**Data source:** `flat_marks`

| Visual | Type | Fields |
|--------|------|--------|
| Student marks table | Table | subject_name, marks_obtained, out_of_marks, percentage, grade |
| Marks by subject | Bar | X=subject_name, Y=marks_obtained |
| Radar chart | Radar | Each axis = subject, value = percentage |
| Subject grades | Table | subject_name, grade (conditional colour) |

**Setup:** Right-click student_name in Dashboard 1 -> Add as Drill-Through
**Slicers:** Student Name, Academic Year

---

### Dashboard 5 — Year-on-Year Trends
**Data source:** `student_summary` + `subject_analysis`

| Visual | Type | Fields |
|--------|------|--------|
| Pass % trend | Line chart | X=academic_year, Y=pass rate |
| Average % trend | Line chart | X=academic_year, Y=AVG(overall_percentage) |
| Grade A count per year | Bar | X=academic_year, Y=COUNT where grade=A |
| Subject avg trend | Multi-line | X=academic_year, Y=subject_avg%, Series=subject_name |
| Year comparison matrix | Matrix | Rows=academic_year, Cols=class_name, Values=avg% |

**Slicers:** Class Name, Division, Subject Name

---

## 6. Sharing the API with Someone (ngrok)

`localhost:8000` only works on YOUR computer.
Use **ngrok** to get a public URL anyone can access.

### Install ngrok (one time)
1. Go to https://ngrok.com -> Sign up free
2. Download ngrok for Windows -> Unzip to `C:\ngrok\`
3. Copy your Authtoken from the ngrok dashboard
4. Run in terminal:
```bash
C:\ngrok\ngrok.exe config add-authtoken PASTE_YOUR_TOKEN_HERE
```

### Every time you want to share
Open **two terminals:**

**Terminal 1 — Django server:**
```bash
cd "C:\Users\LENOVO\Documents\data analytics\Main Project"
python manage.py runserver
```

**Terminal 2 — ngrok tunnel:**
```bash
C:\ngrok\ngrok.exe http 8000
```

You will see output like:
```
Forwarding    https://abc123xyz.ngrok-free.app -> http://localhost:8000
```

### Send these details to your dashboard designer:

```
Base URL  : https://abc123xyz.ngrok-free.app

Endpoint 1 (Flat Marks):
  https://abc123xyz.ngrok-free.app/api/marks/flat/

Endpoint 2 (Student Summary):
  https://abc123xyz.ngrok-free.app/api/marks/students/

Endpoint 3 (Subject Analysis):
  https://abc123xyz.ngrok-free.app/api/marks/subjects/

Auth Type : Basic Authentication
Username  : [your admin username]
Password  : [your admin password]
```

> Keep BOTH terminals running the whole time the designer is working.
> The ngrok URL changes every restart (free plan). Paid plan gives a fixed URL.

---

## 7. Summary

```
Data Flow:
  Excel Upload / Manual Entry / seed_demo_data
              |
      PostgreSQL (school_marks_db)
              |
      Django REST API (3 endpoints)
              |
      ngrok (public URL)
              |
      Power BI Web Connector (Basic Auth)
              |
      5 Power BI Dashboards
```

| Dashboard | Source | Key Insight |
|-----------|--------|-------------|
| 1. School Overview | /students/ | KPI cards, grade distribution |
| 2. Class Performance | /students/ | Class vs class comparison |
| 3. Subject Analysis | /subjects/ | Subject heatmap and averages |
| 4. Student Drill-Through | /flat/ | Per-student radar chart |
| 5. Year Trends | both | Year-on-year line charts |
