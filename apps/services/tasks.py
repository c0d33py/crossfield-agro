from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="services.send_service_enquiry_notification")
def send_service_enquiry_notification(enquiry_id: int) -> None:
    from apps.services.models import ServiceEnquiry

    enquiry = ServiceEnquiry.objects.filter(pk=enquiry_id).first()
    if not enquiry:
        logger.warning("ServiceEnquiry %s missing — skipping notification", enquiry_id)
        return
    offering = enquiry.offering.name if enquiry.offering else "general services"
    logger.info(
        "TODO email: service enquiry %s from %s <%s> for %s",
        enquiry.pk,
        enquiry.name,
        enquiry.email,
        offering,
    )
