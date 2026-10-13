from django.test import TestCase
from marks.services.calculations import (
    determine_grade,
    calculate_student_subject,
    calculate_student_consolidated,
    calculate_subject_analysis,
    calculate_class_overview,
    DEFAULT_GRADE_RULES
)


class CalculationLogicTestCase(TestCase):
    """Unit tests for calculation logic, continuous grade rules, absent handling, pass %."""

    def test_grading_rules_continuous_decimals(self):
        """Test grade evaluation for exact boundaries and decimal values without gaps."""
        # 90 and above -> A
        self.assertEqual(determine_grade(90.0), 'A')
        self.assertEqual(determine_grade(95.5), 'A')
        self.assertEqual(determine_grade(100.0), 'A')

        # 80 to 89.99 -> B
        self.assertEqual(determine_grade(89.5), 'B')
        self.assertEqual(determine_grade(80.0), 'B')

        # 60 to 79.99 -> C
        self.assertEqual(determine_grade(79.99), 'C')
        self.assertEqual(determine_grade(60.0), 'C')

        # 33 to 59.99 -> D
        self.assertEqual(determine_grade(59.5), 'D')
        self.assertEqual(determine_grade(33.0), 'D')

        # Below 33 -> E
        self.assertEqual(determine_grade(32.8), 'E')
        self.assertEqual(determine_grade(0.0), 'E')

        # None -> AB
        self.assertEqual(determine_grade(None), 'AB')

    def test_absent_student_handling(self):
        """Test single subject calculation with absent flag."""
        # Present student
        res_present = calculate_student_subject(marks_obtained=45, out_of_marks=50, is_absent=False)
        self.assertFalse(res_present['is_absent'])
        self.assertEqual(res_present['percentage'], 90.0)
        self.assertEqual(res_present['grade'], 'A')

        # Absent student
        res_absent = calculate_student_subject(marks_obtained=None, out_of_marks=50, is_absent=True)
        self.assertTrue(res_absent['is_absent'])
        self.assertIsNone(res_absent['percentage'])
        self.assertEqual(res_absent['grade'], 'AB')

    def test_consolidated_student_calculation(self):
        """Test multi-subject consolidated total including 6 subjects (including Computer)."""
        subjects = [
            {'subject_name': 'English', 'marks_obtained': 85, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'Marathi', 'marks_obtained': 90, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'Hindi', 'marks_obtained': 80, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'Maths', 'marks_obtained': 95, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'EVS', 'marks_obtained': 88, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'Computer', 'marks_obtained': 92, 'out_of_marks': 100, 'is_absent': False},
        ]
        
        # Verify dynamic calculation includes all 6 subjects (530 / 600) = 88.33% -> Grade B
        result = calculate_student_consolidated('Aarav Sharma', 1, subjects, pass_percentage=33.0)
        self.assertEqual(result['total_obtained'], 530.0)
        self.assertEqual(result['total_out_of'], 600.0)
        self.assertEqual(result['overall_percentage'], 88.33)
        self.assertEqual(result['overall_grade'], 'B')
        self.assertTrue(result['is_pass'])

    def test_partial_absent_consolidated(self):
        """Test consolidated calculation when student is absent in one subject."""
        subjects = [
            {'subject_name': 'English', 'marks_obtained': 70, 'out_of_marks': 100, 'is_absent': False},
            {'subject_name': 'Maths', 'marks_obtained': None, 'out_of_marks': 100, 'is_absent': True},
        ]
        result = calculate_student_consolidated('Bhavna Patel', 2, subjects, pass_percentage=33.0)
        self.assertEqual(result['total_obtained'], 70.0)
        self.assertEqual(result['total_out_of'], 100.0)  # Excludes out-of for absent subject
        self.assertEqual(result['overall_percentage'], 70.0)
        self.assertEqual(result['overall_grade'], 'C')
        self.assertEqual(result['absent_count'], 1)
        self.assertEqual(result['present_count'], 1)

    def test_pass_percentage_customization(self):
        """Test pass threshold configuration."""
        subjects = [
            {'subject_name': 'Maths', 'marks_obtained': 34, 'out_of_marks': 100, 'is_absent': False}
        ]
        # Pass mark 33% -> Pass
        res_33 = calculate_student_consolidated('Chetan Deshmukh', 3, subjects, pass_percentage=33.0)
        self.assertTrue(res_33['is_pass'])

        # Pass mark 35% -> Fail
        res_35 = calculate_student_consolidated('Chetan Deshmukh', 3, subjects, pass_percentage=35.0)
        self.assertFalse(res_35['is_pass'])

    def test_subject_analysis(self):
        """Test subject level analysis summary and grade distribution."""
        records = [
            {'marks_obtained': 92, 'is_absent': False}, # A
            {'marks_obtained': 82, 'is_absent': False}, # B
            {'marks_obtained': 65, 'is_absent': False}, # C
            {'marks_obtained': 45, 'is_absent': False}, # D
            {'marks_obtained': 20, 'is_absent': False}, # E
            {'marks_obtained': None, 'is_absent': True}, # AB
        ]
        analysis = calculate_subject_analysis('English', 100.0, records, pass_percentage=33.0)
        self.assertEqual(analysis['total_students'], 6)
        self.assertEqual(analysis['present_count'], 5)
        self.assertEqual(analysis['absent_count'], 1)
        self.assertEqual(analysis['grade_counts']['A'], 1)
        self.assertEqual(analysis['grade_counts']['B'], 1)
        self.assertEqual(analysis['grade_counts']['C'], 1)
        self.assertEqual(analysis['grade_counts']['D'], 1)
        self.assertEqual(analysis['grade_counts']['E'], 1)
        self.assertEqual(analysis['grade_counts']['AB'], 1)
        self.assertEqual(analysis['pass_count'], 4)
        self.assertEqual(analysis['fail_count'], 1)
        # Avg marks of 5 present students: (92+82+65+45+20) / 5 = 304 / 5 = 60.8
        self.assertEqual(analysis['subject_avg_marks'], 60.8)

    def test_class_overview_toppers_and_needs_attention(self):
        """Test toppers ranking and needs attention list."""
        students_data = [
            {'roll_number': 1, 'student_name': 'Student 1', 'total_obtained': 550, 'total_out_of': 600, 'overall_percentage': 91.67, 'overall_grade': 'A', 'is_pass': True, 'all_absent': False},
            {'roll_number': 2, 'student_name': 'Student 2', 'total_obtained': 490, 'total_out_of': 600, 'overall_percentage': 81.67, 'overall_grade': 'B', 'is_pass': True, 'all_absent': False},
            {'roll_number': 3, 'student_name': 'Student 3', 'total_obtained': 400, 'total_out_of': 600, 'overall_percentage': 66.67, 'overall_grade': 'C', 'is_pass': True, 'all_absent': False},
            {'roll_number': 4, 'student_name': 'Student 4', 'total_obtained': 250, 'total_out_of': 600, 'overall_percentage': 41.67, 'overall_grade': 'D', 'is_pass': True, 'all_absent': False},
            {'roll_number': 5, 'student_name': 'Student 5', 'total_obtained': 150, 'total_out_of': 600, 'overall_percentage': 25.00, 'overall_grade': 'E', 'is_pass': False, 'all_absent': False},
        ]
        overview = calculate_class_overview(students_data, pass_percentage=33.0)
        self.assertEqual(len(overview['toppers']), 5)
        self.assertEqual(overview['toppers'][0]['student_name'], 'Student 1')
        self.assertEqual(len(overview['needs_attention']), 2) # Student 4 (D) and Student 5 (E)
