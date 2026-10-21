from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
import uuid


# ---------------------------------------------------------------------------
# Multi-Tenant: Organization & User Profile
# ---------------------------------------------------------------------------

class Organization(models.Model):
    """
    Represents a school / institution.
    One admin owns the org; teachers join it.
    All data (ClassRooms, Students, Marks) is scoped per org.
    """
    name       = models.CharField(max_length=200, help_text="Full school name, e.g. St. Xavier's High School")
    code       = models.SlugField(max_length=40, unique=True, help_text="Unique org code (auto-generated)")
    admin      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_organization')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            base = slugify(self.name)[:30]
            code = base
            n = 1
            while Organization.objects.filter(code=code).exists():
                code = f"{base}-{n}"
                n += 1
            self.code = code
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """
    Extends Django's User model with a role and organization link.
    Created automatically when an admin or teacher registers.
    """
    ROLE_ADMIN   = 'admin'
    ROLE_TEACHER = 'teacher'
    ROLE_CHOICES = [
        (ROLE_ADMIN,   'Administrator'),
        (ROLE_TEACHER, 'Teacher'),
    ]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_TEACHER)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='members', null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER


# ---------------------------------------------------------------------------
# Academic Data Models
# ---------------------------------------------------------------------------

class AcademicYear(models.Model):
    """Represents an academic year, e.g., 2022-23"""
    name       = models.CharField(max_length=20, unique=True, help_text="Academic Year (e.g. 2022-23)")
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return self.name


class ClassRoom(models.Model):
    """Represents a class division in a specific academic year, e.g., Std III A (2022-23)"""
    organization  = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='classrooms', null=True, blank=True
    )
    class_name    = models.CharField(max_length=50, help_text="e.g. Std III")
    division      = models.CharField(max_length=10, help_text="e.g. A")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")
    class_teacher = models.CharField(max_length=100, blank=True, help_text="Name of the Class Teacher")
    pass_percentage = models.FloatField(
        default=33.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Minimum overall percentage required to pass"
    )

    class Meta:
        unique_together = ('class_name', 'division', 'academic_year', 'organization')
        ordering = ['class_name', 'division']

    def __str__(self):
        return f"{self.class_name} {self.division} ({self.academic_year.name})"


class Student(models.Model):
    """Represents a student enrolled in a ClassRoom"""
    roll_number = models.IntegerField()
    name        = models.CharField(max_length=150)
    classroom   = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="students")

    class Meta:
        unique_together = ('roll_number', 'classroom')
        ordering = ['roll_number']

    def __str__(self):
        return f"Roll {self.roll_number} - {self.name}"


class Subject(models.Model):
    """Represents a subject taught in a specific ClassRoom with maximum out-of marks"""
    name         = models.CharField(max_length=100)
    out_of_marks = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(1.0)],
        help_text="Maximum obtainable marks for this subject"
    )
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="subjects")
    order     = models.IntegerField(default=1, help_text="Display order of subject in tables/sheets")

    class Meta:
        unique_together = ('name', 'classroom')
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} (Out of {self.out_of_marks})"


class Mark(models.Model):
    """Represents marks obtained by a student in a specific subject"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="marks")
    marks_obtained = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Marks scored by the student (leave blank if absent)"
    )
    is_absent = models.BooleanField(
        default=False,
        help_text="Check if the student was absent for this examination"
    )

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        status = "AB" if self.is_absent else (str(self.marks_obtained) if self.marks_obtained is not None else "N/A")
        return f"{self.student.name} - {self.subject.name}: {status}"


class GradeRule(models.Model):
    """
    Configurable grade rules with continuous, gap-less percentage boundaries.
    Default Rules:
      A: 90% - 100%
      B: 80% - 90%
      C: 60% - 80%
      D: 33% - 60%
      E: 0% - 33%
    """
    grade           = models.CharField(max_length=5, unique=True)
    min_percentage  = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Minimum percentage boundary (inclusive)"
    )
    max_percentage  = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Maximum percentage boundary (exclusive, except for 100%)"
    )
    description     = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-min_percentage']

    def __str__(self):
        return f"Grade {self.grade}: {self.min_percentage}% to {self.max_percentage}%"


# ---------------------------------------------------------------------------
# Teacher Join Request (Approval Workflow)
# ---------------------------------------------------------------------------

class JoinRequest(models.Model):
    """
    When a teacher registers, a JoinRequest is created for the admin to approve.
    Until approved, the teacher account exists but has no organization linked.
    """
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    teacher_user  = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='join_request'
    )
    organization  = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='join_requests'
    )
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at  = models.DateTimeField(auto_now_add=True)
    responded_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.teacher_user.username} → {self.organization.name} ({self.status})"

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_rejected(self):
        return self.status == self.STATUS_REJECTED

    @classmethod
    def get_default_rules(cls):
        """Returns standard default grade rules if none exist in the database."""
        return [
            {'grade': 'A', 'min_percentage': 90.0, 'max_percentage': 100.0, 'description': 'Excellent'},
            {'grade': 'B', 'min_percentage': 80.0, 'max_percentage': 90.0,  'description': 'Very Good'},
            {'grade': 'C', 'min_percentage': 60.0, 'max_percentage': 80.0,  'description': 'Good'},
            {'grade': 'D', 'min_percentage': 33.0, 'max_percentage': 60.0,  'description': 'Satisfactory / Pass'},
            {'grade': 'E', 'min_percentage': 0.0,  'max_percentage': 33.0,  'description': 'Needs Improvement / Fail'},
        ]
