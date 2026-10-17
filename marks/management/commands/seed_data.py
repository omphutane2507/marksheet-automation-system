import random
from django.core.management.base import BaseCommand
from django.db import transaction
from marks.models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule


# ---------------------------------------------------------------------------
# Sample Data Configuration
# ---------------------------------------------------------------------------
ACADEMIC_YEARS = [
    {'name': '2022-23', 'is_current': False},
    {'name': '2023-24', 'is_current': False},
    {'name': '2024-25', 'is_current': True},
]

CLASSROOMS = [
    {'class_name': 'Std III', 'division': 'A', 'teacher': 'Mrs. Sunita Patil'},
    {'class_name': 'Std III', 'division': 'B', 'teacher': 'Mr. Rajesh Mehta'},
    {'class_name': 'Std IV',  'division': 'A', 'teacher': 'Mrs. Priya Kulkarni'},
    {'class_name': 'Std IV',  'division': 'B', 'teacher': 'Mr. Vikram Desai'},
    {'class_name': 'Std V',   'division': 'A', 'teacher': 'Mrs. Anjali Sharma'},
    {'class_name': 'Std V',   'division': 'B', 'teacher': 'Mr. Suresh Nair'},
    {'class_name': 'Std VI',  'division': 'A', 'teacher': 'Mrs. Deepa Iyer'},
    {'class_name': 'Std VII', 'division': 'A', 'teacher': 'Mr. Anil Joshi'},
]

SUBJECTS = [
    ('English',  100.0, 1),
    ('Marathi',  100.0, 2),
    ('Hindi',    100.0, 3),
    ('Maths',     100.0, 4),
    ('Science',  100.0, 5),
    ('EVS',       100.0, 6),
    ('Computer',  50.0, 7),
    ('Drawing',   50.0, 8),
]

FIRST_NAMES = [
    'Aarav', 'Bhavna', 'Chetan', 'Divya', 'Eshan', 'Fatima', 'Gaurav', 'Heena',
    'Ishaan', 'Jyoti', 'Karan', 'Lata', 'Mihir', 'Neha', 'Om', 'Pooja',
    'Rajat', 'Smita', 'Tanvi', 'Uday', 'Varsha', 'Wasim', 'Yash', 'Zara',
    'Aditya', 'Bhumi', 'Chirag', 'Deepika', 'Ekta', 'Firoz', 'Gauri', 'Harsh',
    'Ira', 'Jay', 'Kavya',
]

LAST_NAMES = [
    'Sharma', 'Patel', 'Deshmukh', 'Kulkarni', 'Verma', 'Mehta', 'Singh',
    'Joshi', 'Gupta', 'Rao', 'Iyer', 'Nair', 'Pillai', 'Reddy', 'Khan',
    'Sheikh', 'Patil', 'Shinde', 'More', 'Bhosale',
]

GRADE_RULES = [
    {'grade': 'A', 'min_percentage': 90.0, 'max_percentage': 100.0, 'description': 'Excellent'},
    {'grade': 'B', 'min_percentage': 80.0, 'max_percentage': 90.0,  'description': 'Very Good'},
    {'grade': 'C', 'min_percentage': 60.0, 'max_percentage': 80.0,  'description': 'Good'},
    {'grade': 'D', 'min_percentage': 33.0, 'max_percentage': 60.0,  'description': 'Satisfactory / Pass'},
    {'grade': 'E', 'min_percentage': 0.0,  'max_percentage': 33.0,  'description': 'Needs Improvement / Fail'},
]


def generate_mark(profile: str, out_of: float) -> float | None:
    """Generate a realistic mark based on a student performance profile."""
    profiles = {
        'excellent':    (85, 100),
        'good':         (65,  85),
        'average':      (40,  65),
        'struggling':   (20,  45),
        'failing':      (0,   33),
    }
    low, high = profiles.get(profile, (40, 80))
    raw = random.uniform(low, high)
    return round(min(raw * out_of / 100.0, out_of), 1)


