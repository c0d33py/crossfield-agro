from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from apps.contact.models import ContactMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContactMessageInput:
    name: str
    email: str
    phone: str
    company: str
    enquiry_type: str
    message: str
    submitter_ip: str | None = None
    user_agent: str = ""


@transaction.atomic
def submit_contact_message(*, payload: ContactMessageInput) -> ContactMessage:
    message = ContactMessage.objects.create(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        enquiry_type=payload.enquiry_type,
        message=payload.message,
        submitter_ip=payload.submitter_ip,
        user_agent=payload.user_agent[:300],
    )
    logger.info(
        "Contact message %s from %s <%s> [%s]",
        message.pk,
        message.name,
        message.email,
        message.enquiry_type,
    )
    from apps.contact.tasks import send_contact_notification

    send_contact_notification.delay(message.pk)
    return message
