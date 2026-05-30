"""
SEO middleware: serves admin-managed 301/302 redirects before the URLconf
gets to handle the request. Increments hit counter via Celery (best-effort).
"""

from __future__ import annotations

from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect

from apps.seo.selectors import get_active_redirect


class SeoRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only redirect safe methods so we don't accidentally swallow POSTs
        if request.method in {"GET", "HEAD"}:
            redirect = get_active_redirect(request.path)
            if redirect is not None:
                # Fire-and-forget hit counter (don't block on it)
                try:
                    from apps.seo.tasks import increment_redirect_hits

                    increment_redirect_hits.delay(redirect.pk)
                except Exception:
                    pass
                if redirect.status_code == 301:
                    return HttpResponsePermanentRedirect(redirect.target_url)
                return HttpResponseRedirect(redirect.target_url)
        return self.get_response(request)
