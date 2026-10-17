"""
REST API Views for Power BI Web Connector.

Three endpoints expose the school marks data in flat, query-friendly formats:

  GET /api/marks/flat/          → All individual mark records (fact table)
  GET /api/marks/students/      → Consolidated totals per student
  GET /api/marks/subjects/      → Grade distribution per subject

All endpoints support query-string filters:
  ?class_id=1
  ?academic_year=2022-23
  ?class_name=Std+III
  ?division=A
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.db.models import Prefetch

from marks.models import ClassRoom, Student, Subject, Mark, GradeRule
from marks.serializers import FlatMarkSerializer, StudentSummarySerializer, SubjectAnalysisSerializer
from marks.services.calculations import (
    calculate_student_consolidated,
    calculate_subject_analysis,
)


def get_filtered_classrooms(request):
    """Helper: filter ClassRooms from query-string params."""
    qs = ClassRoom.objects.select_related('academic_year').all()

    if class_id := request.GET.get('class_id'):
        qs = qs.filter(pk=class_id)
    if year := request.GET.get('academic_year'):
        qs = qs.filter(academic_year__name=year)
    if cn := request.GET.get('class_name'):
        qs = qs.filter(class_name__iexact=cn)
    if div := request.GET.get('division'):
        qs = qs.filter(division__iexact=div)

    return qs


class FlatMarksAPIView(APIView):
    """
    GET /api/marks/flat/
    ─────────────────────────────────────────────────────────────────────
    Returns every Mark record as one flat row containing:
    academic_year, class_name, division, student info, subject info,
    marks_obtained, is_absent, calculated percentage & grade.

    This is the PRIMARY TABLE for Power BI.
    Power BI can pivot, slice, and aggregate from this single endpoint.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grade_rules = list(GradeRule.objects.all())

        classrooms = get_filtered_classrooms(request)

        marks_qs = Mark.objects.filter(
            student__classroom__in=classrooms
        ).select_related(
            'student',
            'student__classroom',
            'student__classroom__academic_year',
            'subject',
        ).order_by(
            'student__classroom__academic_year__name',
            'student__classroom__class_name',
            'student__classroom__division',
            'student__roll_number',
            'subject__order',
        )

        serializer = FlatMarkSerializer(
            marks_qs,
            many=True,
            context={'grade_rules': grade_rules}
        )
        return Response({
            'count': len(serializer.data),
            'description': 'Flat mark records – one row per student × subject. Use this as your Power BI fact table.',
            'filters_applied': {k: v for k, v in request.GET.items()},
            'results': serializer.data,
        })


class StudentSummaryAPIView(APIView):
    """
    GET /api/marks/students/
    ─────────────────────────────────────────────────────────────────────
    Returns consolidated totals per student across ALL subjects:
    total marks, total%, overall grade, pass/fail status.

    Use this for Power BI KPI cards, toppers lists, and student drill-through.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grade_rules = list(GradeRule.objects.all())
        classrooms  = get_filtered_classrooms(request)
        results = []

        for classroom in classrooms:
            students = Student.objects.filter(classroom=classroom).order_by('roll_number')
            subjects = list(Subject.objects.filter(classroom=classroom).order_by('order', 'name'))

            # Build marks map for this classroom
            marks_map = {}
            for m in Mark.objects.filter(student__classroom=classroom).select_related('student', 'subject'):
                marks_map.setdefault(m.student_id, {})[m.subject_id] = m

            for stud in students:
                subject_marks = [
                    {
                        'subject_name': sub.name,
                        'marks_obtained': marks_map.get(stud.id, {}).get(sub.id, Mark()).marks_obtained,
                        'out_of_marks': sub.out_of_marks,
                        'is_absent': marks_map.get(stud.id, {}).get(sub.id, Mark()).is_absent,
                    }
                    for sub in subjects
                ]

                con = calculate_student_consolidated(
                    stud.name, stud.roll_number, subject_marks,
                    classroom.pass_percentage, grade_rules
                )

                results.append({
                    'academic_year':      classroom.academic_year.name,
                    'class_name':         classroom.class_name,
                    'division':           classroom.division,
                    'roll_number':        stud.roll_number,
                    'student_name':       stud.name,
                    'total_obtained':     con.get('total_obtained', 0.0),
                    'total_out_of':       con.get('total_out_of', 0.0),
                    'overall_percentage': con.get('overall_percentage', 0.0),
                    'overall_grade':      con.get('overall_grade', 'AB'),
                    'is_pass':            con.get('is_pass', False),
                    'present_count':      con.get('present_count', 0),
                    'absent_count':       con.get('absent_count', 0),
                })

        serializer = StudentSummarySerializer(results, many=True)
        return Response({
            'count': len(serializer.data),
            'description': 'Consolidated student summary – one row per student. Use for KPI cards and drill-through.',
            'filters_applied': {k: v for k, v in request.GET.items()},
            'results': serializer.data,
        })


class SubjectAnalysisAPIView(APIView):
    """
    GET /api/marks/subjects/
    ─────────────────────────────────────────────────────────────────────
    Returns subject-level analysis:
    grade distribution counts (A,B,C,D,E,AB), average %, pass %.

    Use this for Power BI subject comparison bar charts and heatmaps.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grade_rules = list(GradeRule.objects.all())
        classrooms  = get_filtered_classrooms(request)
        results = []

        for classroom in classrooms:
            subjects  = Subject.objects.filter(classroom=classroom).order_by('order', 'name')
            students  = list(Student.objects.filter(classroom=classroom))
            marks_map = {}
            for m in Mark.objects.filter(student__classroom=classroom).select_related('student', 'subject'):
                marks_map.setdefault(m.student_id, {})[m.subject_id] = m

            for sub in subjects:
                sub_records = [
                    {
                        'marks_obtained': marks_map.get(stud.id, {}).get(sub.id, Mark()).marks_obtained,
                        'is_absent':      marks_map.get(stud.id, {}).get(sub.id, Mark()).is_absent,
                    }
                    for stud in students
                ]

                analysis = calculate_subject_analysis(
                    sub.name, sub.out_of_marks, sub_records,
                    classroom.pass_percentage, grade_rules
                )
                gc = analysis['grade_counts']

                results.append({
                    'academic_year':          classroom.academic_year.name,
                    'class_name':             classroom.class_name,
                    'division':               classroom.division,
                    'subject_name':           sub.name,
                    'out_of_marks':           sub.out_of_marks,
                    'total_students':         analysis['total_students'],
                    'present_count':          analysis['present_count'],
                    'absent_count':           analysis['absent_count'],
                    'pass_count':             analysis['pass_count'],
                    'fail_count':             analysis['fail_count'],
                    'subject_avg_marks':      analysis['subject_avg_marks'],
                    'subject_avg_percentage': analysis['subject_avg_percentage'],
                    'subject_pass_percent':   analysis['subject_pass_percent'],
                    'grade_A':                gc.get('A', 0),
                    'grade_B':                gc.get('B', 0),
                    'grade_C':                gc.get('C', 0),
                    'grade_D':                gc.get('D', 0),
                    'grade_E':                gc.get('E', 0),
                    'grade_AB':               gc.get('AB', 0),
                })

        serializer = SubjectAnalysisSerializer(results, many=True)
        return Response({
            'count': len(serializer.data),
            'description': 'Subject analysis – one row per subject per class. Use for grade distribution charts.',
            'filters_applied': {k: v for k, v in request.GET.items()},
            'results': serializer.data,
        })
