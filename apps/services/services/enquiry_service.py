from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from apps.services.models import ServiceEnquiry, ServiceOffering

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceEnquiryInput:
    name: str
    email: str
    phone: str
    company: str
    message: str
    offering: ServiceOffering | None = None


@transaction.atomic
def submit_service_enquiry(*, enquiry: ServiceEnquiryInput) -> ServiceEnquiry:
    record = ServiceEnquiry.objects.create(
        offering=enquiry.offering,
        name=enquiry.name,
        email=enquiry.email,
        phone=enquiry.phone,
        company=enquiry.company,
        message=enquiry.message,
    )
    logger.info(
        "Service enquiry %s from %s <%s> for offering=%s",
        record.pk,
        enquiry.name,
        enquiry.email,
        enquiry.offering.slug if enquiry.offering else "general",
    )
    from apps.services.tasks import send_service_enquiry_notification

    send_service_enquiry_notification.delay(record.pk)
    return record
