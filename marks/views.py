import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction

from marks.models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule, Organization, UserProfile, JoinRequest, TeacherPermission
from marks.forms import (
    ClassRoomForm, StudentForm, SubjectForm, ExcelUploadForm, GradeRuleForm,
    AdminRegisterForm, TeacherRegisterForm
)
from marks.services.calculations import (
    determine_grade,
    calculate_student_consolidated,
    calculate_subject_analysis,
    calculate_class_overview
)
from marks.services.excel_import import process_excel_upload
from marks.services.excel_export import export_class_excel


# ---------------------------------------------------------------------------
# Multi-Tenant Helpers
# ---------------------------------------------------------------------------

def get_user_org(request):
    """Return the Organization for the logged-in user, or None."""
    try:
        return request.user.profile.organization
    except Exception:
        return None


def require_active_org(request):
    """
    Returns a redirect response if the logged-in teacher has no org yet
    (pending or rejected join request), otherwise returns None.
    Admins always pass through.
    """
    try:
        profile = request.user.profile
    except Exception:
        return None  # superuser or no profile — let through
    if profile.is_admin:
        return None  # admins always have access
    if profile.organization is None:
        return redirect('pending_approval')
    return None


def get_teacher_permission(user, classroom, subject=None):
    """
    Returns the effective permission role ('editor' or 'viewer') for a teacher
    on a given classroom/subject. Subject-level overrides class-level.
    Admins always return 'editor'. Returns None if no permission exists.
    """
    try:
        profile = user.profile
        if profile.is_admin:
            return TeacherPermission.ROLE_EDITOR
    except Exception:
        return TeacherPermission.ROLE_EDITOR  # superuser passthrough

    # Subject-level check (most specific)
    if subject:
        sub_perm = TeacherPermission.objects.filter(
            teacher=user, classroom=classroom, subject=subject
        ).first()
        if sub_perm:
            return sub_perm.role

    # Class-level check (fallback)
    class_perm = TeacherPermission.objects.filter(
        teacher=user, classroom=classroom, subject=None
    ).first()
    return class_perm.role if class_perm else None


def get_user_classes(request):
    """Return the queryset of ClassRooms visible to the current user."""
    org = get_user_org(request)
    if not org:
        return ClassRoom.objects.none()
    all_classes = ClassRoom.objects.select_related('academic_year').filter(organization=org)
    try:
        profile = request.user.profile
    except Exception:
        return all_classes  # superuser
    if profile.is_admin:
        return all_classes
    # Teachers: only classes they have ANY permission for
    permitted_ids = TeacherPermission.objects.filter(
        teacher=request.user
    ).values_list('classroom_id', flat=True).distinct()
    return all_classes.filter(id__in=permitted_ids)


# ---------------------------------------------------------------------------
# Registration Views
# ---------------------------------------------------------------------------

