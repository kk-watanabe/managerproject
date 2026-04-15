from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import(
    Department,
    CustomUser,
    Project,
    Task,
    Approval,
    Notification,
)

# Register your models here.
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "department",
        "role",
        "is_staff",
    )
    list_filter = ("role", "department", "is_staff")
    search_fields = ("username", "email")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("業務情報", {
            "fields": ("department", "role")
        }),
    )


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = (
        "title",
        "assignee",
        "status",
        "progress_rate",
        "due_date",
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "department",
        "applicant",
        "status",
        "progress_rate",
        "consumption_rate",
        "is_over_budget",
        "created_at",
    )
    list_filter = ("status", "department")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "assignee",
        "status",
        "progress_rate",
        "due_date",
        "is_delayed",
    )
    list_filter = ("status", "project")
    search_fields = ("title", "description")
    ordering = ("due_date",)


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "approver",
        "level",
        "examination",
        "examined_at",
    )
    list_filter = ("level", "examination")
    search_fields = ("project__name", "approver__username")
    ordering = ("-examined_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "project",
        "is_read",
        "created_at",
    )
    list_filter = ("is_read",)
    search_fields = ("recipient__username", "message")
    ordering = ("-created_at",)