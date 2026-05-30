from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

import pytest

from apps.blog.models import Author, Post, PostStatus, Tag
from apps.blog.selectors import get_published_posts, get_related_posts

pytestmark = pytest.mark.django_db


def _author(**kw) -> Author:
    kw.setdefault("name", "A. Editor")
    kw.setdefault("slug", "a-editor")
    return Author.objects.create(**kw)


def _tag(name="Cereals") -> Tag:
    return Tag.objects.create(name=name, slug=name.lower())


def _post(author=None, status=PostStatus.PUBLISHED, **kw) -> Post:
    if author is None:
        author = _author()
    kw.setdefault("title", "How to apply urea")
    kw.setdefault("slug", "how-to-apply-urea")
    kw.setdefault("excerpt", "Field-proven application timing.")
    kw.setdefault("body", "Long body text here.")
    if status == PostStatus.PUBLISHED:
        kw.setdefault("published_at", timezone.now())
    return Post.objects.create(author=author, status=status, **kw)


class TestSelectors:
    def test_only_published_returned(self):
        author = _author()
        _post(author=author, slug="published", title="P")
        _post(author=author, slug="draft", title="D", status=PostStatus.DRAFT)
        slugs = list(get_published_posts().values_list("slug", flat=True))
        assert slugs == ["published"]

    def test_future_publish_date_excluded(self):
        _post(slug="future", published_at=timezone.now() + timezone.timedelta(days=1))
        assert get_published_posts().count() == 0

    def test_related_posts_share_tag(self):
        a = _author()
        t = _tag()
        p1 = _post(author=a, slug="p1")
        p2 = _post(author=a, slug="p2", title="P2")
        p1.tags.add(t)
        p2.tags.add(t)
        related = list(get_related_posts(p1))
        assert p2 in related
        assert p1 not in related


class TestPostListView:
    def test_renders_published(self, client):
        _post(slug="hello", title="Hello world")
        response = client.get(reverse("blog:list"))
        assert response.status_code == 200
        assert b"Hello world" in response.content
        assert b'"@type": "Blog"' in response.content

    def test_empty_state(self, client):
        response = client.get(reverse("blog:list"))
        assert response.status_code == 200
        assert b"No posts yet" in response.content


class TestPostDetailView:
    def test_404_for_draft(self, client):
        _post(slug="draft", status=PostStatus.DRAFT)
        response = client.get(reverse("blog:post-detail", kwargs={"slug": "draft"}))
        assert response.status_code == 404

    def test_renders_with_jsonld(self, client):
        _post(slug="visible", title="Visible Post")
        response = client.get(reverse("blog:post-detail", kwargs={"slug": "visible"}))
        assert response.status_code == 200
        assert b"Visible Post" in response.content
        assert b'"@type": "Article"' in response.content


class TestTagAndAuthor:
    def test_tag_detail_lists_posts(self, client):
        t = _tag(name="Wheat")
        p = _post(slug="wheat-post", title="On wheat")
        p.tags.add(t)
        response = client.get(reverse("blog:tag-detail", kwargs={"slug": "wheat"}))
        assert response.status_code == 200
        assert b"On wheat" in response.content

    def test_author_detail_lists_posts(self, client):
        a = _author(name="J. Smith", slug="j-smith")
        _post(author=a, slug="by-js", title="By JS")
        response = client.get(reverse("blog:author-detail", kwargs={"slug": "j-smith"}))
        assert response.status_code == 200
        assert b"By JS" in response.content
        assert b'"@type": "Person"' in response.content