def register_view(request):
    """
    Combined registration page. Shows admin and teacher registration tabs.
    GET  -> render empty forms
    POST -> detect which form was submitted via hidden 'role' field
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    admin_form   = AdminRegisterForm()
    teacher_form = TeacherRegisterForm()
    active_tab   = request.GET.get('tab', 'admin')  # read ?tab= from GET
    if active_tab not in ('admin', 'teacher'):
        active_tab = 'admin'

    if request.method == 'POST':
        role = request.POST.get('role', 'admin')
        active_tab = role

        if role == 'admin':
            admin_form = AdminRegisterForm(request.POST)
            if admin_form.is_valid():
                cd = admin_form.cleaned_data
                with transaction.atomic():
                    # 1. Create User
                    user = User.objects.create_user(
                        username   = cd['username'],
                        email      = cd['email'],
                        password   = cd['password1'],
                        first_name = cd['first_name'],
                        last_name  = cd.get('last_name', ''),
                    )
                    # 2. Create Organisation
                    org = Organization.objects.create(
                        name  = cd['school_name'],
                        admin = user,
                    )
                    # 3. Create UserProfile
                    UserProfile.objects.create(
                        user         = user,
                        role         = UserProfile.ROLE_ADMIN,
                        organization = org,
                    )
                auth_login(request, user)
                messages.success(
                    request,
                    f"Welcome {user.first_name}! Your school '{org.name}' has been created. "
                    f"Share your username '{user.username}' with teachers so they can register."
                )
                return redirect('dashboard')

        elif role == 'teacher':
            teacher_form = TeacherRegisterForm(request.POST)
            if teacher_form.is_valid():
                cd = teacher_form.cleaned_data
                with transaction.atomic():
                    admin_user = User.objects.get(username=cd['admin_username'])
                    org        = Organization.objects.get(admin=admin_user)
                    # 1. Create User
                    user = User.objects.create_user(
                        username   = cd['username'],
                        email      = cd['email'],
                        password   = cd['password1'],
                        first_name = cd['first_name'],
                        last_name  = cd.get('last_name', ''),
                    )
                    # 2. Create UserProfile — no org yet (pending approval)
                    UserProfile.objects.create(
                        user         = user,
                        role         = UserProfile.ROLE_TEACHER,
                        organization = None,
                    )
                    # 3. Create JoinRequest for the admin to review
                    JoinRequest.objects.create(
                        teacher_user = user,
                        organization = org,
                        status       = JoinRequest.STATUS_PENDING,
                    )
                auth_login(request, user)
                # No flash message — pending.html communicates the status clearly
                return redirect('pending_approval')

    return render(request, 'registration/register.html', {
        'admin_form':   admin_form,
        'teacher_form': teacher_form,
        'active_tab':   active_tab,
    })


def check_admin_username(request):
    """
    AJAX endpoint: check if an admin username exists and has an organisation.
    Returns JSON: {valid, org_name, admin_display_name, member_count}
    Called by the teacher registration form for live feedback.
    """
    username = request.GET.get('username', '').strip().lower()
    if not username:
        return JsonResponse({'valid': False, 'error': ''})
    try:
        admin_user = User.objects.get(username=username)
        org = Organization.objects.get(admin=admin_user)
        member_count = org.members.count()
        return JsonResponse({
            'valid': True,
            'org_name':          org.name,
            'admin_display_name': admin_user.get_full_name() or admin_user.username,
            'member_count':      member_count,
        })
    except User.DoesNotExist:
        return JsonResponse({'valid': False, 'error': f"No admin account with username \"{username}\" exists."})
    except Organization.DoesNotExist:
        return JsonResponse({'valid': False, 'error': f"User \"{username}\" has not set up an organisation yet."})


def ensure_default_grade_rules():
    """Seeds default grade rules if none exist in the database."""
    if GradeRule.objects.count() == 0:
        for rule in GradeRule.get_default_rules():
            GradeRule.objects.create(**rule)


@login_required
def pending_approval_view(request):
    """
    Shown to teachers whose join request is still pending or was rejected.
    Also handles the case where the teacher has been approved and can now access the dashboard.
    """
    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')

    # Already approved — send to dashboard
    if profile.organization is not None:
        return redirect('dashboard')

    # Look up the join request
    join_request = JoinRequest.objects.filter(teacher_user=request.user).first()

    return render(request, 'registration/pending.html', {
        'join_request': join_request,
    })


def landing_view(request):
    """
    Public landing page shown to unauthenticated visitors.
    Logged-in users are sent straight to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard_view(request):
    guard = require_active_org(request)
    if guard:
        return guard
    """
    Main Analytics Dashboard with Chart.js visualization:
    - Summary Cards: Total Students, Class Average %, Pass %
    - Grade Distribution per subject (Bar Chart)
    - Pass vs Fail Ratio (Donut Chart)
    - Average Marks per subject (Bar Chart)
    - Toppers List & Needs Attention List
    """
    ensure_default_grade_rules()
    
    org = get_user_org(request)
    academic_years = AcademicYear.objects.all()
    classes = get_user_classes(request)  # respects teacher permissions

    # Filter selection
    selected_class_id = request.GET.get('class_id')
    
    if selected_class_id:
        current_class = get_object_or_404(ClassRoom, pk=selected_class_id)
    else:
        current_class = classes.first()

    if not current_class:
        context = {
            'academic_years': academic_years,
            'classes': classes,
            'current_class': None,
            'has_data': False
        }
        return render(request, 'marks/dashboard.html', context)

    students = list(Student.objects.filter(classroom=current_class).order_by('roll_number'))
    subjects = list(Subject.objects.filter(classroom=current_class).order_by('order', 'name'))
    grade_rules = list(GradeRule.objects.all())

    # Build marks mapping
    marks_query = Mark.objects.filter(student__classroom=current_class).select_related('student', 'subject')
    marks_map = {}
    for m in marks_query:
        if m.student_id not in marks_map:
            marks_map[m.student_id] = {}
        marks_map[m.student_id][m.subject_id] = m

    # Calculate student consolidated statistics
    class_students_data = []
    for stud in students:
        stud_subject_marks = []
        for sub in subjects:
            m_obj = marks_map.get(stud.id, {}).get(sub.id)
            stud_subject_marks.append({
                'subject_name': sub.name,
                'marks_obtained': m_obj.marks_obtained if m_obj else None,
                'out_of_marks': sub.out_of_marks,
                'is_absent': m_obj.is_absent if m_obj else False
            })
        con_res = calculate_student_consolidated(
            stud.name, stud.roll_number, stud_subject_marks,
            current_class.pass_percentage, grade_rules
        )
        class_students_data.append(con_res)

    class_overview = calculate_class_overview(class_students_data, current_class.pass_percentage, grade_rules)

    # Subject Analysis for Charts
    subject_chart_labels = []
    subject_averages = []
    subject_grade_dist = [] # [ {subject: 'Maths', A: 2, B: 1, C: 1, D: 0, E: 0, AB: 0} ]

    for sub in subjects:
        sub_records = []
        for stud in students:
            m_obj = marks_map.get(stud.id, {}).get(sub.id)
            sub_records.append({
                'marks_obtained': m_obj.marks_obtained if m_obj else None,
                'is_absent': m_obj.is_absent if m_obj else False
            })

        s_analysis = calculate_subject_analysis(
            sub.name, sub.out_of_marks, sub_records,
            current_class.pass_percentage, grade_rules
        )

        subject_chart_labels.append(sub.name)
        subject_averages.append(s_analysis['subject_avg_percentage'])
        
        gc = s_analysis['grade_counts']
        subject_grade_dist.append({
            'subject': sub.name,
            'A': gc.get('A', 0),
            'B': gc.get('B', 0),
            'C': gc.get('C', 0),
            'D': gc.get('D', 0),
            'E': gc.get('E', 0),
            'AB': gc.get('AB', 0),
        })

    # Prepare JSON chart payload
    chart_data = {
        'subject_labels': subject_chart_labels,
        'subject_averages': subject_averages,
        'pass_count': class_overview['pass_count'],
        'fail_count': class_overview['fail_count'],
        'overall_grade_counts': class_overview['grade_counts'],
        'subject_grade_dist': subject_grade_dist
    }

    context = {
        'academic_years': academic_years,
        'classes': classes,
        'current_class': current_class,
        'subjects': subjects,
        'students_count': len(students),
        'class_overview': class_overview,
        'chart_data_json': json.dumps(chart_data),
        'has_data': True
    }
    return render(request, 'marks/dashboard.html', context)


