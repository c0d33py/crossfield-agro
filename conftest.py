"""Project-wide pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _eager_celery(settings):
    """Run Celery tasks synchronously in tests."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
