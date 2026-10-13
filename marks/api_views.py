from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q

from .models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule
from .serializers import (
    AcademicYearSerializer, ClassRoomSerializer, StudentSerializer,
    SubjectSerializer, MarkSerializer, GradeRuleSerializer,
    StudentSummarySerializer
)


class AcademicYearListAPI(APIView):
    """GET /api/academic-years/ — List all academic years."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AcademicYear.objects.all()
        return Response(AcademicYearSerializer(qs, many=True).data)


class ClassRoomListAPI(APIView):
    """GET /api/classrooms/?year_id=1 — List all classrooms, optionally filtered by year."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ClassRoom.objects.select_related('academic_year').all()
        year_id = request.query_params.get('year_id')
        if year_id:
            qs = qs.filter(academic_year_id=year_id)
        return Response(ClassRoomSerializer(qs, many=True).data)


class StudentListAPI(APIView):
    """GET /api/students/?classroom_id=1 — List all students, optionally filtered by classroom."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Student.objects.select_related('classroom__academic_year').all()
        classroom_id = request.query_params.get('classroom_id')
        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        return Response(StudentSerializer(qs, many=True).data)


class MarksListAPI(APIView):
    """
    GET /api/marks/ — Full marks data, ideal for Power BI import.
    Supports query params: classroom_id, academic_year_id, subject_id
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Mark.objects.select_related(
            'student__classroom__academic_year',
            'subject__classroom'
        ).all()

        classroom_id = request.query_params.get('classroom_id')
        year_id = request.query_params.get('academic_year_id')
        subject_id = request.query_params.get('subject_id')

        if classroom_id:
            qs = qs.filter(student__classroom_id=classroom_id)
        if year_id:
            qs = qs.filter(student__classroom__academic_year_id=year_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        return Response(MarkSerializer(qs, many=True).data)


class StudentSummaryAPI(APIView):
    """
    GET /api/summary/ — Per-student aggregated summary.
    Best for Power BI 'Student Performance' table visual.
    Supports query params: classroom_id, academic_year_id
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        students = Student.objects.select_related('classroom__academic_year').all()

        classroom_id = request.query_params.get('classroom_id')
        year_id = request.query_params.get('academic_year_id')

        if classroom_id:
            students = students.filter(classroom_id=classroom_id)
        if year_id:
            students = students.filter(classroom__academic_year_id=year_id)

        results = []
        for student in students:
            marks = Mark.objects.filter(student=student)
            subjects = Subject.objects.filter(classroom=student.classroom)

            total_out_of = sum(
                m.subject.out_of_marks
                for m in marks
                if not m.is_absent and m.marks_obtained is not None
            )
            total_obtained = sum(
                m.marks_obtained
                for m in marks
                if not m.is_absent and m.marks_obtained is not None
            )
            subjects_appeared = marks.filter(is_absent=False).count()
            subjects_absent = marks.filter(is_absent=True).count()
            percentage = round((total_obtained / total_out_of * 100), 2) if total_out_of > 0 else 0.0

            results.append({
                'student_id': student.id,
                'roll_number': student.roll_number,
                'student_name': student.name,
                'classroom': str(student.classroom),
                'academic_year': student.classroom.academic_year.name,
                'total_obtained': total_obtained,
                'total_out_of': total_out_of,
                'percentage': percentage,
                'subjects_appeared': subjects_appeared,
                'subjects_absent': subjects_absent,
            })

        return Response(results)


class GradeRuleListAPI(APIView):
    """GET /api/grade-rules/ — Grade configuration for Power BI calculated columns."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = GradeRule.objects.all()
        return Response(GradeRuleSerializer(qs, many=True).data)


class DashboardStatsAPI(APIView):
    """
    GET /api/dashboard/ — Quick overview stats for Power BI card visuals.
    Returns totals across the entire database.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_students = Student.objects.count()
        total_classrooms = ClassRoom.objects.count()
        total_marks_entered = Mark.objects.filter(
            is_absent=False, marks_obtained__isnull=False
        ).count()
        total_absent = Mark.objects.filter(is_absent=True).count()
        academic_years = AcademicYear.objects.count()

        return Response({
            'total_students': total_students,
            'total_classrooms': total_classrooms,
            'total_marks_entered': total_marks_entered,
            'total_absent_records': total_absent,
            'academic_years': academic_years,
        })