def class_list_view(request):
    guard = require_active_org(request)
    if guard:
        return guard
    """Lists active classes the current user has access to."""
    ensure_default_grade_rules()
    org = get_user_org(request)
    classes = get_user_classes(request)

    if request.method == 'POST':
        form = ClassRoomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.organization = org
            classroom.save()
            messages.success(request, f"Class '{classroom}' created successfully!")
            return redirect('class_detail', class_id=classroom.id)
    else:
        form = ClassRoomForm()

    context = {
        'classes': classes,
        'form': form,
        'academic_years': AcademicYear.objects.all()
    }
    return render(request, 'marks/class_list.html', context)


def class_detail_view(request, class_id):
    guard = require_active_org(request)
    if guard:
        return guard
    """
    Detailed class analysis view. Teachers need at least viewer permission.
    """
    ensure_default_grade_rules()
    classroom = get_object_or_404(ClassRoom, pk=class_id)

    # Permission check for teachers
    perm = get_teacher_permission(request.user, classroom)
    if perm is None:
        messages.error(request, "You don't have permission to access this class.")
        return redirect('class_list')
    is_editor = (perm == TeacherPermission.ROLE_EDITOR)
    students = list(Student.objects.filter(classroom=classroom).order_by('roll_number'))
    subjects = list(Subject.objects.filter(classroom=classroom).order_by('order', 'name'))
    grade_rules = list(GradeRule.objects.all())

    # Map marks
    marks_query = Mark.objects.filter(student__classroom=classroom).select_related('student', 'subject')
    marks_map = {}
    for m in marks_query:
        if m.student_id not in marks_map:
            marks_map[m.student_id] = {}
        marks_map[m.student_id][m.subject_id] = m

    # Student consolidated table
    student_consolidated_rows = []
    for stud in students:
        stud_subject_marks = []
        for sub in subjects:
            m_obj = marks_map.get(stud.id, {}).get(sub.id)
            stud_subject_marks.append({
                'subject_name': sub.name,
                'marks_obtained': m_obj.marks_obtained if m_obj else None,
                'out_of_marks': sub.out_of_marks,
                'is_absent': m_obj.is_absent if m_obj else False
            })

        con_res = calculate_student_consolidated(
            stud.name, stud.roll_number, stud_subject_marks,
            classroom.pass_percentage, grade_rules
        )
        con_res['student_id'] = stud.id
        student_consolidated_rows.append(con_res)

    # Subject Analysis tables
    subject_analyses = []
    for sub in subjects:
        sub_records = []
        for stud in students:
            m_obj = marks_map.get(stud.id, {}).get(sub.id)
            sub_records.append({
                'marks_obtained': m_obj.marks_obtained if m_obj else None,
                'is_absent': m_obj.is_absent if m_obj else False
            })

        s_analysis = calculate_subject_analysis(
            sub.name, sub.out_of_marks, sub_records,
            classroom.pass_percentage, grade_rules
        )
        s_analysis['subject_obj'] = sub
        subject_analyses.append(s_analysis)

    class_overview = calculate_class_overview(student_consolidated_rows, classroom.pass_percentage, grade_rules)

    context = {
        'classroom': classroom,
        'students': students,
        'subjects': subjects,
        'student_rows': student_consolidated_rows,
        'subject_analyses': subject_analyses,
        'class_overview': class_overview,
        'subject_form': SubjectForm(),
        'student_form': StudentForm(),
        'is_editor': is_editor,   # controls edit buttons in template
    }
    return render(request, 'marks/class_detail.html', context)


