"""
Management command: seed_demo_data
====================================
Populates the database with realistic school data for Power BI dashboard development.

Creates:
  - 3 Academic Years  : 2022-23, 2023-24, 2024-25
  - 8 Classes          : Std III–VI with divisions A and B
  - 5–8 Subjects each  : varies per class (Math, English, Science, Hindi, etc.)
  - 30 Students per class
  - Full mark records   : realistic distribution (A→E grades, some absent, some failures)

Usage:
  python manage.py seed_demo_data
  python manage.py seed_demo_data --org "Your School Name"
  python manage.py seed_demo_data --clear   (wipe existing demo data first)
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from marks.models import (
    Organization, UserProfile, AcademicYear,
    ClassRoom, Student, Subject, Mark, GradeRule
)


# ── Realistic student names ──────────────────────────────────────────────────
FIRST_NAMES = [
    "Aarav", "Arjun", "Vihaan", "Aditya", "Sai", "Rohan", "Karan", "Dev",
    "Yash", "Nikhil", "Ananya", "Priya", "Sneha", "Riya", "Pooja", "Nisha",
    "Tanvi", "Meera", "Shreya", "Kavya", "Raj", "Omkar", "Pranav", "Kunal",
    "Sahil", "Divya", "Aditi", "Siya", "Mansi", "Komal", "Harsh", "Vivek",
    "Gaurav", "Rahul", "Vishal", "Anjali", "Neha", "Sakshi", "Bhavna", "Rutuja",
]
LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Verma", "Singh", "Joshi", "Desai", "Nair",
    "Rao", "Iyer", "Mehta", "Shah", "Gupta", "Mishra", "Pandey", "Tiwari",
    "Yadav", "Chavan", "Patil", "More", "Jadhav", "Shinde", "Kulkarni", "Salvi",
]

# ── Subjects per class level ──────────────────────────────────────────────────
SUBJECTS_BY_LEVEL = {
    "Std I":   [("English",  100), ("Hindi",    100), ("Maths",    100), ("EVS",      100)],
    "Std II":  [("English",  100), ("Hindi",    100), ("Maths",    100), ("EVS",      100)],
    "Std III": [("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("Social Studies", 100)],
    "Std IV":  [("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("Social Studies", 100)],
    "Std V":   [("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("Social Studies", 100), ("Computer", 50)],
    "Std VI":  [("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("Social Studies", 100), ("Computer", 50)],
    "Std VII": [("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("History",       100), ("Geography", 100), ("Computer", 50)],
    "Std VIII":[("English",  100), ("Hindi",    100), ("Maths",    100), ("Science",  100), ("History",       100), ("Geography", 100), ("Computer", 50)],
}

# ── Academic years to create ──────────────────────────────────────────────────
ACADEMIC_YEARS = ["2022-23", "2023-24", "2024-25"]
CURRENT_YEAR   = "2024-25"

# ── Classes to create (class_name, division) ──────────────────────────────────
CLASSES = [
    ("Std III", "A"), ("Std III", "B"),
    ("Std IV",  "A"), ("Std IV",  "B"),
    ("Std V",   "A"), ("Std V",   "B"),
    ("Std VI",  "A"), ("Std VI",  "B"),
]

# ── Mark distribution profiles ────────────────────────────────────────────────
# Different student "ability" profiles to make data realistic
PROFILES = {
    "excellent":  {"mean": 88, "std": 6,  "absent_chance": 0.00},
    "good":       {"mean": 72, "std": 10, "absent_chance": 0.01},
    "average":    {"mean": 55, "std": 12, "absent_chance": 0.02},
    "struggling": {"mean": 38, "std": 14, "absent_chance": 0.03},
    "weak":       {"mean": 24, "std": 10, "absent_chance": 0.05},
}
PROFILE_WEIGHTS = [0.15, 0.25, 0.35, 0.15, 0.10]   # distribution across 30 students


class Command(BaseCommand):
    help = "Seeds the database with realistic school demo data for Power BI dashboards."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org", type=str, default=None,
            help="Organization name to seed (default: first organization found)"
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete existing demo data before seeding"
        )
        parser.add_argument(
            "--students", type=int, default=30,
            help="Number of students per class (default: 30)"
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n  EduMarks AI -- Demo Data Seeder"))
        self.stdout.write("=" * 50)

        # -- 1. Find organization --
        org = self._get_org(options["org"])
        if not org:
            return

        self.stdout.write(f"  Organisation : {self.style.SUCCESS(org.name)}")

        # -- 2. Optionally clear existing data --
        if options["clear"]:
            self._clear_data(org)

        # -- 3. Ensure default grade rules exist --
        self._ensure_grade_rules()

        # -- 4. Create academic years --
        years = self._create_academic_years()

        # -- 5. Seed each year x class combination --
        n_students = options["students"]
        total_marks = 0

        with transaction.atomic():
            for year_obj in years:
                self.stdout.write(f"\n  Year: {year_obj.name}")
                for class_name, division in CLASSES:
                    classroom = self._get_or_create_classroom(org, class_name, division, year_obj)
                    subjects  = self._create_subjects(classroom)
                    students  = self._create_students(classroom, n_students)
                    marks_ct  = self._create_marks(students, subjects, year_obj)
                    total_marks += marks_ct
                    self.stdout.write(
                        f"    [OK] {class_name} {division}  |  "
                        f"{len(students)} students x {len(subjects)} subjects "
                        f"= {marks_ct} marks"
                    )

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] {total_marks:,} mark records created.\n"
            f"  API ready at:\n"
            f"  http://127.0.0.1:8000/api/marks/flat/\n"
            f"  http://127.0.0.1:8000/api/marks/students/\n"
            f"  http://127.0.0.1:8000/api/marks/subjects/\n"
        ))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_org(self, name):
        """Find the organization to seed into."""
        if name:
            try:
                org = Organization.objects.get(name__iexact=name)
            except Organization.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌  Organization "{name}" not found.'))
                orgs = Organization.objects.all()
                if orgs.exists():
                    self.stdout.write("Available organizations:")
                    for o in orgs:
                        self.stdout.write(f"  • {o.name}")
                else:
                    self.stdout.write("No organizations exist. Register as admin first at /register/?tab=admin")
                return None
        else:
            org = Organization.objects.first()
            if not org:
                self.stdout.write(self.style.ERROR(
                    "❌  No organizations found in the database.\n"
                    "   Register an admin account first at: http://127.0.0.1:8000/register/?tab=admin"
                ))
                return None
        return org

    def _clear_data(self, org):
        """Remove all classroom/student/mark data for this org."""
        self.stdout.write(self.style.WARNING("  ⚠  Clearing existing classroom data..."))
        classrooms = ClassRoom.objects.filter(organization=org)
        student_ids = Student.objects.filter(classroom__in=classrooms).values_list('id', flat=True)
        Mark.objects.filter(student_id__in=student_ids).delete()
        Student.objects.filter(classroom__in=classrooms).delete()
        Subject.objects.filter(classroom__in=classrooms).delete()
        classrooms.delete()
        self.stdout.write(self.style.WARNING("  ✔  Cleared."))

    def _ensure_grade_rules(self):
        """Create default grade rules if none exist."""
        if GradeRule.objects.exists():
            return
        defaults = [
            ("A", 90.0, 100.0, "Excellent"),
            ("B", 80.0,  90.0, "Very Good"),
            ("C", 60.0,  80.0, "Good"),
            ("D", 33.0,  60.0, "Satisfactory"),
            ("E",  0.0,  33.0, "Needs Improvement"),
        ]
        for grade, min_p, max_p, desc in defaults:
            GradeRule.objects.get_or_create(
                grade=grade,
                defaults={"min_percentage": min_p, "max_percentage": max_p, "description": desc}
            )

    def _create_academic_years(self):
        """Create academic years, return list of objects."""
        years = []
        for name in ACADEMIC_YEARS:
            yr, _ = AcademicYear.objects.get_or_create(
                name=name,
                defaults={"is_current": name == CURRENT_YEAR}
            )
            years.append(yr)
        return years

    def _get_or_create_classroom(self, org, class_name, division, year_obj):
        classroom, _ = ClassRoom.objects.get_or_create(
            organization=org,
            class_name=class_name,
            division=division,
            academic_year=year_obj,
            defaults={
                "class_teacher": self._random_teacher_name(),
                "pass_percentage": 33.0,
            }
        )
        return classroom

    def _create_subjects(self, classroom):
        """Create subjects for a classroom based on class level."""
        subject_defs = SUBJECTS_BY_LEVEL.get(classroom.class_name, SUBJECTS_BY_LEVEL["Std III"])
        subjects = []
        for order, (name, out_of) in enumerate(subject_defs, start=1):
            sub, _ = Subject.objects.get_or_create(
                classroom=classroom,
                name=name,
                defaults={"out_of_marks": out_of, "order": order}
            )
            subjects.append(sub)
        return subjects

    def _create_students(self, classroom, count):
        """Create students for a classroom if they don't exist."""
        existing = list(Student.objects.filter(classroom=classroom).order_by('roll_number'))
        if len(existing) >= count:
            return existing[:count]

        used_names = {s.name for s in existing}
        start_roll = len(existing) + 1
        new_students = []

        name_pool = [
            f"{fn} {ln}"
            for fn in FIRST_NAMES
            for ln in LAST_NAMES
            if f"{fn} {ln}" not in used_names
        ]
        random.shuffle(name_pool)

        for i in range(start_roll, count + 1):
            name = name_pool[i - 1] if (i - 1) < len(name_pool) else f"Student {i}"
            stud, created = Student.objects.get_or_create(
                classroom=classroom,
                roll_number=i,
                defaults={"name": name}
            )
            new_students.append(stud)

        return existing + new_students

    def _create_marks(self, students, subjects, year_obj):
        """Create realistic marks for each student × subject."""
        # Assign ability profile to each student (consistent per student)
        profile_names = list(PROFILES.keys())
        student_profiles = random.choices(profile_names, weights=PROFILE_WEIGHTS, k=len(students))

        marks_created = 0
        for stud, profile_name in zip(students, student_profiles):
            profile = PROFILES[profile_name]

            # Add year-based performance trend (slight improvement each year)
            year_boost = {"2022-23": -3, "2023-24": 0, "2024-25": 3}.get(year_obj.name, 0)

            for sub in subjects:
                # Skip if mark already exists
                if Mark.objects.filter(student=stud, subject=sub).exists():
                    continue

                is_absent = random.random() < profile["absent_chance"]

                if is_absent:
                    Mark.objects.create(student=stud, subject=sub, is_absent=True)
                else:
                    raw = random.gauss(
                        profile["mean"] + year_boost,
                        profile["std"]
                    )
                    pct = max(0.0, min(100.0, raw))
                    obtained = round((pct / 100.0) * sub.out_of_marks, 1)
                    obtained = max(0.0, min(sub.out_of_marks, obtained))
                    Mark.objects.create(
                        student=stud,
                        subject=sub,
                        marks_obtained=obtained,
                        is_absent=False
                    )
                marks_created += 1

        return marks_created

    @staticmethod
    def _random_teacher_name():
        first = random.choice(["Mr.", "Ms.", "Mrs.", "Dr."])
        last  = random.choice(LAST_NAMES)
        return f"{first} {last}"
