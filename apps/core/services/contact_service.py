from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContactEnquiry:
    name: str
    email: str
    phone: str
    company: str
    enquiry_type: str
    message: str


@transaction.atomic
def submit_contact_enquiry(*, enquiry: ContactEnquiry) -> ContactEnquiry:
    """
    Persist (TODO: once a ContactMessage model exists in the `contact` app)
    and dispatch a notification email via Celery.

    For now this only logs and queues the notification — the `contact` app
    owns persistence.
    """
    logger.info(
        "Contact enquiry %s from %s <%s>",
        enquiry.enquiry_type,
        enquiry.name,
        enquiry.email,
    )
    from apps.core.tasks import send_contact_notification

    send_contact_notification.delay(
        name=enquiry.name,
        email=enquiry.email,
        phone=enquiry.phone,
        company=enquiry.company,
        enquiry_type=enquiry.enquiry_type,
        message=enquiry.message,
    )
    return enquiry