def marks_entry_view(request, class_id):
    guard = require_active_org(request)
    if guard:
        return guard
    """
    Subject Marks Entry interface.
    Requires editor permission at class level (or subject-level override).
    """
    classroom = get_object_or_404(ClassRoom, pk=class_id)
    subjects = Subject.objects.filter(classroom=classroom).order_by('order', 'name')
    selected_subject_id = request.GET.get('subject_id')

    if selected_subject_id:
        current_subject = get_object_or_404(Subject, pk=selected_subject_id, classroom=classroom)
    else:
        current_subject = subjects.first()

    # Permission check
    class_perm = get_teacher_permission(request.user, classroom)
    if class_perm is None:
        messages.error(request, "You don't have permission to access this class.")
        return redirect('class_list')
    # Subject-level may override class-level
    effective_perm = get_teacher_permission(request.user, classroom, current_subject) if current_subject else class_perm
    if effective_perm == TeacherPermission.ROLE_VIEWER:
        messages.warning(request, "You have view-only access — marks entry is restricted for this class/subject.")
        return redirect('class_detail', class_id=class_id)
    if not current_subject:
        messages.warning(request, "Please add at least one subject to this class before entering marks.")
        return redirect('class_detail', class_id=classroom.id)

    students = Student.objects.filter(classroom=classroom).order_by('roll_number')

    if request.method == 'POST':
        errors = []
        marks_to_update = []

        with transaction.atomic():
            for stud in students:
                mark_key = f"mark_{stud.id}"
                absent_key = f"absent_{stud.id}"

                is_absent = absent_key in request.POST
                raw_mark = request.POST.get(mark_key, '').strip()

                marks_obtained = None

                if is_absent:
                    is_absent = True
                    marks_obtained = None
                elif raw_mark:
                    try:
                        m_val = float(raw_mark)
                        if m_val < 0:
                            errors.append(f"{stud.name}: Marks cannot be negative ({m_val}).")
                        elif m_val > current_subject.out_of_marks:
                            errors.append(f"{stud.name}: Marks ({m_val}) exceeds maximum out-of marks ({current_subject.out_of_marks}).")
                        else:
                            marks_obtained = m_val
                    except ValueError:
                        errors.append(f"{stud.name}: Invalid marks format '{raw_mark}'.")
                else:
                    is_absent = True # blank entry treated as absent or unentered

                if not errors:
                    Mark.objects.update_or_create(
                        student=stud,
                        subject=current_subject,
                        defaults={
                            'marks_obtained': marks_obtained,
                            'is_absent': is_absent
                        }
                    )

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            messages.success(request, f"Marks for '{current_subject.name}' saved successfully!")
            return redirect(f"/classes/{class_id}/marks/?subject_id={current_subject.id}")

    # Build existing marks dictionary
    existing_marks = {
        m.student_id: m for m in Mark.objects.filter(subject=current_subject)
    }

    student_entries = []
    for idx, stud in enumerate(students, 1):
        m_obj = existing_marks.get(stud.id)
        student_entries.append({
            'sr_no': idx,
            'student': stud,
            'mark_obj': m_obj,
            'marks_obtained': m_obj.marks_obtained if m_obj else '',
            'is_absent': m_obj.is_absent if m_obj else False,
        })

    context = {
        'classroom': classroom,
        'subjects': subjects,
        'current_subject': current_subject,
        'student_entries': student_entries,
    }
    return render(request, 'marks/marks_entry.html', context)


