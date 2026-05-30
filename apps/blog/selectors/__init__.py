from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.blog.models import Author, Post, PostStatus, Tag


def _base_published_qs() -> QuerySet[Post]:
    return (
        Post.objects.filter(
            status=PostStatus.PUBLISHED,
            published_at__lte=timezone.now(),
        )
        .select_related("author")
        .prefetch_related("tags")
    )


def get_published_posts() -> QuerySet[Post]:
    return _base_published_qs()


def get_post_by_slug(slug: str) -> Post | None:
    return _base_published_qs().filter(slug=slug).first()


def get_posts_for_tag(tag: Tag) -> QuerySet[Post]:
    return _base_published_qs().filter(tags=tag)


def get_posts_for_author(author: Author) -> QuerySet[Post]:
    return _base_published_qs().filter(author=author)


def get_active_authors() -> QuerySet[Author]:
    return Author.objects.filter(is_active=True).order_by("name")


def get_author_by_slug(slug: str) -> Author | None:
    return Author.objects.filter(slug=slug, is_active=True).first()


def get_all_tags() -> QuerySet[Tag]:
    return Tag.objects.all().order_by("name")


def get_tag_by_slug(slug: str) -> Tag | None:
    return Tag.objects.filter(slug=slug).first()


def get_related_posts(post: Post, limit: int = 3) -> QuerySet[Post]:
    """Posts sharing at least one tag, excluding the current post."""
    tag_ids = list(post.tags.values_list("id", flat=True))
    if not tag_ids:
        return _base_published_qs().exclude(pk=post.pk)[:limit]
    return _base_published_qs().filter(tags__in=tag_ids).exclude(pk=post.pk).distinct()[:limit]
