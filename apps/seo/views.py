from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from apps.seo.selectors import get_active_robots_rules


def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Render /robots.txt from the RobotsRule table. If no rules exist, fall back
    to a safe default that blocks admin/staff URLs and advertises the sitemap.
    """
    lines: list[str] = []
    rules = list(get_active_robots_rules())
    if rules:
        for r in rules:
            lines.append(r.render_line())
    else:
        lines = [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /staff-portal/",
            "Disallow: /api/",
            "Disallow: /cart/",
            "Disallow: /checkout/",
            "Disallow: /orders/",
            "Disallow: /payments/",
        ]

    # Always append the sitemap line(s).
    host = request.get_host()
    scheme = "https" if request.is_secure() else "http"
    lines.append(f"\nSitemap: {scheme}://{host}/sitemap.xml")

    return HttpResponse("\n".join(lines), content_type="text/plain")
