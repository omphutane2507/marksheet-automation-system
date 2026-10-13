"""
Pure calculation functions for School Marks Analysis & Dashboard.
Designed to be decoupled, deterministic, and easy to unit test.
"""

# Default Grade Rules dictionary if DB is not queried directly
DEFAULT_GRADE_RULES = [
    {'grade': 'A', 'min_percentage': 90.0, 'max_percentage': 100.0},
    {'grade': 'B', 'min_percentage': 80.0, 'max_percentage': 90.0},
    {'grade': 'C', 'min_percentage': 60.0, 'max_percentage': 80.0},
    {'grade': 'D', 'min_percentage': 33.0, 'max_percentage': 60.0},
    {'grade': 'E', 'min_percentage': 0.0, 'max_percentage': 33.0},
]


def determine_grade(percentage, grade_rules=None):
    """
    Determines letter grade from percentage with continuous boundary logic.
    Handles decimals seamlessly (e.g., 89.5 -> 'B', 59.5 -> 'D', 32.8 -> 'E').
    
    :param percentage: float value between 0 and 100
    :param grade_rules: list of dicts/objects containing 'grade', 'min_percentage', 'max_percentage'
    :return: str letter grade ('A', 'B', 'C', 'D', 'E')
    """
    if percentage is None:
        return "AB"

    # Clamp percentage to 0-100 range
    percentage = max(0.0, min(100.0, float(percentage)))

    if not grade_rules:
        grade_rules = DEFAULT_GRADE_RULES

    def _get_min(rule_obj):
        return rule_obj.get('min_percentage', 0.0) if isinstance(rule_obj, dict) else getattr(rule_obj, 'min_percentage', 0.0)

    def _get_grade(rule_obj):
        return rule_obj.get('grade', 'E') if isinstance(rule_obj, dict) else getattr(rule_obj, 'grade', 'E')

    sorted_rules = sorted(grade_rules, key=_get_min, reverse=True)

    for rule in sorted_rules:
        min_p = _get_min(rule)
        grade = _get_grade(rule)
        
        # Continuous comparison: top tier includes boundary, lower tiers check >= min_p
        if percentage >= min_p:
            return grade

    return "E"


def calculate_student_subject(marks_obtained, out_of_marks, is_absent, grade_rules=None):
    """
    Calculates percentage and grade for a single subject mark record.
    
    :param marks_obtained: float or None
    :param out_of_marks: float (> 0)
    :param is_absent: bool flag
    :param grade_rules: optional custom grade rules list
    :return: dict with {marks_obtained, out_of_marks, percentage, grade, is_absent}
    """
    if is_absent or marks_obtained is None:
        return {
            'marks_obtained': None,
            'out_of_marks': float(out_of_marks),
            'percentage': None,
            'grade': 'AB',
            'is_absent': True,
        }

    marks = float(marks_obtained)
    out_of = float(out_of_marks) if out_of_marks > 0 else 100.0
    percentage = round((marks / out_of) * 100.0, 2)
    grade = determine_grade(percentage, grade_rules)

    return {
        'marks_obtained': marks,
        'out_of_marks': out_of,
        'percentage': percentage,
        'grade': grade,
        'is_absent': False,
    }


def calculate_student_consolidated(student_name, roll_number, subject_marks, pass_percentage=33.0, grade_rules=None):
    """
    Calculates total marks, total percentage, overall grade, and pass status for a student across ALL subjects.
    Fixes Excel error: Computes total across ALL active subjects dynamically (no subject omitted).
    
    :param student_name: str
    :param roll_number: int
    :param subject_marks: list of dicts [{'subject_name': 'Maths', 'marks_obtained': 85, 'out_of_marks': 100, 'is_absent': False}, ...]
    :param pass_percentage: float (default 33.0)
    :param grade_rules: optional custom grade rules list
    :return: dict with student overall details & subject breakout
    """
    total_obtained = 0.0
    total_out_of = 0.0
    absent_count = 0
    present_count = 0
    subject_details = []

    for item in subject_marks:
        sub_name = item['subject_name']
        marks_obtained = item.get('marks_obtained')
        out_of = float(item.get('out_of_marks', 100.0))
        is_absent = bool(item.get('is_absent', False))

        sub_res = calculate_student_subject(marks_obtained, out_of, is_absent, grade_rules)
        sub_res['subject_name'] = sub_name
        subject_details.append(sub_res)

        if sub_res['is_absent']:
            absent_count += 1
        else:
            present_count += 1
            total_obtained += sub_res['marks_obtained']
            total_out_of += out_of

    all_absent = (present_count == 0)

    if all_absent:
        overall_percentage = 0.0
        overall_grade = 'AB'
        is_pass = False
    else:
        # Calculate percentage based on valid present subjects out-of total
        overall_percentage = round((total_obtained / total_out_of) * 100.0, 2) if total_out_of > 0 else 0.0
        overall_grade = determine_grade(overall_percentage, grade_rules)
        is_pass = overall_percentage >= float(pass_percentage)

    return {
        'roll_number': roll_number,
        'student_name': student_name,
        'total_obtained': round(total_obtained, 2),
        'total_out_of': round(total_out_of, 2),
        'overall_percentage': overall_percentage,
        'overall_grade': overall_grade,
        'is_pass': is_pass,
        'all_absent': all_absent,
        'present_count': present_count,
        'absent_count': absent_count,
        'subjects': subject_details,
    }