def excel_upload_view(request):
    guard = require_active_org(request)
    if guard:
        return guard
    """Excel Upload Interface for multi-sheet workbook import with validation feedback."""
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            classroom = form.cleaned_data['classroom']
            excel_file = request.FILES['excel_file']

            success, msgs, summary = process_excel_upload(excel_file, classroom)
            if success:
                messages.success(request, f"Import Success! Imported {summary.get('students_count', 0)} students across {summary.get('subjects_count', 0)} subjects.")
                return redirect('class_detail', class_id=classroom.id)
            else:
                for err in msgs:
                    messages.error(request, err)
    else:
        form = ExcelUploadForm()

    context = {'form': form}
    return render(request, 'marks/excel_upload.html', context)


def excel_export_view(request, class_id):
    """Downloads formatted Excel workbook for a ClassRoom."""
    classroom = get_object_or_404(ClassRoom, pk=class_id)
    excel_buffer = export_class_excel(classroom)

    filename = f"{classroom.class_name}_{classroom.division}_{classroom.academic_year.name}_Result_Analysis.xlsx"
    filename = filename.replace(" ", "_")

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def grade_rules_view(request):
    guard = require_active_org(request)
    if guard:
        return guard
    """View and edit grade boundary settings and standard rules."""
    ensure_default_grade_rules()
    rules = GradeRule.objects.all()

    if request.method == 'POST':
        for rule in rules:
            min_k = f"min_{rule.id}"
            max_k = f"max_{rule.id}"
            desc_k = f"desc_{rule.id}"

            if min_k in request.POST and max_k in request.POST:
                rule.min_percentage = float(request.POST[min_k])
                rule.max_percentage = float(request.POST[max_k])
                rule.description = request.POST.get(desc_k, '')
                rule.save()

        messages.success(request, "Grade rules updated successfully!")
        return redirect('grade_rules')

    context = {'rules': rules}
    return render(request, 'marks/grade_rules.html', context)


def add_student_view(request, class_id):
    """Quick modal/form POST handler to add a student to a class."""
    classroom = get_object_or_404(ClassRoom, pk=class_id)
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.classroom = classroom
            student.save()
            messages.success(request, f"Student '{student.name}' added.")
    return redirect('class_detail', class_id=class_id)


def add_subject_view(request, class_id):
    """Quick modal/form POST handler to add a subject to a class."""
    classroom = get_object_or_404(ClassRoom, pk=class_id)
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.classroom = classroom
            subject.save()
            messages.success(request, f"Subject '{subject.name}' added.")
    return redirect('class_detail', class_id=class_id)


