from __future__ import annotations

from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.views.generic import View

from apps.products.forms import ProductSearchForm
from apps.products.selectors import (
    SORT_CHOICES,
    get_active_categories,
    get_category_by_slug,
    get_product_by_slug,
    get_products_for_category,
    get_published_products,
    get_related_products,
    search_products,
)


class _RenderMixin:
    template_name: str = ""

    def render(self, request: HttpRequest, context: dict) -> HttpResponse:
        from django.shortcuts import render

        return render(request, self.template_name, context)


class ProductListView(_RenderMixin, View):
    template_name = "products/product_list.html"
    paginate_by = 12

    def get(self, request: HttpRequest) -> HttpResponse:
        sort = request.GET.get("sort", "newest")
        if sort not in SORT_CHOICES:
            sort = "newest"

        category_slug = request.GET.get("category") or ""
        active_category = get_category_by_slug(category_slug) if category_slug else None

        qs = get_published_products(
            category_id=active_category.id if active_category else None,
            sort=sort,
        )
        total = qs.count()
        page = Paginator(qs, self.paginate_by).get_page(request.GET.get("page"))

        return self.render(
            request,
            {
                "page_obj": page,
                "products": page.object_list,
                "total": total,
                "categories": get_active_categories(),
                "active_category": active_category,
                "current_sort": sort,
                "sort_options": [
                    ("newest", "Newest first"),
                    ("name", "Name (A → Z)"),
                    ("price-asc", "Price (low → high)"),
                    ("price-desc", "Price (high → low)"),
                ],
                "search_form": ProductSearchForm(),
            },
        )


class CategoryDetailView(_RenderMixin, View):
    template_name = "products/category_detail.html"
    paginate_by = 12

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        category = get_category_by_slug(slug)
        if category is None:
            raise Http404("Category not found")

        sort = request.GET.get("sort", "newest")
        if sort not in SORT_CHOICES:
            sort = "newest"

        # get_products_for_category honours the descendant tree but doesn't
        # take a sort arg; apply the ordering ourselves to match list view.
        qs = get_products_for_category(category).order_by(SORT_CHOICES[sort], "-id")
        total = qs.count()
        page = Paginator(qs, self.paginate_by).get_page(request.GET.get("page"))

        # Build the parent crumbs lazily (most categories are at depth 1-2).
        crumbs: list = []
        node = category.parent
        while node is not None:
            crumbs.append(node)
            node = node.parent
        crumbs.reverse()

        return self.render(
            request,
            {
                "category": category,
                "page_obj": page,
                "products": page.object_list,
                "total": total,
                "categories": get_active_categories(),
                "active_category": category,
                "subcategories": list(
                    category.children.filter(is_active=True).order_by("position", "name")
                ),
                "parent_crumbs": crumbs,
                "current_sort": sort,
                "sort_options": [
                    ("newest", "Newest first"),
                    ("name", "Name (A → Z)"),
                    ("price-asc", "Price (low → high)"),
                    ("price-desc", "Price (high → low)"),
                ],
            },
        )


class ProductDetailView(_RenderMixin, View):
    template_name = "products/product_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        product = get_product_by_slug(slug)
        if product is None:
            raise Http404("Product not found")
        related = get_related_products(product)
        return self.render(request, {"product": product, "related": related})


class ProductSearchView(_RenderMixin, View):
    template_name = "products/product_search.html"
    paginate_by = 20

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ProductSearchForm(request.GET or None)
        query = form.cleaned_data["q"] if form.is_valid() else ""
        qs = search_products(query) if query else get_published_products().none()
        page = Paginator(qs, self.paginate_by).get_page(request.GET.get("page"))
        return self.render(
            request,
            {"form": form, "query": query, "page_obj": page, "products": page.object_list},
        )