def calculate_subject_analysis(subject_name, out_of_marks, mark_records, pass_percentage=33.0, grade_rules=None):
    """
    Generates result analysis table for a single subject:
    - Count per grade (A, B, C, D, E, AB)
    - Subject average marks & percentage (excluding AB)
    - Pass count, fail count, pass percentage
    """
    grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'AB': 0}
    total_students = len(mark_records)
    total_marks_sum = 0.0
    total_percentage_sum = 0.0
    present_count = 0
    absent_count = 0
    pass_count = 0
    fail_count = 0

    for mark in mark_records:
        sub_res = calculate_student_subject(
            mark.get('marks_obtained'),
            out_of_marks,
            mark.get('is_absent', False),
            grade_rules
        )
        g = sub_res['grade']
        grade_counts[g] = grade_counts.get(g, 0) + 1

        if sub_res['is_absent']:
            absent_count += 1
        else:
            present_count += 1
            total_marks_sum += sub_res['marks_obtained']
            total_percentage_sum += sub_res['percentage']

            if sub_res['percentage'] >= pass_percentage:
                pass_count += 1
            else:
                fail_count += 1

    subject_avg_marks = round(total_marks_sum / present_count, 2) if present_count > 0 else 0.0
    subject_avg_percentage = round(total_percentage_sum / present_count, 2) if present_count > 0 else 0.0
    subject_pass_percent = round((pass_count / present_count) * 100.0, 2) if present_count > 0 else 0.0

    return {
        'subject_name': subject_name,
        'out_of_marks': out_of_marks,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'subject_avg_marks': subject_avg_marks,
        'subject_avg_percentage': subject_avg_percentage,
        'subject_pass_percent': subject_pass_percent,
        'grade_counts': grade_counts,
    }


def calculate_class_overview(class_students_data, pass_percentage=33.0, grade_rules=None):
    """
    Computes class-wide consolidated result analysis:
    - Overall grade distribution (A, B, C, D, E, AB)
    - Class Average Percentage
    - Overall Pass Percentage
    - Toppers List (Top 5)
    - Needs Attention List (Grades D & E)
    """
    total_students = len(class_students_data)
    grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'AB': 0}
    pass_count = 0
    fail_count = 0
    sum_percentages = 0.0
    active_students_count = 0

    toppers = []
    needs_attention = []

    for stud in class_students_data:
        g = stud['overall_grade']
        grade_counts[g] = grade_counts.get(g, 0) + 1

        if not stud['all_absent']:
            active_students_count += 1
            sum_percentages += stud['overall_percentage']
            if stud['is_pass']:
                pass_count += 1
            else:
                fail_count += 1

        if g in ['D', 'E']:
            needs_attention.append({
                'roll_number': stud['roll_number'],
                'student_name': stud['student_name'],
                'overall_percentage': stud['overall_percentage'],
                'overall_grade': stud['overall_grade'],
            })

    class_avg_percentage = round(sum_percentages / active_students_count, 2) if active_students_count > 0 else 0.0
    overall_pass_percentage = round((pass_count / active_students_count) * 100.0, 2) if active_students_count > 0 else 0.0

    # Sort students for toppers (excluding all-absent)
    valid_students = [s for s in class_students_data if not s['all_absent']]
    sorted_students = sorted(valid_students, key=lambda s: s['overall_percentage'], reverse=True)
    toppers = [
        {
            'rank': idx + 1,
            'roll_number': s['roll_number'],
            'student_name': s['student_name'],
            'total_obtained': s['total_obtained'],
            'total_out_of': s['total_out_of'],
            'overall_percentage': s['overall_percentage'],
            'overall_grade': s['overall_grade'],
        }
        for idx, s in enumerate(sorted_students[:5])
    ]

    return {
        'total_students': total_students,
        'active_students': active_students_count,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'class_avg_percentage': class_avg_percentage,
        'overall_pass_percentage': overall_pass_percentage,
        'grade_counts': grade_counts,
        'toppers': toppers,
        'needs_attention': needs_attention,
    }
