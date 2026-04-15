from .models import Notification, CustomUser


def create_notification(recipient, message, project=None):
    Notification.objects.create(
        recipient=recipient,
        project=project,
        message=message,
    )