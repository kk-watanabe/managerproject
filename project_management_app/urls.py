from django.urls import path
from .views import (
    HomeView,
    MyTaskListView,
    TaskCreateView,
    TaskDetailView,
    TaskUpdateView,
    TaskDeleteView,
    MyProjectListView,
    ProjectCreateView,
    ProjectStartView,
    ProjectDetailView,
    BudgetRecordCreateView,
    DepartmentProjectListView,
    DepartmentApprovalListView,
    DepartmentApprovalView,
    HQProjectListView,
    HQApprovalListView,
    HQApprovalView,
    NotificationListView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    path('tasks/', MyTaskListView.as_view(), name='my_tasks'),
    path("projects/<int:project_pk>/tasks/create/", TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path('tasks/<int:pk>/edit/', TaskUpdateView.as_view(), name='task_update'),
    path("tasks/<int:pk>/delete/", TaskDeleteView.as_view(), name="task_delete"),

    path("projects/", MyProjectListView.as_view(), name="my_projects"),
    path("projects/new/", ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/start/", ProjectStartView.as_view(), name="project_start"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project_detail"),

    path("projects/<int:pk>/budget/add/", BudgetRecordCreateView.as_view(), name="budget_record_add"),

    path("department/projects/", DepartmentProjectListView.as_view(), name="department_project_list"),
    path("department/approvals/", DepartmentApprovalListView.as_view(), name="department_approval_list"),
    path("department/approvals/<int:pk>/", DepartmentApprovalView.as_view(), name="department_approval"),

    path("hq/projects/", HQProjectListView.as_view(), name="hq_project_list"),
    path("hq/approvals/", HQApprovalListView.as_view(), name="hq_approval_list"),
    path("hq/approvals/<int:pk>/", HQApprovalView.as_view(), name="hq_approval"),

    path("notifications/", NotificationListView.as_view(), name="notifications"),
]
