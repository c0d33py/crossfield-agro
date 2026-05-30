from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.blog.sitemaps import sitemaps as blog_sitemaps
from apps.careers.sitemaps import sitemaps as career_sitemaps
from apps.core.sitemaps import sitemaps as core_sitemaps
from apps.industries.sitemaps import sitemaps as industry_sitemaps
from apps.media_center.sitemaps import sitemaps as media_sitemaps
from apps.products.sitemaps import sitemaps as product_sitemaps
from apps.seo.views import robots_txt
from apps.services.sitemaps import sitemaps as service_sitemaps

sitemaps = {
    **core_sitemaps,
    **product_sitemaps,
    **industry_sitemaps,
    **service_sitemaps,
    **blog_sitemaps,
    **career_sitemaps,
    **media_sitemaps,
}

admin_url = getattr(settings, "ADMIN_URL", "admin/")

urlpatterns = [
    path(admin_url, admin.site.urls),
    # Catalog
    path("products/", include("apps.products.urls", namespace="products")),
    path("industries/", include("apps.industries.urls", namespace="industries")),
    path("services/", include("apps.services.urls", namespace="services")),
    # Commerce
    path("cart/", include("apps.cart.urls", namespace="cart")),
    path("checkout/", include("apps.checkout.urls", namespace="checkout")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("payments/", include("apps.payments.urls", namespace="payments")),
    path("invoices/", include("apps.invoices.urls", namespace="invoices")),
    # Engagement
    path("blog/", include("apps.blog.urls", namespace="blog")),
    path("contact/", include("apps.contact.urls", namespace="contact")),
    path("careers/", include("apps.careers.urls", namespace="careers")),
    path("media-center/", include("apps.media_center.urls", namespace="media_center")),
    # System
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    # SEO — sitemap + robots.txt
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots-txt"),
    # Core corporate pages — MUST be last because it catches /<slug>/
    path("", include("apps.core.urls", namespace="core")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
