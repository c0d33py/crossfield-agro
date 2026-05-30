# SEO Rules

SEO is a first-class concern for Crosfield Agro Pakistan — agro-industrial buyers
discover suppliers through search. The `seo` app owns all metadata centrally.

## Mandatory Per-Page Metadata

Every public-facing URL must provide:

- `<title>` — 50–60 chars, brand-suffixed (`{page} | Crosfield Agro Pakistan`)
- `<meta name="description">` — 140–160 chars, action-oriented
- `<link rel="canonical">` — absolute URL, no query params unless meaningful
- `<meta property="og:*">` — title, description, image (1200×630), url, type
- `<meta name="twitter:card">` — `summary_large_image`
- `hreflang` if multilingual variants exist

## Structured Data (Schema.org)

Use JSON-LD, not microdata. Required per page type:

| Page type     | Schema                                            |
|---------------|---------------------------------------------------|
| Homepage      | `Organization`, `WebSite` (with `SearchAction`)   |
| Product       | `Product` + `Offer` + `AggregateRating` (if any)  |
| Industry/Cat  | `CollectionPage` + `BreadcrumbList`               |
| Blog post     | `Article` + `BreadcrumbList` + `Person` (author)  |
| Contact       | `Organization` + `ContactPoint`                   |
| About         | `Organization` + `AboutPage`                      |

All schema rendered server-side from the `seo` app's helpers.

## Sitemaps

- XML sitemap auto-generated via Django `sitemaps` framework
- Split sitemaps: products, industries, blog, static-pages
- `sitemap-index.xml` aggregates them
- Regenerate on model save via Celery task; cache 1 hour
- Submit to Google Search Console + Bing Webmaster

## URLs

- Lowercase, kebab-case (`/products/nitrogen-fertilizer/`)
- Trailing slash enforced (Django default)
- No `?id=` style URLs for indexable pages — slug-based only
- Canonical URL is the source of truth; pagination, filters use `rel=next/prev` or noindex

## Performance (Core Web Vitals)

| Metric | Target |
|--------|--------|
| LCP    | < 2.5s |
| INP    | < 200ms |
| CLS    | < 0.1  |

- Above-fold images: `loading="eager"`, `fetchpriority="high"`, preloaded
- Below-fold images: `loading="lazy"`
- WebP/AVIF served via `<picture>`
- CSS critical-path inlined; rest deferred

## Content Rules

- One `<h1>` per page
- Heading hierarchy must be linear (no `<h2>` → `<h4>` skips)
- Internal linking: every product links to its industry and related products
- Image `alt` attributes: descriptive, not keyword-stuffed
- No cloaking, no doorway pages, no auto-generated thin content

## Forbidden

- ❌ `noindex` on indexable pages without intent
- ❌ Duplicate titles/descriptions across pages
- ❌ Client-side-only rendered critical content (SSR or pre-render required)
- ❌ Blocking `robots.txt` from JS/CSS Google needs to render
