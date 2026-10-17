"""
REST API Serializers for Power BI Web Connector.
These flatten the relational data into the wide-table format
that Power BI expects (one row = one student × subject mark).
"""

from rest_framework import serializers
from marks.models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule
from marks.services.calculations import calculate_student_consolidated, calculate_subject_analysis
from django.db.models import Prefetch


# --------------------------------------------------------------------------
# Simple Model Serializers
# --------------------------------------------------------------------------

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'is_current']


class ClassRoomSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)

    class Meta:
        model = ClassRoom
        fields = ['id', 'class_name', 'division', 'academic_year_name', 'class_teacher', 'pass_percentage']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'out_of_marks', 'order']


class GradeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeRule
        fields = ['id', 'grade', 'min_percentage', 'max_percentage', 'description']


# --------------------------------------------------------------------------
# Flat Mark Record (one row per student-subject combination)
# Power BI can use this as a fact table and slice by any dimension.
# --------------------------------------------------------------------------

class FlatMarkSerializer(serializers.ModelSerializer):
    """
    Wide-format flat table:
    Each row = one student × one subject mark record.
    Power BI connects to this endpoint and slices / pivots freely.
    """
    # Student fields
    roll_number      = serializers.IntegerField(source='student.roll_number')
    student_name     = serializers.CharField(source='student.name')

    # Class fields
    class_name       = serializers.CharField(source='student.classroom.class_name')
    division         = serializers.CharField(source='student.classroom.division')
    academic_year    = serializers.CharField(source='student.classroom.academic_year.name')
    class_teacher    = serializers.CharField(source='student.classroom.class_teacher')

    # Subject fields
    subject_name     = serializers.CharField(source='subject.name')
    out_of_marks     = serializers.FloatField(source='subject.out_of_marks')

    # Calculated fields (computed at serialization time)
    percentage       = serializers.SerializerMethodField()
    grade            = serializers.SerializerMethodField()

    class Meta:
        model  = Mark
        fields = [
            'id',
            'academic_year', 'class_name', 'division', 'class_teacher',
            'roll_number', 'student_name',
            'subject_name', 'out_of_marks',
            'marks_obtained', 'is_absent',
            'percentage', 'grade',
        ]

    def get_percentage(self, obj):
        if obj.is_absent or obj.marks_obtained is None:
            return None
        return round((obj.marks_obtained / obj.subject.out_of_marks) * 100.0, 2)

    def get_grade(self, obj):
        pct = self.get_percentage(obj)
        if pct is None:
            return 'AB'
        rules = self.context.get('grade_rules', [])
        from marks.services.calculations import determine_grade
        return determine_grade(pct, rules)


# --------------------------------------------------------------------------
# Consolidated Student Summary (one row per student per class)
# --------------------------------------------------------------------------

class StudentSummarySerializer(serializers.Serializer):
    """
    One row per student with consolidated totals across all subjects.
    Used for Power BI KPI cards and student-level drill-through.
    """
    academic_year       = serializers.CharField()
    class_name          = serializers.CharField()
    division            = serializers.CharField()
    roll_number         = serializers.IntegerField()
    student_name        = serializers.CharField()
    total_obtained      = serializers.FloatField()
    total_out_of        = serializers.FloatField()
    overall_percentage  = serializers.FloatField()
    overall_grade       = serializers.CharField()
    is_pass             = serializers.BooleanField()
    present_count       = serializers.IntegerField()
    absent_count        = serializers.IntegerField()


# --------------------------------------------------------------------------
# Subject Analysis Summary (one row per subject per class)
# --------------------------------------------------------------------------

class SubjectAnalysisSerializer(serializers.Serializer):
    """
    One row per subject with grade distribution counts.
    Used for Power BI subject comparison charts.
    """
    academic_year           = serializers.CharField()
    class_name              = serializers.CharField()
    division                = serializers.CharField()
    subject_name            = serializers.CharField()
    out_of_marks            = serializers.FloatField()
    total_students          = serializers.IntegerField()
    present_count           = serializers.IntegerField()
    absent_count            = serializers.IntegerField()
    pass_count              = serializers.IntegerField()
    fail_count              = serializers.IntegerField()
    subject_avg_marks       = serializers.FloatField()
    subject_avg_percentage  = serializers.FloatField()
    subject_pass_percent    = serializers.FloatField()
    grade_A                 = serializers.IntegerField()
    grade_B                 = serializers.IntegerField()
    grade_C                 = serializers.IntegerField()
    grade_D                 = serializers.IntegerField()
    grade_E                 = serializers.IntegerField()
    grade_AB                = serializers.IntegerField()
