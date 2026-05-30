from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="contact.send_contact_notification")
def send_contact_notification(message_id: int) -> None:
    """Notify staff inbox of a new contact message. Wire to real mail when SMTP is configured."""
    from apps.contact.models import ContactMessage

    msg = ContactMessage.objects.filter(pk=message_id).first()
    if not msg:
        logger.warning("ContactMessage %s not found", message_id)
        return
    logger.info(
        "TODO email: new contact message #%s from %s <%s> [%s]",
        msg.pk,
        msg.name,
        msg.email,
        msg.enquiry_type,
    )
