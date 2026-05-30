from __future__ import annotations

from django.db.models import QuerySet

from apps.products.models import Category


def get_active_categories() -> QuerySet[Category]:
    return Category.objects.filter(is_active=True).order_by("position", "name")


def get_category_by_slug(slug: str) -> Category | None:
    return Category.objects.filter(slug=slug, is_active=True).select_related("parent").first()


def get_category_tree() -> list[dict]:
    """
    Return a serialized tree of active categories suitable for nav rendering.
    Two queries total (root + children), not N+1.
    """
    all_active = list(get_active_categories().values("id", "name", "slug", "parent_id"))
    by_parent: dict[int | None, list[dict]] = {}
    for c in all_active:
        by_parent.setdefault(c["parent_id"], []).append(
            {"id": c["id"], "name": c["name"], "slug": c["slug"], "children": []}
        )

    def attach(node: dict) -> dict:
        node["children"] = [attach(child) for child in by_parent.get(node["id"], [])]
        return node

    return [attach(root) for root in by_parent.get(None, [])]
