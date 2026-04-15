from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, UpdateView, CreateView, FormView
from django.urls import reverse_lazy
from .models import Project, Task, CustomUser, Approval
from .forms import TaskUpdateForm, ProjectCreateForm, ApprovalForm
from django.contrib import messages

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
        
        return context


class MyTaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'project_management_app/my_tasks.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        return (
            Task.objects.filter(
                assignee=self.request.user
            )
            .select_related('project')
            .order_by("due_date")
        )


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskUpdateForm
    template_name = 'project_management_app/task_update.html'
    success_url = reverse_lazy("my_tasks")

    def get_queryset(self):
        return Task.objects.filter(
            assignee=self.request.user
        ).select_related('project')
    
    def form_valid(self, form):
        messages.success(self.request, "タスクを更新しました。")
        return super().form_valid(form)


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectCreateForm
    template_name = "project_management_app/project_create.html"
    success_url = reverse_lazy("my_projects")

    def form_valid(self, form):
        form.instance.applicant = self.request.user
        form.instance.status = Project.Status.PENDING_MANAGER
        messages.success(self.request, "案件を申請しました。")
        return super().form_valid(form)


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


class DepartmentApprovalListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/department_approval_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            Project.objects.filter(
                department=self.request.user.department,
                status=Project.Status.PENDING_MANAGER,
            )
            .select_related("applicant", "department")
            .order_by("-created_at")
        )


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
        else:
            self.project.status = Project.Status.REJECTED

        self.project.save(update_fields=["status", "updated_at"])

        messages.success(self.request, "一次承認を完了しました。")
        return redirect("department_approval_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context


class HQApprovalListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project_management_app/hq_approval_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            Project.objects.filter(
                status=Project.Status.PENDING_HQ
            )
            .select_related("department", "applicant")
            .order_by("-created_at")
        )


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
            self.project.status = Project.Status.IN_PROGRESS
        else:
            self.project.status = Project.Status.REJECTED

        self.project.save(update_fields=["status", "updated_at"])

        messages.success(self.request, "最終承認を完了しました。")
        return redirect("hq_approval_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context