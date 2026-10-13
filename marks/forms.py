from django import forms
from marks.models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule


class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ['class_name', 'division', 'academic_year', 'class_teacher', 'pass_percentage']
        widgets = {
            'class_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Std III'}),
            'division': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'class_teacher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teacher name'}),
            'pass_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
        }


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['roll_number', 'name']
        widgets = {
            'roll_number': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Roll No'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Full Name'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'out_of_marks', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject Name (e.g. Maths)'}),
            'out_of_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }


class ExcelUploadForm(forms.Form):
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Target Class & Division"
    )
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'}),
        label="Upload Excel Workbook (.xlsx)"
    )


class GradeRuleForm(forms.ModelForm):
    class Meta:
        model = GradeRule
        fields = ['grade', 'min_percentage', 'max_percentage', 'description']
        widgets = {
            'grade': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'min_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'max_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
