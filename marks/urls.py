from django.urls import path
from marks import views
from marks import api_views

urlpatterns = [
    # -----------------------------------------------------------------------
    # Public Pages (no login required)
    # -----------------------------------------------------------------------
    path('', views.landing_view, name='landing'),
    path('api/check-admin/', views.check_admin_username, name='check_admin_username'),

    # -----------------------------------------------------------------------
    # App Pages (login required — handled by @login_required in views.py)
    # -----------------------------------------------------------------------
    path('dashboard/', views.dashboard_view, name='dashboard'),
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
    # Join Request Approval Workflow
    # -----------------------------------------------------------------------
    path('pending/', views.pending_approval_view, name='pending_approval'),
    path('join-requests/', views.join_requests_view, name='join_requests'),
    path('join-requests/<int:request_id>/approve/', views.approve_join_request, name='approve_join_request'),
    path('join-requests/<int:request_id>/reject/',  views.reject_join_request,  name='reject_join_request'),

    # -----------------------------------------------------------------------
    # REST API — for Power BI Web connector & external integrations
    # -----------------------------------------------------------------------
    path('api/marks/flat/', api_views.FlatMarksAPIView.as_view(), name='api_marks_flat'),
    path('api/marks/students/', api_views.StudentSummaryAPIView.as_view(), name='api_students_summary'),
    path('api/marks/subjects/', api_views.SubjectAnalysisAPIView.as_view(), name='api_subjects_analysis'),
]
