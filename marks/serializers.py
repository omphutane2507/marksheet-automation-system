from rest_framework import serializers
from .models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'


class ClassRoomSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)

    class Meta:
        model = ClassRoom
        fields = '__all__'


class StudentSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.__str__', read_only=True)

    class Meta:
        model = Student
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.__str__', read_only=True)

    class Meta:
        model = Subject
        fields = '__all__'


class MarkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll = serializers.IntegerField(source='student.roll_number', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_out_of = serializers.FloatField(source='subject.out_of_marks', read_only=True)
    classroom = serializers.CharField(source='student.classroom.__str__', read_only=True)
    academic_year = serializers.CharField(source='student.classroom.academic_year.name', read_only=True)

    class Meta:
        model = Mark
        fields = '__all__'


class GradeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeRule
        fields = '__all__'


class StudentSummarySerializer(serializers.Serializer):
    """Aggregated per-student summary for Power BI dashboards."""
    student_id = serializers.IntegerField()
    roll_number = serializers.IntegerField()
    student_name = serializers.CharField()
    classroom = serializers.CharField()
    academic_year = serializers.CharField()
    total_obtained = serializers.FloatField()
    total_out_of = serializers.FloatField()
    percentage = serializers.FloatField()
    subjects_appeared = serializers.IntegerField()
    subjects_absent = serializers.IntegerField()
