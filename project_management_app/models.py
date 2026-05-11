from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Avg, Sum
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


# Create your models here.
class Department(models.Model):
    name = models.CharField("部門", max_length=100, unique=True)
    is_headquarters = models.BooleanField(default=False)

    class Meta:
        verbose_name = "部門"
        verbose_name_plural = "部門"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        MEMBER = "member", "タスク担当者"
        APPLICANT = "applicant", "申請者"
        MANAGER = "manager", "部門管理者"
        HQ = "hq", "本部管理者"
    
    department = models.ForeignKey(
        Department,
        verbose_name="所属部門",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True
    )
    role = models.CharField(
        "ロール",
        max_length=30,
        choices=Role.choices,
        default=Role.APPLICANT
    )

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "下書き"
        PENDING_MANAGER = "pending_manager", "部門承認待ち"
        PENDING_HQ = "pending_hq", "本部承認待ち"
        APPROVED = "approved", "承認済"
        IN_PROGRESS = "in_progress", "進行中"
        COMPLETED = "completed", "完了"
        DELAYED = "delayed", "遅延"
        REJECTED = "rejected", "却下"
    
    name = models.CharField("案件名", max_length=200)
    description = models.TextField("目的・概要")
    applicant = models.ForeignKey(
        CustomUser,
        verbose_name="案件担当者",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_projects"
    )
    department = models.ForeignKey(
        Department,
        verbose_name="担当部門",
        on_delete=models.PROTECT,
        related_name="projects",
    )
    estimated_budget = models.DecimalField(
        "予算額", max_digits=12, decimal_places=0
        )
    is_budget_notified = models.BooleanField(default=False)
    #actual_amount = models.DecimalField(
    #    "実績額", max_digits=12, decimal_places=0, default=0
    #)
    progress_rate = models.PositiveIntegerField(
        "全体進捗率",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    status = models.CharField(
        "ステータス",
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT
    )

    submitted_at = models.DateField("申請日", null=True, blank=True)
    start_date = models.DateField("開始日", null=True, blank=True)
    due_date = models.DateField("期限", null=True, blank=True)
    approved_at = models.DateField("最終承認日", null=True, blank=True)
    completed_at = models.DateField("完了日", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)
    
    class Meta:
        verbose_name = "案件"
        verbose_name_plural = "案件"
        ordering = ["-created_at"]
    
    @property
    def total_actual_amount(self):
        return (
            self.budget_records.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )
    
    @property
    def consumption_rate(self):
        if not self.estimated_budget:
            return 0
        return round(
            (self.total_actual_amount / self.estimated_budget) * 100, 1
        )

    @property
    def has_delayed_tasks(self):
        return any(task.is_delayed for task in self.tasks.all())

    @property
    def is_delayed(self):
        is_delayed = bool(
            self.due_date
            and self.due_date < timezone.now().date()
            and (self.status == self.Status.APPROVED
                 or
                 self.status == self.Status.IN_PROGRESS)
        )

        if is_delayed:
            self.status == self.Status.DELAYED
        
        return is_delayed
    
    @property
    def is_over_budget(self):
        return self.total_actual_amount > self.estimated_budget
    
    @property
    def total_diff(self):
        return self.total_actual_amount - self.estimated_budget

    def update_progress(self):
        avg_progress = self.tasks.aggregate(
            avg=Avg("progress_rate")
        )["avg"] or 0
        new_progress = int(avg_progress)

        if self.progress_rate != new_progress:
            self.progress_rate = new_progress
            self.save(update_fields=["progress_rate"])
    
    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "未着手"
        IN_PROGRESS = "in_progress", "進行中"
        DONE = "done", "完了"
        DELAYED = "delayed", "遅延"

    project = models.ForeignKey(
        Project,
        verbose_name="案件",
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    assignee = models.ForeignKey(
        CustomUser,
        verbose_name="タスク担当者",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    title = models.CharField("タスク名", max_length=200)
    description = models.TextField("詳細", blank=True)
    status = models.CharField(
        "ステータス",
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
    progress_rate = models.PositiveIntegerField(
        "進捗率",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    due_date = models.DateField("期限", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "タスク"
        verbose_name_plural = "タスク"
        ordering = ["due_date", "id"]
    
    def __str__(self):
        return self.title
    
    @property
    def is_delayed(self):
        is_delayed = bool(
            self.due_date
            and self.due_date < timezone.now().date()
            and self.status != self.Status.DONE
            and (self.project.status == self.project.Status.APPROVED
                 or
                 self.project.status == self.project.Status.IN_PROGRESS)
        )
        if is_delayed:
            self.status = self.Status.DELAYED
        
        return is_delayed
    
    def save(self, *args, **kwargs):
        if self.progress_rate == 100:
            self.status = self.Status.DONE
        super().save(*args, **kwargs)
        self.project.update_progress()


class Approval(models.Model):
    class Examination(models.TextChoices):
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"
    
    class ApprovalLevel(models.TextChoices):
        DEPARTMENT = "department", "部門承認"
        HQ = "hq", "本部承認"
    
    project = models.ForeignKey(
        Project,
        verbose_name="案件",
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    approver = models.ForeignKey(
        CustomUser,
        verbose_name="承認者",
        on_delete=models.PROTECT,
        related_name="approvals",
    )
    level = models.CharField(
        "承認段階",
        max_length=20,
        choices=ApprovalLevel.choices,
    )
    examination = models.CharField(
        "審査",
        max_length=20,
        choices=Examination.choices,
    )
    comment = models.TextField("コメント", null=True, blank=True)
    examined_at = models.DateTimeField("審査日時", default=timezone.now)

    class Meta:
        verbose_name = "承認履歴"
        verbose_name_plural = "承認履歴"
        ordering = ["examined_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["project", "level"],
                name="unique_approval_per_project_level"
            )
        ]
    
    def __str__(self):
        return f"{self.project.name} - {self.get_level_display()}"
    

class Notification(models.Model):
    recipient = models.ForeignKey(
        CustomUser,
        verbose_name="通知先",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    project = models.ForeignKey(
        Project,
        verbose_name="対象案件",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.TextField("メッセージ")
    is_read = models.BooleanField("既読", default=False)
    created_at = models.DateTimeField("通知日時", auto_now_add=True)

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.recipient.username}: {self.message[:20]}"
    

class BudgetPlan(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="budget_plans",
        verbose_name="案件"
    )
    category = models.CharField("費目", max_length=100)
    planned_amount = models.DecimalField("予定額", max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "予算内訳"
        verbose_name_plural = "予算内訳"

    def __str__(self):
        return f"{self.category} - {self.project.name}"
    

class BudgetRecord(models.Model):
    project = models.ForeignKey(
        Project,
        verbose_name="案件",
        on_delete=models.CASCADE,
        related_name="budget_records",
    )
    budget_plan = models.ForeignKey(
        BudgetPlan,
        on_delete=models.PROTECT,
        related_name="records",
        verbose_name="費目",
        null=True,
        blank=True,
    )
    item_name = models.CharField("明細", max_length=100)
    amount = models.DecimalField(
        "実績額",
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    recorded_at = models.DateField(
        "計上日",
        default=timezone.now
    )
    note = models.TextField("備考", blank=True)

    class Meta:
        verbose_name = "予算実績"
        verbose_name_plural = "予算実績"
        ordering = ["-recorded_at", "-id"]
    
    def clean(self):
        super().clean()

        if not self.project_id:
            return

        if self.budget_plan_id:
            if self.budget_plan.project_id != self.project_id:
                raise ValidationError("不正な費目です（案件が一致しません）")
    
    def __str__(self):
        return f"{self.project.name} - {self.item_name}"


class Comment(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
        verbose_name="案件"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
        verbose_name="タスク"
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="投稿者"
    )
    content = models.TextField("コメント")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        verbose_name = "コメント"
        verbose_name_plural = "コメント"
        ordering = ["created_at"]