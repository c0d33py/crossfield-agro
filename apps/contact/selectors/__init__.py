from django.db.models import QuerySet

from apps.contact.models import ContactMessage, ContactStatus


def get_new_messages() -> QuerySet[ContactMessage]:
    return ContactMessage.objects.filter(status=ContactStatus.NEW).order_by("-created_at")


def get_messages_by_type(enquiry_type: str) -> QuerySet[ContactMessage]:
    return ContactMessage.objects.filter(enquiry_type=enquiry_type).order_by("-created_at")
