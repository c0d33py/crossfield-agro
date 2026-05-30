from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="careers.send_application_notification")
def send_application_notification(application_id: int) -> None:
    from apps.careers.models import JobApplication

    app = JobApplication.objects.select_related("posting").filter(pk=application_id).first()
    if not app:
        logger.warning("JobApplication %s missing", application_id)
        return
    logger.info(
        "TODO email: new application #%s from %s <%s> for %s",
        app.pk,
        app.full_name,
        app.email,
        app.posting.title,
    )
