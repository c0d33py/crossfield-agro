from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.send_contact_notification")
def send_contact_notification(
    *,
    name: str,
    email: str,
    phone: str,
    company: str,
    enquiry_type: str,
    message: str,
) -> None:
    """Send a contact-enquiry notification email. Wire to real mail config later."""
    logger.info("TODO email: contact enquiry from %s <%s> [%s]", name, email, enquiry_type)
