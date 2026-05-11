from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, UpdateView, CreateView, FormView, DetailView, DeleteView, View
from django.urls import reverse_lazy
from .models import Project, Task, CustomUser, Approval, Notification, BudgetPlan, BudgetRecord, Department
from .forms import TaskUpdateForm, ProjectCreateForm, ApprovalForm, BudgetRecordForm, TaskCreateForm, CommentForm, BudgetPlanFormSet
from django.contrib import messages
from .utils import create_notification
from django.db.models import Q, Prefetch, Sum
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db import transaction
from collections import defaultdict

# Create your views here.
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "project_management_app/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.role == CustomUser.Role.MEMBER:
            tasks = Task.objects.filter(
                assignee=user
            )
            context["tasks"] = tasks.select_related("project")
            context["has_delayed_tasks"] = any(
                t.is_delayed for t in tasks
            )

        elif user.role == CustomUser.Role.APPLICANT:
            projects = Project.objects.filter(
                applicant=user
            )
            context["projects"] = projects.select_related("department")
            context["has_delayed_tasks"] = any(
                p.has_delayed_tasks for p in projects
            )
            context["has_delayed_projects"] = any(
                p.is_delayed for p in projects
            )

        elif user.role == CustomUser.Role.MANAGER:
            projects = Project.objects.filter(
                department=user.department
            )
            context["projects"] = projects
            context["has_delayed_projects"] = any(
                p.is_delayed for p in projects
            )

        elif user.role == CustomUser.Role.HQ:
            projects = Project.objects.all().select_related(
                "department", "applicant"
            )
            context["projects"] = projects
            context["has_delayed_projects"] = any(
                p.is_delayed for p in projects
            )
        
        return context


class MyTaskListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'project_management_app/my_task_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        user = self.request.user

        return (
            Project.objects.filter(
                Q(applicant=user) |
                Q(tasks__assignee=user)
            )
            .prefetch_related(
                Prefetch(
                "tasks",
                queryset=Task.objects.select_related("assignee").order_by("due_date")
                )
            )
            .distinct()
        )


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskCreateForm
    template_name = "project_management_app/task_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project,
            pk=kwargs["project_pk"],
            applicant=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["department"] = self.project.department
        return kwargs
    
    def form_valid(self, form):
        project = self.project
        task = form.save(commit=False)
        task.project = project
        task.save()

        if project.status == Project.Status.COMPLETED:
            project.status = Project.Status.IN_PROGRESS
            project.completed_at = None
            project.save(update_fields=["status", "completed_at", "updated_at"])
        
        return redirect("project_detail", pk=self.project.pk)

    # テンプレートでproject情報を使う場合のため
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context
    

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "project_management_app/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.select_related(
            "project", "assignee"
        )
    

class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskUpdateForm
    template_name = 'project_management_app/task_update.html'
    success_url = reverse_lazy("my_tasks")

    def get_queryset(self):
        return Task.objects.filter(
            Q(assignee=self.request.user) |
            Q(project__applicant=self.request.user),
            project__status__in=[
                Project.Status.APPROVED,
                Project.Status.IN_PROGRESS
            ]
        ).select_related('project')
    
    def form_valid(self, form):
        response = super().form_valid(form)

        project = self.object.project

        # 全タスクが100%かチェック
        all_done = all(
            task.progress_rate == 100 for task in project.tasks.all()
        )

        if all_done and project.status == Project.Status.IN_PROGRESS:
            project.status = Project.Status.COMPLETED
            project.completed_at = timezone.now()
            project.save(update_fields=["status", "completed_at", "updated_at"])

        messages.success(self.request, "タスクを更新しました。")
        return response


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "project_management_app/task_confirm_delete.html"
    context_object_name = "task"
    
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        project = task.project

        # 申請者のみ削除可能
        if request.user != project.applicant:
            raise PermissionDenied

        #if project.status != Project.Status.IN_PROGRESS:
        #    raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object.project  # 先に保持

        response = super().post(request, *args, **kwargs)

        # 削除後に進捗更新
        project.update_progress()

        return response
    
    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.project.pk})
    

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectCreateForm
    template_name = "project_management_app/project_create.html"
    success_url = reverse_lazy("my_projects")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            context["formset"] = BudgetPlanFormSet(
                self.request.POST,
                prefix="form"
            )
        else:
            context["formset"] = BudgetPlanFormSet(
                prefix="form"
            )

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        form.instance.applicant = self.request.user
        form.instance.department = self.request.user.department
        form.instance.status = Project.Status.PENDING_MANAGER

        if not formset.is_valid():
            return self.form_invalid(form)

        total = sum(
            f.cleaned_data.get("planned_amount") or 0
            for f in formset.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
        )

        if total != form.instance.estimated_budget:
            form.add_error(None, "内訳合計が予算と一致しません")
            return self.form_invalid(form)
        
        
        with transaction.atomic():
            self.object = form.save()

            formset.instance = self.object
            formset.save()

        # 通知
        managers = CustomUser.objects.filter(
            department=self.object.department,
            role=CustomUser.Role.MANAGER,
        )

        for manager in managers:
            create_notification(
                recipient=manager,
                project=self.object,
                message=f"新規案件『{self.object.name}』の承認依頼があります。",
            )

        messages.success(self.request, "案件を申請しました。")
        return redirect(self.success_url)


