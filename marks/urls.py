from django.urls import path
from marks import views
from marks import api_views

urlpatterns = [
    # -----------------------------------------------------------------------
    # Web Views
    # -----------------------------------------------------------------------
    path('', views.dashboard_view, name='dashboard'),
    path('classes/', views.class_list_view, name='class_list'),
    path('classes/<int:class_id>/', views.class_detail_view, name='class_detail'),
    path('classes/<int:class_id>/marks/', views.marks_entry_view, name='marks_entry'),
    path('classes/<int:class_id>/export/', views.excel_export_view, name='excel_export'),
    path('classes/<int:class_id>/add-student/', views.add_student_view, name='add_student'),
    path('classes/<int:class_id>/add-subject/', views.add_subject_view, name='add_subject'),
    path('upload/', views.excel_upload_view, name='excel_upload'),
    path('settings/grade-rules/', views.grade_rules_view, name='grade_rules'),
    path('seed-sample-data/', views.seed_sample_data, name='seed_sample_data'),

    # -----------------------------------------------------------------------
    # REST API — for Power BI Web connector & external integrations
    # -----------------------------------------------------------------------
    path('api/marks/', api_views.MarksListAPI.as_view(), name='api_marks'),
    path('api/students/', api_views.StudentListAPI.as_view(), name='api_students'),
    path('api/classrooms/', api_views.ClassRoomListAPI.as_view(), name='api_classrooms'),
    path('api/academic-years/', api_views.AcademicYearListAPI.as_view(), name='api_academic_years'),
    path('api/grade-rules/', api_views.GradeRuleListAPI.as_view(), name='api_grade_rules'),
    path('api/summary/', api_views.StudentSummaryAPI.as_view(), name='api_summary'),
    path('api/dashboard/', api_views.DashboardStatsAPI.as_view(), name='api_dashboard'),
]
