from django import forms
from django.utils import timezone
from .models import Task, Project, Approval, BudgetPlan, BudgetRecord, Comment
from django.forms import inlineformset_factory, BaseInlineFormSet

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


class BudgetPlanBaseFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        total = 0
        valid_count = 0  # ★ 追加

        for form in self.forms:
            if not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE", False):
                continue

            category = form.cleaned_data.get("category")
            amount = form.cleaned_data.get("planned_amount")

            # 空行
            if not category and amount is None:
                continue

            # 片方だけ入力チェック
            if category and amount is None:
                raise forms.ValidationError("費目に金額を入力してください")

            if amount and not category:
                raise forms.ValidationError("金額に対応する費目名を入力してください")

            # ★ 有効行としてカウント
            valid_count += 1
            total += amount or 0

        # ★ 1件以上必須
        if valid_count == 0:
            raise forms.ValidationError("少なくとも1件の予算内訳を入力してください")


BudgetPlanFormSet = inlineformset_factory(
    Project,
    BudgetPlan,
    fields=("category", "planned_amount"),
    extra=3,
    can_delete=True,
    formset=BudgetPlanBaseFormSet
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
        fields = ["budget_plan", "item_name", "amount", "recorded_at", "note"]
        widgets = {
            "recorded_at": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        if self.project:
            self.fields["budget_plan"].queryset = (
                self.project.budget_plans.order_by("id")
            )

    def save(self, commit=True):
        obj = super().save(commit=False)

        if not self.project:
            raise ValueError("projectが設定されていません")

        obj.project = self.project

        if commit:
            obj.save()

        return obj


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