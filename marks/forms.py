from django import forms
from django.contrib.auth.models import User
from marks.models import AcademicYear, ClassRoom, Student, Subject, Mark, GradeRule, Organization


# ---------------------------------------------------------------------------
# Registration Forms
# ---------------------------------------------------------------------------

class AdminRegisterForm(forms.Form):
    """Form for a new school admin to register and create their organisation."""
    school_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': "e.g. St. Xavier's High School",
            'autocomplete': 'off',
        }),
        label="School / Organisation Name"
    )
    first_name = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={'placeholder': "Your first name"}),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=60, required=False,
        widget=forms.TextInput(attrs={'placeholder': "Your last name (optional)"}),
        label="Last Name"
    )
    username = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={'placeholder': "Choose a unique username", 'autocomplete': 'off'}),
        label="Admin Username"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': "admin@school.com"}),
        label="Email Address"
    )
    password1 = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': "Minimum 6 characters"}),
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': "Confirm your password"}),
        label="Confirm Password"
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned


class TeacherRegisterForm(forms.Form):
    """Form for a teacher to register under an existing admin's organisation."""
    admin_username = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={
            'placeholder': "Enter your school admin's username",
            'autocomplete': 'off',
        }),
        label="Admin Username (Organisation Code)"
    )
    first_name = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={'placeholder': "Your first name"}),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=60, required=False,
        widget=forms.TextInput(attrs={'placeholder': "Your last name (optional)"}),
        label="Last Name"
    )
    username = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={'placeholder': "Choose a unique username", 'autocomplete': 'off'}),
        label="Teacher Username"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': "teacher@school.com"}),
        label="Email Address"
    )
    password1 = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': "Minimum 6 characters"}),
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': "Confirm your password"}),
        label="Confirm Password"
    )

    def clean_admin_username(self):
        admin_uname = self.cleaned_data['admin_username'].strip().lower()
        try:
            admin_user = User.objects.get(username=admin_uname)
            # Must have an owned organization
            org = Organization.objects.get(admin=admin_user)
        except User.DoesNotExist:
            raise forms.ValidationError(
                f"No admin account found with username '{admin_uname}'. "
                "Please ask your school admin for their exact username."
            )
        except Organization.DoesNotExist:
            raise forms.ValidationError(
                f"The user '{admin_uname}' has not set up an organisation yet."
            )
        return admin_uname

    def clean_username(self):
        username = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned


# ---------------------------------------------------------------------------
# Existing App Forms
# ---------------------------------------------------------------------------

class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ['class_name', 'division', 'academic_year', 'class_teacher', 'pass_percentage']
        widgets = {
            'class_name':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Std III'}),
            'division':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A'}),
            'academic_year':    forms.Select(attrs={'class': 'form-select'}),
            'class_teacher':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teacher name'}),
            'pass_percentage':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
        }


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['roll_number', 'name']
        widgets = {
            'roll_number': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Roll No'}),
            'name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Full Name'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'out_of_marks', 'order']
        widgets = {
            'name':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject Name (e.g. Maths)'}),
            'out_of_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
            'order':        forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
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
            'grade':           forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'min_percentage':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'max_percentage':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'description':     forms.TextInput(attrs={'class': 'form-control'}),
        }