def seed_sample_data(request):
    """
    Seeds the 5-student sample dataset from the problem statement:
    - Std III A (2022-23)
    - 6 subjects: English, Marathi, Hindi, Maths, EVS, Computer
    - 5 sample students with realistic scores & absent test case
    """
    ensure_default_grade_rules()
    
    with transaction.atomic():
        year, _ = AcademicYear.objects.get_or_create(name="2022-23", defaults={'is_current': True})
        classroom, _ = ClassRoom.objects.get_or_create(
            class_name="Std III",
            division="A",
            academic_year=year,
            defaults={'class_teacher': 'Mrs. Sunita Patil', 'pass_percentage': 33.0}
        )

        sub_names = [
            ('English', 100, 1),
            ('Marathi', 100, 2),
            ('Hindi', 100, 3),
            ('Maths', 100, 4),
            ('EVS', 100, 5),
            ('Computer', 100, 6) # Includes Computer subject
        ]

        subject_objs = {}
        for sname, out_of, order in sub_names:
            sub, _ = Subject.objects.get_or_create(
                classroom=classroom,
                name=sname,
                defaults={'out_of_marks': out_of, 'order': order}
            )
            subject_objs[sname] = sub

        sample_students = [
            (1, "Aarav Sharma", {'English': 92, 'Marathi': 88, 'Hindi': 90, 'Maths': 95, 'EVS': 94, 'Computer': 96}),
            (2, "Bhavna Patel", {'English': 82, 'Marathi': 78, 'Hindi': 85, 'Maths': 80, 'EVS': 84, 'Computer': 88}),
            (3, "Chetan Deshmukh", {'English': 65, 'Marathi': 62, 'Hindi': 70, 'Maths': 58, 'EVS': 64, 'Computer': 72}),
            (4, "Divya Kulkarni", {'English': 45, 'Marathi': 52, 'Hindi': 48, 'Maths': 38, 'EVS': 50, 'Computer': 42}),
            (5, "Eshan Verma", {'English': 88, 'Marathi': None, 'Hindi': 82, 'Maths': 90, 'EVS': 85, 'Computer': 89}), # Absent in Marathi
        ]

        for roll, name, scores in sample_students:
            stud, _ = Student.objects.get_or_create(
                classroom=classroom,
                roll_number=roll,
                defaults={'name': name}
            )
            for sub_name, score in scores.items():
                sub = subject_objs[sub_name]
                is_absent = (score is None)
                Mark.objects.update_or_create(
                    student=stud,
                    subject=sub,
                    defaults={'marks_obtained': score, 'is_absent': is_absent}
                )

    messages.success(request, f"Sample dataset loaded for Std III A (5 students, 6 subjects including Computer)!")
    return redirect('class_detail', class_id=classroom.id)


# ---------------------------------------------------------------------------
# Admin: Join Request Approval Workflow
# ---------------------------------------------------------------------------

@login_required
def join_requests_view(request):
    """
    Admin-only page listing all pending (and recent) join requests for their org.
    """
    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')

    if not profile.is_admin:
        messages.error(request, "Only administrators can manage join requests.")
        return redirect('dashboard')

    org = profile.organization
    requests_qs = JoinRequest.objects.filter(organization=org).select_related('teacher_user')

    return render(request, 'marks/join_requests.html', {
        'join_requests': requests_qs,
        'pending_count': requests_qs.filter(status=JoinRequest.STATUS_PENDING).count(),
    })


@login_required
def approve_join_request(request, request_id):
    """Approve a teacher's join request — links them to the org."""
    from django.utils import timezone

    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')

    if not profile.is_admin:
        messages.error(request, "Only administrators can approve join requests.")
        return redirect('dashboard')

    join_req = get_object_or_404(JoinRequest, pk=request_id, organization=profile.organization)

    if join_req.status != JoinRequest.STATUS_PENDING:
        messages.warning(request, f"This request has already been {join_req.status}.")
        return redirect('join_requests')

    with transaction.atomic():
        # Link teacher to org
        teacher_profile = join_req.teacher_user.profile
        teacher_profile.organization = profile.organization
        teacher_profile.save()
        # Mark request approved
        join_req.status = JoinRequest.STATUS_APPROVED
        join_req.responded_at = timezone.now()
        join_req.save()

    messages.success(
        request,
        f"✅ {join_req.teacher_user.get_full_name() or join_req.teacher_user.username} has been approved "
        f"and can now access the school workspace."
    )
    return redirect('join_requests')


