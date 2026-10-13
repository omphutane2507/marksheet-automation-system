import pandas as pd
import openpyxl
from django.db import transaction
from marks.models import ClassRoom, Student, Subject, Mark


def process_excel_upload(file_obj, classroom):
    """
    Parses and validates an uploaded Excel workbook for a ClassRoom.
    Workbook format:
    - Sheets per subject (e.g. English, Marathi, Hindi, Maths, EVS, Computer)
    - Columns: SR.NO., ROLL NO (or NAME), NAME OF STUDENT, MARKS (or MARKS OBTAINED)
    - Absent entries indicated by "AB" (case insensitive) or blank/empty with absent flag.
    
    Returns: tuple (success: bool, messages: list[str], summary_dict: dict)
    """
    errors = []
    warnings = []

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as e:
        return False, [f"Failed to open Excel file: {str(e)}"], {}

    sheet_names = wb.sheetnames
    
    # Filter out consolidated and overall analysis summary sheets
    subject_sheets = [s for s in sheet_names if s.strip().lower() not in ['consolidated', 'overall result analysis', 'summary', 'sheet1']]

    if not subject_sheets:
        return False, ["No subject sheets found in the uploaded Excel file."], {}

    parsed_data = {} # { subject_name: [ {roll_number, student_name, marks_obtained, is_absent, row_idx} ] }
    student_registry = {} # { roll_number: student_name }

    for sheet_name in subject_sheets:
        ws = wb[sheet_name]
        data = list(ws.values)
        
        if not data or len(data) < 2:
            warnings.append(f"Sheet '{sheet_name}' is empty or missing data rows.")
            continue

        # Find header row
        header_row_idx = None
        headers = []

        for idx, row in enumerate(data[:10]): # search top 10 rows
            row_str = [str(cell).strip().upper() if cell is not None else '' for cell in row]
            if any('NAME' in cell for cell in row_str) and any('MARK' in cell or 'OBTAINED' in cell for cell in row_str):
                header_row_idx = idx
                headers = row_str
                break

        if header_row_idx is None:
            # Fallback to row 0
            header_row_idx = 0
            headers = [str(cell).strip().upper() if cell is not None else '' for cell in data[0]]

        # Map column indexes
        sr_idx = -1
        name_idx = -1
        marks_idx = -1

        for idx, col in enumerate(headers):
            if 'SR' in col or 'ROLL' in col or 'NO' in col:
                if sr_idx == -1:
                    sr_idx = idx
            if 'NAME' in col or 'STUDENT' in col:
                if name_idx == -1:
                    name_idx = idx
            if 'MARK' in col or 'OBTAINED' in col or 'SCORE' in col:
                if marks_idx == -1:
                    marks_idx = idx

        if name_idx == -1 or marks_idx == -1:
            errors.append(f"Sheet '{sheet_name}': Could not identify required columns ('NAME OF STUDENT' and 'MARKS').")
            continue

        # Target subject out_of_marks (default 100 or fetched from existing DB subject)
        existing_subject = Subject.objects.filter(classroom=classroom, name__iexact=sheet_name.strip()).first()
        out_of_marks = existing_subject.out_of_marks if existing_subject else 100.0

        sheet_records = []

        for row_num, row in enumerate(data[header_row_idx + 1:], start=header_row_idx + 2):
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue # skip empty row

            raw_name = str(row[name_idx]).strip() if row[name_idx] is not None else ''
            if not raw_name or raw_name.upper().startswith(('TOTAL', 'AVERAGE', 'COUNT', 'PERCENTAGE', 'CLASS', 'GRADE')):
                continue # ignore summary/header rows at bottom

            # Determine roll number / sr no
            raw_sr = row[sr_idx] if sr_idx != -1 and row[sr_idx] is not None else len(sheet_records) + 1
            try:
                roll_no = int(float(str(raw_sr).strip()))
            except ValueError:
                roll_no = len(sheet_records) + 1

            student_registry[roll_no] = raw_name

            # Parse marks
            raw_marks = row[marks_idx]
            is_absent = False
            marks_obtained = None

            if raw_marks is None or str(raw_marks).strip() == '':
                is_absent = True
            elif str(raw_marks).strip().upper() in ['AB', 'ABSENT', 'A']:
                is_absent = True
            else:
                try:
                    marks_val = float(str(raw_marks).strip())
                    if marks_val < 0:
                        errors.append(f"Sheet '{sheet_name}', Row {row_num} ({raw_name}): Marks cannot be negative ({marks_val}).")
                    elif marks_val > out_of_marks:
                        errors.append(f"Sheet '{sheet_name}', Row {row_num} ({raw_name}): Marks ({marks_val}) exceeds maximum out-of marks ({out_of_marks}).")
                    else:
                        marks_obtained = marks_val
                except ValueError:
                    errors.append(f"Sheet '{sheet_name}', Row {row_num} ({raw_name}): Invalid marks value '{raw_marks}'. Expected number or 'AB'.")

            sheet_records.append({
                'roll_number': roll_no,
                'student_name': raw_name,
                'marks_obtained': marks_obtained,
                'is_absent': is_absent,
                'row_num': row_num
            })

        parsed_data[sheet_name.strip()] = sheet_records

    if errors:
        return False, errors, {}

    # Save to database in single transaction
    with transaction.atomic():
        # 1. Update/Create Students
        for roll_no, s_name in sorted(student_registry.items()):
            Student.objects.update_or_create(
                classroom=classroom,
                roll_number=roll_no,
                defaults={'name': s_name}
            )

        # 2. Update/Create Subjects and Marks
        total_marks_created = 0
        for sub_name, records in parsed_data.items():
            subject, _ = Subject.objects.get_or_create(
                classroom=classroom,
                name=sub_name,
                defaults={'out_of_marks': 100.0}
            )

            for rec in records:
                student = Student.objects.get(classroom=classroom, roll_number=rec['roll_number'])
                Mark.objects.update_or_create(
                    student=student,
                    subject=subject,
                    defaults={
                        'marks_obtained': rec['marks_obtained'],
                        'is_absent': rec['is_absent']
                    }
                )
                total_marks_created += 1

    summary = {
        'students_count': len(student_registry),
        'subjects_count': len(parsed_data),
        'marks_count': total_marks_created
    }

    return True, ["Excel file successfully uploaded and imported!"], summary
