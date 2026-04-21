from django import forms
from django.utils import timezone
from .models import Task, Project, Approval, BudgetRecord, Department

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
            "start_date",
            "due_date",
            "estimated_budget",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 本部を除外
        self.fields["department"].queryset = Department.objects.filter(
            is_headquarters=False
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        due_date = cleaned_data.get("due_date")
        today = timezone.now().date()

        # 開始日が過去
        if start_date and start_date < today:
            self.add_error("start_date", "開始日は今日以降の日付を指定してください。")

        # 期限が過去
        if due_date and due_date < today:
            self.add_error("due_date", "期限は今日以降の日付を指定してください。")

        # 期限 < 開始日
        if start_date and due_date and due_date < start_date:
            self.add_error("due_date", "期限は開始日以降に設定してください。")

        return cleaned_data


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