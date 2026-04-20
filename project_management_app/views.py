from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, UpdateView, CreateView, FormView, DetailView, DeleteView, View
from django.urls import reverse_lazy
from .models import Project, Task, CustomUser, Approval, Notification, BudgetRecord, Department
from .forms import TaskUpdateForm, ProjectCreateForm, ApprovalForm, BudgetRecordForm, TaskCreateForm
from django.contrib import messages
from .utils import create_notification
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.core.exceptions import PermissionDenied

# Create your views here.
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "project_management_app/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.role == CustomUser.Role.MEMBER:
            context["tasks"] = Task.objects.filter(
                assignee=user
            ).select_related("project")

        elif user.role == CustomUser.Role.APPLICANT:
            context["projects"] = Project.objects.filter(
                applicant=user
            ).select_related("department")

        elif user.role == CustomUser.Role.MANAGER:
            context["projects"] = Project.objects.filter(
                department=user.department,)
            #    status=Project.Status.PENDING_MANAGER,
            #)

        elif user.role == CustomUser.Role.HQ:
            context["projects"] = Project.objects.all().select_related(
                "department", "applicant"
            )

            projects = Project.objects.all()

            context["has_over_budget"] = any(
                p.total_actual_amount > p.estimated_budget
                for p in projects
            )
            context["over_budget_count"] = sum(
                1 for p in projects if p.is_over_budget
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

    def form_valid(self, form):
        task = form.save(commit=False)
        task.project = self.project
        task.save()
        return redirect("project_detail", pk=self.project.pk)

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

    def form_valid(self, form):
        form.instance.applicant = self.request.user
        form.instance.status = Project.Status.PENDING_MANAGER
        response = super().form_valid(form)

        managers = CustomUser.objects.filter(
            department=form.instance.department,
            role=CustomUser.Role.MANAGER,
        )

        for manager in managers:
            create_notification(
                recipient=manager,
                project=form.instance,
                message=f"新規案件『{form.instance.name}』の承認依頼があります。",
            )
        
        messages.success(self.request, "案件を申請しました。")
        return response


class ProjectStartView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(
            Project,
            pk=pk,
            applicant=request.user,  # ← 申請者のみ
            status=Project.Status.APPROVED
        )

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
                "budget_records",
                "approvals",
            )
        )
    

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "project_management_app/notifications.html"
    context_object_name = "notifications"
    
    def get_queryset(self):
        LIMIT = 15

        self.request.user.notifications.filter(
            is_read=False
        ).update(is_read=True)

        return self.request.user.notifications.select_related(
            "project"
        ).order_by("-created_at")[:LIMIT]


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

    def form_valid(self, form):
        form.instance.project = self.project
        messages.success(self.request, "予算実績を登録しました。")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("my_projects")