class ProjectStartView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(
            Project,
            pk=pk,
            applicant=request.user,  # ← 申請者のみ
            status=Project.Status.APPROVED
        )

        if project.status != Project.Status.APPROVED:
            raise PermissionDenied

        project.status = Project.Status.IN_PROGRESS
        project.save(update_fields=["status", "updated_at"])

        return redirect("project_detail", pk=project.pk)

        
class MyProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/my_projects.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            Project.objects.filter(
                applicant=self.request.user
            )
            .select_related("department")
            .order_by("-created_at")
        )


class DepartmentProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/department_project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        return (
            Project.objects.filter(
                department=self.request.user.department
            )
            .select_related("applicant", "department")
            .order_by("-created_at")
        )
    

class DepartmentApprovalListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/department_approval_list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        department = self.request.user.department

        # 承認待ち
        context["pending_projects"] = Project.objects.filter(
            department=department,
            status=Project.Status.PENDING_MANAGER
        ).select_related(
            "applicant", "department"
        ).order_by("-created_at")


        # 承認履歴
        context["approval_histories"] = Approval.objects.filter(
            project__department=department,
            level=Approval.ApprovalLevel.DEPARTMENT
        ).select_related(
            "project", "approver"
        ).order_by("-examined_at")[:20]  # 最新20件

        return context


