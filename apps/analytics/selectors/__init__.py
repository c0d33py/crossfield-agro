from __future__ import annotations

from datetime import date, timedelta

from django.db.models import QuerySet, Sum

from apps.analytics.models import DailyRollup


def get_top_paths(days: int = 7, limit: int = 20) -> QuerySet:
    cutoff = date.today() - timedelta(days=days)
    return (
        DailyRollup.objects.filter(date__gte=cutoff)
        .values("path")
        .annotate(total=Sum("views"))
        .order_by("-total")[:limit]
    )


def get_rollup_for_date(d: date) -> QuerySet[DailyRollup]:
    return DailyRollup.objects.filter(date=d).order_by("-views")