@login_required
def reject_join_request(request, request_id):
    """Reject a teacher's join request."""
    from django.utils import timezone

    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')

    if not profile.is_admin:
        messages.error(request, "Only administrators can reject join requests.")
        return redirect('dashboard')

    join_req = get_object_or_404(JoinRequest, pk=request_id, organization=profile.organization)

    if join_req.status != JoinRequest.STATUS_PENDING:
        messages.warning(request, f"This request has already been {join_req.status}.")
        return redirect('join_requests')

    with transaction.atomic():
        join_req.status = JoinRequest.STATUS_REJECTED
        join_req.responded_at = timezone.now()
        join_req.save()

    messages.info(
        request,
        f"❌ Request from {join_req.teacher_user.get_full_name() or join_req.teacher_user.username} has been rejected."
    )
    return redirect('join_requests')


# ---------------------------------------------------------------------------
# Admin: Teacher Permission Management
# ---------------------------------------------------------------------------

@login_required
def teacher_permissions_view(request):
    """Admin page — manage teacher access (editor/viewer) per class & subject."""
    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')
    if not profile.is_admin:
        messages.error(request, "Only administrators can manage teacher permissions.")
        return redirect('dashboard')

    org = profile.organization
    teachers = UserProfile.objects.filter(
        organization=org, role=UserProfile.ROLE_TEACHER
    ).select_related('user')
    classes = ClassRoom.objects.filter(organization=org).prefetch_related('subjects').select_related('academic_year')

    selected_teacher = None
    teacher_perms    = []
    selected_teacher_id = request.GET.get('teacher_id')
    if selected_teacher_id:
        try:
            selected_teacher = User.objects.get(pk=selected_teacher_id, profile__organization=org)
            teacher_perms = TeacherPermission.objects.filter(
                teacher=selected_teacher
            ).select_related('classroom', 'subject', 'classroom__academic_year')
        except User.DoesNotExist:
            pass

    return render(request, 'marks/teacher_permissions.html', {
        'teachers': teachers,
        'classes': classes,
        'selected_teacher': selected_teacher,
        'teacher_perms': teacher_perms,
        'role_editor': TeacherPermission.ROLE_EDITOR,
        'role_viewer': TeacherPermission.ROLE_VIEWER,
    })


@login_required
def grant_permission_view(request):
    """POST: Create or update a TeacherPermission record."""
    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')
    if not profile.is_admin:
        messages.error(request, "Only administrators can grant permissions.")
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('teacher_permissions')

    teacher_id = request.POST.get('teacher_id')
    class_id   = request.POST.get('class_id')
    subject_id = request.POST.get('subject_id') or None
    role       = request.POST.get('role', TeacherPermission.ROLE_VIEWER)

    teacher   = get_object_or_404(User, pk=teacher_id)
    classroom = get_object_or_404(ClassRoom, pk=class_id, organization=profile.organization)
    subject   = get_object_or_404(Subject, pk=subject_id, classroom=classroom) if subject_id else None

    TeacherPermission.objects.update_or_create(
        teacher=teacher, classroom=classroom, subject=subject,
        defaults={'role': role, 'granted_by': request.user}
    )
    scope = subject.name if subject else 'All Subjects'
    messages.success(request, f"\u2705 {teacher.get_full_name() or teacher.username} granted {role} access to {classroom} / {scope}.")
    return redirect(f"/teacher-permissions/?teacher_id={teacher_id}")


@login_required
def revoke_permission_view(request, perm_id):
    """POST: Delete a TeacherPermission record."""
    try:
        profile = request.user.profile
    except Exception:
        return redirect('dashboard')
    if not profile.is_admin:
        messages.error(request, "Only administrators can revoke permissions.")
        return redirect('dashboard')

    perm = get_object_or_404(
        TeacherPermission, pk=perm_id,
        classroom__organization=profile.organization
    )
    teacher_id = perm.teacher_id
    scope = perm.subject.name if perm.subject else 'All Subjects'
    label = f"{perm.teacher.username} / {perm.classroom} / {scope}"
    perm.delete()
    messages.info(request, f"\u274c Permission removed: {label}.")
    return redirect(f"/teacher-permissions/?teacher_id={teacher_id}")
