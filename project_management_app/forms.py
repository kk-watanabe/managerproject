from django import forms
from .models import Task, Project, Approval, BudgetRecord

class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "assignee", "due_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


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
            "applicant",
            "start_date",
            "due_date",
            "estimated_budget",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = Approval
        fields = ["examination", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }


class BudgetRecordForm(forms.ModelForm):
    class Meta:
        model = BudgetRecord
        fields = ["item_name", "amount", "recorded_at", "note"]