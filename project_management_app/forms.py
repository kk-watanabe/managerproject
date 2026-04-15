from django import forms
from .models import Task, Project, Approval

class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status", "progress_rate", "description", "due_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "department",
            "estimated_budget",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = Approval
        fields = ["examination", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }