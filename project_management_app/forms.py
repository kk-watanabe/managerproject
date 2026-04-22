from django import forms
from django.utils import timezone
from .models import Task, Project, Approval, BudgetPlan, BudgetRecord, Comment
from django.forms import inlineformset_factory

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
            "start_date",
            "due_date",
            "estimated_budget",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
    
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


BudgetPlanFormSet = inlineformset_factory(
    Project,
    BudgetPlan,
    fields=("category", "planned_amount"),
    extra=3,
    can_delete=True
)


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
        fields = ["category", "item_name", "amount", "recorded_at", "note"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5, "placeholder": "コメントを入力..."})
        }
    
    def clean_content(self):
        content = self.cleaned_data.get("content")

        if not content or not content.strip():
            raise forms.ValidationError("コメントは必須です。")

        return content