class DepartmentApprovalView(LoginRequiredMixin, FormView):
    template_name = "project_management_app/department_approval.html"
    form_class = ApprovalForm

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project,
            pk=kwargs["pk"],
            department=request.user.department,
            status=Project.Status.PENDING_MANAGER,
        )

        # 部門管理者のみ承認可能
        if request.user.role != CustomUser.Role.MANAGER:
            raise PermissionDenied
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.save(commit=False)
        approval.project = self.project
        approval.approver = self.request.user
        approval.level = Approval.ApprovalLevel.DEPARTMENT
        approval.save()

        if approval.examination == Approval.Examination.APPROVED:
            self.project.status = Project.Status.PENDING_HQ
            self.project.save(update_fields=["status", "updated_at"])

            # 本部へ通知（承認時のみ）
            hq_users = CustomUser.objects.filter(
                role=CustomUser.Role.HQ
            )

            for hq_user in hq_users:
                create_notification(
                    recipient=hq_user,
                    project=self.project,
                    message=f"案件『{self.project.name}』が本部承認待ちです。",
                )

            # 申請者へ通知
            create_notification(
                recipient=self.project.applicant,
                project=self.project,
                message=f"案件『{self.project.name}』が部門承認され、本部承認待ちになりました。",
            )

        else:
            self.project.status = Project.Status.REJECTED
            self.project.save(update_fields=["status", "updated_at"])

            # 申請者へ却下通知
            create_notification(
                recipient=self.project.applicant,
                project=self.project,
                message=f"案件『{self.project.name}』は部門管理者により却下されました。",
            )
        
        messages.success(self.request, "一次承認を完了しました。")
        return redirect("department_approval_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context


class HQProjectListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = "project_management_app/hq_project_list.html"
    context_object_name = "departments"

    def get_queryset(self):
        return Department.objects.filter(is_headquarters=False).prefetch_related(
            Prefetch(
                "projects",
                queryset=Project.objects.select_related("applicant").order_by("-created_at")
            )
        )
    

class HQApprovalListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/hq_approval_list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 承認待ち
        context["pending_projects"] = Project.objects.filter(
            status=Project.Status.PENDING_HQ
        ).select_related(
            "applicant", "department"
        ).order_by("-created_at")


        # 承認履歴
        context["approval_histories"] = Approval.objects.filter(
            level=Approval.ApprovalLevel.HQ
        ).select_related(
            "project", "approver"
        ).order_by("-examined_at")[:20]  # 最新20件

        return context


class HQApprovalView(LoginRequiredMixin, FormView):
    template_name = "project_management_app/hq_approval.html"
    form_class = ApprovalForm

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project,
            pk=kwargs["pk"],
            status=Project.Status.PENDING_HQ,
        )

        # HQのみ承認可能
        if request.user.role != CustomUser.Role.HQ:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.save(commit=False)
        approval.project = self.project
        approval.approver = self.request.user
        approval.level = Approval.ApprovalLevel.HQ
        approval.save()

        if approval.examination == Approval.Examination.APPROVED:
            self.project.status = Project.Status.APPROVED
            self.project.save(update_fields=["status", "updated_at"])

            create_notification(
                recipient=self.project.applicant,
                project=self.project,
                message=f"案件『{self.project.name}』が本部で最終承認されました。",
            )

        else:
            self.project.status = Project.Status.REJECTED
            self.project.save(update_fields=["status", "updated_at"])

            create_notification(
                recipient=self.project.applicant,
                project=self.project,
                message=f"案件『{self.project.name}』は本部で却下されました。",
            )
            
        messages.success(self.request, "最終承認を完了しました。")
        return redirect("hq_approval_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "project_management_app/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return (
            Project.objects.select_related(
                "department",
                "applicant"
            )
            .prefetch_related(
                "tasks",
                "approvals",
                Prefetch(
                    "budget_plans",
                    queryset=BudgetPlan.objects.prefetch_related("records")
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        # ■ サマリー
        plans = project.budget_plans.annotate(
            actual=Sum("records__amount")
        )

        for p in plans:
            actual = p.actual or 0
            planned = p.planned_amount or 0

            p.diff = actual - planned
            p.rate = round(actual / planned * 100, 1) if planned > 0 else 0

        context["budget_summary"] = plans

        # ■ 明細（全件）
        context["budget_records"] = project.budget_records.select_related(
            "budget_plan"
        ).order_by("-recorded_at")

        return context
    

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "project_management_app/notifications.html"
    context_object_name = "notifications"
    
    def get_queryset(self):
        LIMIT = 15

        queryset = self.request.user.notifications.select_related(
            "project"
        ).order_by("-created_at")[:LIMIT]

        # 表示対象だけ既読化
        self.request.user.notifications.filter(
            id__in=[n.id for n in queryset],
            is_read=False
        ).update(is_read=True)

        return queryset


class BudgetPlanDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "project_management_app/budget_plan_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.objects.prefetch_related("budget_plans")
    
    
class BudgetRecordCreateView(LoginRequiredMixin, CreateView):
    model = BudgetRecord
    form_class = BudgetRecordForm
    template_name = "project_management_app/budget_record_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            Project,
            pk=kwargs["pk"],
            applicant=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.project
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.project = self.project
        obj.save()

        self.object = obj

        project = self.project

        # ★ 予算超過チェック
        if project.is_over_budget and not project.is_budget_notified:

            managers = CustomUser.objects.filter(
                department=project.department,
                role=CustomUser.Role.MANAGER
            )

            hq_users = CustomUser.objects.filter(
                role=CustomUser.Role.HQ
            )

            for m in managers:
                create_notification(
                    recipient=m,
                    project=project,
                    message=f"案件『{project.name}』が予算超過しています。対応を確認してください。"
                )

            for hq in hq_users:
                create_notification(
                    recipient=hq,
                    project=project,
                    message=f"案件『{project.name}』が予算超過しています。"
                )

            project.is_budget_notified = True
            project.save(update_fields=["is_budget_notified"])

        messages.success(self.request, "実績を登録しました。")

        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.project.pk})


class ProjectCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.project_id = project.id
            comment.author_id = request.user.id
            comment.save()

        return redirect("project_detail", pk=pk)


class TaskCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task_id = task.id
            comment.author_id = request.user.id
            comment.save()

        return redirect("task_detail", pk=pk)


class DepartmentOverBudgetProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/department_over_budget_projects.html"
    context_object_name = "projects"

    def get_queryset(self):
        user = self.request.user

        projects = Project.objects.filter(department=user.department)

        return [p for p in projects if p.is_over_budget][:20]
    

class HQOverBudgetProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/hq_over_budget_projects.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        projects = Project.objects.select_related("department")

        over_budget = [p for p in projects if p.is_over_budget]

        grouped = defaultdict(list)
        for p in over_budget:
            grouped[p.department].append(p)

        context["grouped_projects"] = dict(grouped)

        return context


class ApprovalDetailView(LoginRequiredMixin, DetailView):
    model = Approval
    template_name = "project_management_app/approval_detail.html"
    context_object_name = "approval"