from django.urls import path
from .views import (
    HomeView,
    MyTaskListView,
    TaskUpdateView,
    MyProjectListView,
    ProjectCreateView,
    DepartmentApprovalListView,
    DepartmentApprovalView,
    HQApprovalListView,
    HQApprovalView,
    NotificationListView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    path('tasks/', MyTaskListView.as_view(), name='my_tasks'),
    path('tasks/<int:pk>/edit/', TaskUpdateView.as_view(), name='task_update'),

    path("projects/", MyProjectListView.as_view(), name="my_projects"),
    path("projects/new/", ProjectCreateView.as_view(), name="project_create"),

    path("department/approvals/", DepartmentApprovalListView.as_view(), name="department_approval_list"),
    path("department/approvals/<int:pk>/", DepartmentApprovalView.as_view(), name="department_approval"),

    path("hq/approvals/", HQApprovalListView.as_view(), name="hq_approval_list"),
    path("hq/approvals/<int:pk>/", HQApprovalView.as_view(), name="hq_approval"),

    path("notifications/", NotificationListView.as_view(), name="notifications"),
]
