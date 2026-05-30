from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from apps.careers.models import JobApplication, JobPosting

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApplicationInput:
    posting: JobPosting
    full_name: str
    email: str
    phone: str
    location: str
    cv: object  # InMemoryUploadedFile or similar
    cover_letter: str
    linkedin_url: str
    submitter_ip: str | None = None
    user_agent: str = ""


@transaction.atomic
def submit_application(*, payload: ApplicationInput) -> JobApplication:
    if not payload.posting.is_open:
        from django.core.exceptions import ValidationError

        raise ValidationError("This posting is not accepting applications.")

    application = JobApplication.objects.create(
        posting=payload.posting,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        location=payload.location,
        cv=payload.cv,
        cover_letter=payload.cover_letter,
        linkedin_url=payload.linkedin_url,
        submitter_ip=payload.submitter_ip,
        user_agent=payload.user_agent[:300],
    )
    logger.info(
        "Application %s from %s for posting %s",
        application.pk,
        application.full_name,
        payload.posting.slug,
    )
    from apps.careers.tasks import send_application_notification

    send_application_notification.delay(application.pk)
    return application
