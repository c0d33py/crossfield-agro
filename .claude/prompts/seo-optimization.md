# Prompt: SEO Optimization

Use this when adding SEO to a new page type or auditing existing pages.

---

## Prompt Template

```text
Optimize SEO for: {page_type}  (e.g. product detail, industry landing, blog post)

Deliverables:
1. Metadata
   - <title>: 50–60 chars, brand-suffixed
   - <meta name="description">: 140–160 chars, action-oriented
   - <link rel="canonical">: absolute URL
   - Open Graph: og:title, og:description, og:image (1200×630), og:url, og:type
   - Twitter Card: summary_large_image
   - hreflang (if multilingual)

2. Structured Data (JSON-LD, server-rendered)
   - Pick correct schema for the page type:
     * Product → Product + Offer (+ AggregateRating if reviews)
     * Industry/Category → CollectionPage + BreadcrumbList
     * Blog post → Article + BreadcrumbList + Person (author)
     * Homepage → Organization + WebSite (with SearchAction)
     * Contact → Organization + ContactPoint
   - Validate via Google Rich Results Test before shipping

3. URL
   - Slug-based, kebab-case, lowercase
   - Trailing slash (Django default)
   - No query params on canonical
   - Old URLs redirected 301 to new (if migrating)

4. Content structure
   - One <h1> per page; linear heading hierarchy (no skips)
   - First 100 words contain primary keyword naturally
   - Internal links: this page links to at least 2 related pages
   - Inbound: at least 1 other page in the site links here

5. Images
   - Descriptive alt text (no keyword stuffing)
   - WebP/AVIF via <picture>
   - Width/height attributes set (no layout shift)
   - Above-fold: loading="eager" fetchpriority="high"
   - Below-fold: loading="lazy"

6. Performance (Core Web Vitals)
   - LCP < 2.5s — critical CSS inlined, hero image preloaded
   - INP < 200ms — defer non-critical JS
   - CLS < 0.1 — reserve dimensions for all media

7. Sitemap
   - Add to django.contrib.sitemaps registration
   - Trigger sitemap regeneration on save via signal → Celery

8. Indexing controls
   - Verify robots.txt does not block
   - Verify no accidental <meta name="robots" content="noindex">
   - Submit URL to Google Search Console after deploy

Implementation:
- All metadata served from the seo app (centralized)
- Template fragment {% include "seo/_meta.html" with object=obj %}
- JSON-LD helper: seo.helpers.json_ld_for(obj)
```

---

## SEO Checklist (per page)

- [ ] Title unique site-wide, 50–60 chars
- [ ] Description unique, 140–160 chars
- [ ] Canonical URL set and correct
- [ ] OG tags present and accurate
- [ ] JSON-LD validates in Rich Results Test
- [ ] One H1; linear heading hierarchy
- [ ] All images have alt text + dimensions
- [ ] Page registered in sitemap
- [ ] LCP element preloaded
- [ ] No console errors (CLS triggers, JS errors hurt CWV)
- [ ] Mobile rendering verified
