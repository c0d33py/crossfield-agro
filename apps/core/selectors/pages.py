"""
Static registry of corporate pages. Single source of truth for slug → template
mapping, page titles, meta descriptions, and footer/nav grouping.

Mirrors the `core` module list in .claude/project.json.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageMeta:
    slug: str  # URL slug (kebab-case)
    title: str  # H1 / <title>
    description: str  # meta description (140-160 chars)
    section: str  # footer/nav grouping
    template: str  # template path relative to templates root


def _p(slug, title, description, section, template=None) -> PageMeta:
    return PageMeta(
        slug=slug,
        title=title,
        description=description,
        section=section,
        template=template or f"core/pages/{slug.replace('-', '_')}.html",
    )


# Order here is the order they appear in site map / footer.
PAGE_REGISTRY: dict[str, PageMeta] = {
    p.slug: p
    for p in [
        # ---- COMPANY ----
        _p(
            "about-us",
            "About Crosfield Agro Pakistan",
            "Crosfield Agro Pakistan delivers fertilizers, agrochemicals, and specialty inputs to growers and industrial processors across South Asia.",
            "company",
        ),
        _p(
            "company-overview",
            "Company Overview",
            "An overview of Crosfield Agro Pakistan — our scale, footprint, manufacturing capability, and the markets we serve.",
            "company",
        ),
        _p(
            "mission-vision",
            "Mission & Vision",
            "Crosfield Agro Pakistan's mission to advance Pakistani agriculture through science-led inputs, and our long-term vision for the sector.",
            "company",
        ),
        _p(
            "leadership-team",
            "Leadership Team",
            "Meet the leadership team driving Crosfield Agro Pakistan — operations, R&D, commercial, and finance.",
            "company",
        ),
        _p(
            "message-from-ceo",
            "Message from the CEO",
            "A direct message from our Chief Executive Officer on Crosfield's commitment to growers, partners, and Pakistani agriculture.",
            "company",
        ),
        _p(
            "our-history",
            "Our History",
            "From foundation to the present day — milestones that have shaped Crosfield Agro Pakistan into a trusted agro-industrial supplier.",
            "company",
        ),
        # ---- CAPABILITIES ----
        _p(
            "certifications",
            "Certifications",
            "ISO 9001, ISO 14001, ISO 45001, and product-level certifications that govern Crosfield Agro Pakistan's manufacturing and quality systems.",
            "capabilities",
        ),
        _p(
            "quality-standards",
            "Quality Standards",
            "Our quality framework — inbound material testing, in-process controls, batch traceability, and final-release testing for every shipment.",
            "capabilities",
        ),
        _p(
            "sustainability",
            "Sustainability",
            "How Crosfield Agro Pakistan reduces resource intensity in manufacturing, supports soil health on-farm, and reports against ESG benchmarks.",
            "capabilities",
        ),
        _p(
            "research-development",
            "Research & Development",
            "Crosfield's R&D programme — formulation chemistry, agronomy field trials, and product development for South Asian cropping systems.",
            "capabilities",
        ),
        _p(
            "infrastructure",
            "Infrastructure",
            "Our manufacturing, warehousing, laboratory, and distribution infrastructure across Pakistan.",
            "capabilities",
        ),
        _p(
            "manufacturing-process",
            "Manufacturing Process",
            "A step-by-step look at how Crosfield Agro Pakistan manufactures fertilizers, agrochemicals, and specialty inputs at industrial scale.",
            "capabilities",
        ),
        _p(
            "global-presence",
            "Global Presence",
            "Crosfield Agro Pakistan's plants, distribution, export, and partnership footprint across South Asia and beyond.",
            "capabilities",
        ),
        # ---- CATALOG / SERVICE ----
        # NOTE: /industries/ and /services/ are now served by the dedicated apps
        # (apps.industries, apps.services) — they own those URL prefixes. Do not
        # re-add them here or the slug catch-all will shadow the real views.
        # ---- ENGAGEMENT ----
        _p(
            "faq",
            "Frequently Asked Questions",
            "Answers to common questions on ordering, technical specifications, application guidance, and after-sales support.",
            "engagement",
        ),
        _p(
            "testimonials",
            "Testimonials",
            "What growers, agronomists, and industrial partners say about working with Crosfield Agro Pakistan.",
            "engagement",
        ),
        _p(
            "partners",
            "Partners",
            "Crosfield Agro Pakistan's technology, distribution, research, and supply-chain partners.",
            "engagement",
        ),
        _p(
            "clients",
            "Clients",
            "A selection of growers, cooperatives, distributors, and industrial buyers who rely on Crosfield Agro Pakistan inputs.",
            "engagement",
        ),
        _p(
            "media-highlights",
            "Media Highlights",
            "Press, interviews, and external coverage of Crosfield Agro Pakistan, our products, and our people.",
            "engagement",
        ),
        _p(
            "awards-recognition",
            "Awards & Recognition",
            "Industry awards and recognition received by Crosfield Agro Pakistan for product quality, sustainability, and operational excellence.",
            "engagement",
        ),
        # NOTE: /careers/ and /contact-us/ moved to their dedicated apps
        # (apps.careers, apps.contact). They own those URL prefixes — do not
        # re-add them here or the slug catch-all will shadow the real views.
        # ---- LEGAL ----
        _p(
            "privacy-policy",
            "Privacy Policy",
            "How Crosfield Agro Pakistan collects, uses, retains, and protects your personal information.",
            "legal",
        ),
        _p(
            "terms-conditions",
            "Terms & Conditions",
            "The terms governing use of this website and any purchases made from Crosfield Agro Pakistan.",
            "legal",
        ),
        _p(
            "cookie-policy",
            "Cookie Policy",
            "What cookies and similar technologies this website uses, and how to manage your preferences.",
            "legal",
        ),
        _p(
            "disclaimer",
            "Disclaimer",
            "Important disclaimers regarding the content, technical guidance, and product information published on this website.",
            "legal",
        ),
        _p(
            "site-map",
            "Site Map",
            "An index of every public page on the Crosfield Agro Pakistan website.",
            "legal",
        ),
    ]
}


def get_page_meta(slug: str) -> PageMeta | None:
    return PAGE_REGISTRY.get(slug)


def get_all_pages() -> list[PageMeta]:
    return list(PAGE_REGISTRY.values())


def get_pages_by_section() -> dict[str, list[PageMeta]]:
    grouped: dict[str, list[PageMeta]] = {}
    for page in PAGE_REGISTRY.values():
        grouped.setdefault(page.section, []).append(page)
    return grouped
