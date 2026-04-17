from .models import Notification, Project

def notification_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    else:
        count = 0

    return {
        "unread_notification_count": count
    }


def pending_approval_count(request):
    if request.user.is_authenticated:

        # 部門管理者
        if request.user.role == "manager":
            count = Project.objects.filter(
                department=request.user.department,
                status=Project.Status.PENDING_MANAGER
            ).count()

        # 本部管理者
        elif request.user.role == "hq":
            count = Project.objects.filter(
                status=Project.Status.PENDING_HQ
            ).count()

        else:
            count = 0
    else:
        count = 0

    return {
        "pending_approval_count": count
    }