class Command(BaseCommand):
    help = (
        'Seeds comprehensive sample data: 3 academic years × 8 classrooms × ~30 students each. '
        'Generates realistic marks suitable for Power BI dashboards.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing marks/student/classroom data before seeding.',
        )
        parser.add_argument(
            '--years',
            nargs='+',
            default=['2022-23', '2023-24', '2024-25'],
            help='Academic years to seed (default: all three).',
        )

    def handle(self, *args, **options):
        random.seed(42)  # Reproducible results

        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Mark.objects.all().delete()
            Student.objects.all().delete()
            ClassRoom.objects.all().delete()
            AcademicYear.objects.all().delete()
            GradeRule.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared.'))

        with transaction.atomic():
            # 1. Grade Rules
            self._seed_grade_rules()

            years_to_seed = options['years']
            total_students = 0
            total_marks = 0

            for year_cfg in ACADEMIC_YEARS:
                if year_cfg['name'] not in years_to_seed:
                    continue

                year, created = AcademicYear.objects.get_or_create(
                    name=year_cfg['name'],
                    defaults={'is_current': year_cfg['is_current']}
                )
                action = 'Created' if created else 'Found'
                self.stdout.write(f'  {action} Academic Year: {year.name}')

                for cls_cfg in CLASSROOMS:
                    classroom, _ = ClassRoom.objects.get_or_create(
                        class_name=cls_cfg['class_name'],
                        division=cls_cfg['division'],
                        academic_year=year,
                        defaults={
                            'class_teacher': cls_cfg['teacher'],
                            'pass_percentage': 33.0,
                        }
                    )

                    # Subjects
                    subject_objs = []
                    for sname, out_of, order in SUBJECTS:
                        sub, _ = Subject.objects.get_or_create(
                            classroom=classroom,
                            name=sname,
                            defaults={'out_of_marks': out_of, 'order': order}
                        )
                        subject_objs.append(sub)

                    # Students (30 per class, varied profiles)
                    profiles = (
                        ['excellent'] * 5 +
                        ['good'] * 10 +
                        ['average'] * 9 +
                        ['struggling'] * 4 +
                        ['failing'] * 2
                    )
                    random.shuffle(profiles)

                    names_used = set()
                    students_in_class = []
                    for roll in range(1, 31):
                        # Generate unique name
                        while True:
                            fname = random.choice(FIRST_NAMES)
                            lname = random.choice(LAST_NAMES)
                            full_name = f'{fname} {lname}'
                            if full_name not in names_used:
                                names_used.add(full_name)
                                break

                        stud, _ = Student.objects.get_or_create(
                            classroom=classroom,
                            roll_number=roll,
                            defaults={'name': full_name}
                        )
                        students_in_class.append((stud, profiles[roll - 1]))

                    total_students += len(students_in_class)

                    # Marks
                    for stud, profile in students_in_class:
                        for sub in subject_objs:
                            # 5% chance of being absent per subject
                            is_absent = random.random() < 0.05
                            if is_absent:
                                obtained = None
                            else:
                                obtained = generate_mark(profile, sub.out_of_marks)

                            Mark.objects.update_or_create(
                                student=stud,
                                subject=sub,
                                defaults={
                                    'marks_obtained': obtained,
                                    'is_absent': is_absent,
                                }
                            )
                            total_marks += 1

                    self.stdout.write(
                        f'    [OK] {classroom} - 30 students, {len(subject_objs)} subjects'
                    )

        self.stdout.write(self.style.SUCCESS(
            f'\n[DONE] Seed complete! Created {total_students} students '
            f'with {total_marks} mark records across {len(years_to_seed)} academic year(s).'
        ))
        self.stdout.write(self.style.SUCCESS(
            '   Power BI can now connect to PostgreSQL and query marks_mark, marks_student, '
            'marks_classroom, marks_academicyear, marks_subject tables.'
        ))

    def _seed_grade_rules(self):
        """Create default grade rules if they don't exist."""
        for rule in GRADE_RULES:
            GradeRule.objects.get_or_create(
                grade=rule['grade'],
                defaults={
                    'min_percentage': rule['min_percentage'],
                    'max_percentage': rule['max_percentage'],
                    'description': rule['description'],
                }
            )
        self.stdout.write(f'  [OK] Grade rules ready ({len(GRADE_RULES)} rules)')
