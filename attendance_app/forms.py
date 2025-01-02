from django import forms
from .models import LeaveAttendance


class LeaveAttendanceForm(forms.ModelForm):
    class Meta:
        model = LeaveAttendance
        fields = ['start_date', 'end_date', 'reason', 'type']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 4}),
        }
