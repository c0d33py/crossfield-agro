"""
Seed sample catalog data for development:
  - 5 product categories
  - 10 industries
  - 20 published products (each linked to a category + 1-3 industries)
  - 10 service offerings

Safe to run multiple times — uses get_or_create on slug.

Usage:
    python manage.py seed_catalog
    python manage.py seed_catalog --flush   # delete existing seeded rows first
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.industries.models import Industry
from apps.products.models import Category, Product, ProductStatus, ProductVariant
from apps.services.models import ServiceCategory, ServiceOffering

CATEGORIES = [
    {
        "slug": "nitrogen-fertilizers",
        "name": "Nitrogen Fertilizers",
        "description": "Urea, ammonium nitrate, and ammonium sulphate formulations for cereal and forage crops.",
    },
    {
        "slug": "phosphate-fertilizers",
        "name": "Phosphate Fertilizers",
        "description": "DAP, SSP, TSP and NPK blends engineered for South Asian soils.",
    },
    {
        "slug": "specialty-nutrients",
        "name": "Specialty Nutrients",
        "description": "Water-soluble fertilizers, foliar feeds, and micronutrient blends for high-value horticulture.",
    },
    {
        "slug": "crop-protection",
        "name": "Crop Protection",
        "description": "Herbicides, insecticides, and fungicides formulated and tested under our R&D programme.",
    },
    {
        "slug": "industrial-inputs",
        "name": "Industrial Inputs",
        "description": "Specialty chemicals and contract-formulated inputs for industrial processors.",
    },
]

INDUSTRIES = [
    {
        "slug": "cereals",
        "name": "Cereals",
        "summary": "Wheat, rice, and maize — Pakistan's calorie base. Inputs that lift yields without raising input cost per tonne.",
    },
    {
        "slug": "cotton",
        "name": "Cotton",
        "summary": "Inputs tuned for Pakistan's cotton belt — fertility, pest pressure, and fibre-quality drivers.",
    },
    {
        "slug": "sugarcane",
        "name": "Sugarcane",
        "summary": "Nutrient and crop-protection programmes designed around sugarcane's 12-18 month cycle.",
    },
    {
        "slug": "horticulture",
        "name": "Horticulture",
        "summary": "Fruits, vegetables, and ornamentals — soluble nutrients and quality-grade crop protection.",
    },
    {
        "slug": "rice-paddy",
        "name": "Rice & Paddy",
        "summary": "Basmati and IRRI rice systems — flooded-soil nutrient dynamics and pest management.",
    },
    {
        "slug": "livestock-feed",
        "name": "Livestock Feed",
        "summary": "Specialty inputs for livestock-feed manufacturers — premixes, additives, and process aids.",
    },
    {
        "slug": "oilseeds",
        "name": "Oilseeds",
        "summary": "Sunflower, canola, and mustard — micronutrient management for oil yield and quality.",
    },
    {
        "slug": "pulses-legumes",
        "name": "Pulses & Legumes",
        "summary": "Chickpea, lentil, mung bean — phosphorus and micronutrient strategies for nodulation and yield.",
    },
    {
        "slug": "tobacco",
        "name": "Tobacco",
        "summary": "Specialty fertilizer programmes for KPK's tobacco-growing districts.",
    },
    {
        "slug": "industrial-processing",
        "name": "Industrial Processing",
        "summary": "Specialty chemicals and contract-manufactured formulations for industrial customers.",
    },
]

# 20 products — name, sku, category_slug, price (PKR), short, stock, industries (slugs)
PRODUCTS = [
    # Nitrogen
    {
        "slug": "crosfield-urea-46n",
        "name": "Crosfield Urea 46% N",
        "sku": "CF-N-UREA-46",
        "category": "nitrogen-fertilizers",
        "price": "3450.00",
        "stock": 5000,
        "short": "Granular urea, 46% N, anti-caking treated — 50 kg bag.",
        "industries": ["cereals", "rice-paddy", "sugarcane", "cotton"],
    },
    {
        "slug": "crosfield-can-26n",
        "name": "Crosfield CAN 26% N",
        "sku": "CF-N-CAN-26",
        "category": "nitrogen-fertilizers",
        "price": "2980.00",
        "stock": 3200,
        "short": "Calcium ammonium nitrate, 26% N — gentle on soil pH, ideal for horticulture.",
        "industries": ["horticulture", "oilseeds"],
    },
    {
        "slug": "crosfield-amsul-21n",
        "name": "Crosfield Ammonium Sulphate 21% N",
        "sku": "CF-N-AMSUL-21",
        "category": "nitrogen-fertilizers",
        "price": "2650.00",
        "stock": 1800,
        "short": "21% N + 24% S — supplies sulphur alongside nitrogen for oilseed crops.",
        "industries": ["oilseeds", "tobacco", "horticulture"],
    },
    # Phosphate
    {
        "slug": "crosfield-dap-46p",
        "name": "Crosfield DAP 46% P₂O₅",
        "sku": "CF-P-DAP-46",
        "category": "phosphate-fertilizers",
        "price": "9200.00",
        "stock": 2400,
        "short": "Diammonium phosphate, 18-46-0 — basal application for cereals and cotton.",
        "industries": ["cereals", "cotton", "rice-paddy"],
    },
    {
        "slug": "crosfield-ssp-18p",
        "name": "Crosfield SSP 18% P₂O₅",
        "sku": "CF-P-SSP-18",
        "category": "phosphate-fertilizers",
        "price": "1850.00",
        "stock": 4100,
        "short": "Single superphosphate with calcium and sulphur — pulses and legumes.",
        "industries": ["pulses-legumes", "oilseeds"],
    },
    {
        "slug": "crosfield-tsp-46p",
        "name": "Crosfield TSP 46% P₂O₅",
        "sku": "CF-P-TSP-46",
        "category": "phosphate-fertilizers",
        "price": "7400.00",
        "stock": 1200,
        "short": "Triple superphosphate — concentrated phosphorus for high-input systems.",
        "industries": ["sugarcane", "horticulture"],
    },
    {
        "slug": "crosfield-npk-15-15-15",
        "name": "Crosfield NPK 15-15-15",
        "sku": "CF-NPK-15-15-15",
        "category": "phosphate-fertilizers",
        "price": "5400.00",
        "stock": 2700,
        "short": "Balanced NPK blend for general-purpose application across cereals and vegetables.",
        "industries": ["cereals", "horticulture", "cotton"],
    },
    {
        "slug": "crosfield-npk-20-10-10",
        "name": "Crosfield NPK 20-10-10 + S",
        "sku": "CF-NPK-20-10-10",
        "category": "phosphate-fertilizers",
        "price": "5750.00",
        "stock": 2100,
        "short": "Nitrogen-rich blend with sulphur — wheat top-dressing and sugarcane ratoon.",
        "industries": ["cereals", "sugarcane"],
    },
    # Specialty
    {
        "slug": "crosfield-zinc-sulphate-33",
        "name": "Crosfield Zinc Sulphate 33%",
        "sku": "CF-S-ZNS-33",
        "category": "specialty-nutrients",
        "price": "950.00",
        "stock": 800,
        "short": "33% Zn — corrects zinc deficiency in rice, wheat, and cotton.",
        "industries": ["rice-paddy", "cereals", "cotton"],
    },
    {
        "slug": "crosfield-boron-foliar",
        "name": "Crosfield Boron Foliar 20%",
        "sku": "CF-S-B-20",
        "category": "specialty-nutrients",
        "price": "1450.00",
        "stock": 600,
        "short": "Foliar boron for fruit set and oilseed flowering. 1 L bottle.",
        "industries": ["horticulture", "oilseeds"],
    },
    {
        "slug": "crosfield-water-soluble-19-19-19",
        "name": "Crosfield Water-Soluble 19-19-19",
        "sku": "CF-S-WS-19",
        "category": "specialty-nutrients",
        "price": "4800.00",
        "stock": 950,
        "short": "Fully water-soluble NPK with micros — drip and fertigation systems.",
        "industries": ["horticulture"],
    },
    {
        "slug": "crosfield-chelated-iron",
        "name": "Crosfield Chelated Iron (EDDHA-Fe 6%)",
        "sku": "CF-S-FE-6",
        "category": "specialty-nutrients",
        "price": "8900.00",
        "stock": 200,
        "short": "EDDHA-chelated iron — corrects lime-induced chlorosis in fruit trees.",
        "industries": ["horticulture"],
    },
    {
        "slug": "crosfield-calcium-nitrate",
        "name": "Crosfield Calcium Nitrate",
        "sku": "CF-S-CAN-WS",
        "category": "specialty-nutrients",
        "price": "3200.00",
        "stock": 1400,
        "short": "Water-soluble calcium nitrate — protected cropping and tomato fertigation.",
        "industries": ["horticulture"],
    },
    # Crop protection
    {
        "slug": "crosfield-glyphosate-41",
        "name": "Crosfield Glyphosate 41% SL",
        "sku": "CF-CP-GLY-41",
        "category": "crop-protection",
        "price": "2200.00",
        "stock": 1700,
        "short": "Non-selective post-emergence herbicide — pre-sowing burn-down.",
        "industries": ["cereals", "cotton", "sugarcane"],
    },
    {
        "slug": "crosfield-imidacloprid-200",
        "name": "Crosfield Imidacloprid 200 SL",
        "sku": "CF-CP-IMI-200",
        "category": "crop-protection",
        "price": "5100.00",
        "stock": 540,
        "short": "Systemic insecticide for sucking pests in cotton, vegetables, and rice.",
        "industries": ["cotton", "horticulture", "rice-paddy"],
    },
    {
        "slug": "crosfield-mancozeb-75wp",
        "name": "Crosfield Mancozeb 75% WP",
        "sku": "CF-CP-MAN-75",
        "category": "crop-protection",
        "price": "1750.00",
        "stock": 1100,
        "short": "Protective contact fungicide — broad-spectrum disease control.",
        "industries": ["horticulture", "oilseeds"],
    },
    {
        "slug": "crosfield-emamectin-19ec",
        "name": "Crosfield Emamectin Benzoate 1.9% EC",
        "sku": "CF-CP-EMA-19",
        "category": "crop-protection",
        "price": "3450.00",
        "stock": 320,
        "short": "Lepidopteran insecticide for cotton bollworm and vegetable caterpillars.",
        "industries": ["cotton", "horticulture"],
    },
    # Industrial
    {
        "slug": "crosfield-citric-acid-anhydrous",
        "name": "Crosfield Citric Acid Anhydrous",
        "sku": "CF-IND-CIT-ANH",
        "category": "industrial-inputs",
        "price": "650.00",
        "stock": 8000,
        "short": "Food-grade citric acid — beverage, confectionery, and feed processors.",
        "industries": ["industrial-processing", "livestock-feed"],
    },
    {
        "slug": "crosfield-monocalcium-phosphate",
        "name": "Crosfield Monocalcium Phosphate (Feed)",
        "sku": "CF-IND-MCP-FG",
        "category": "industrial-inputs",
        "price": "1200.00",
        "stock": 3500,
        "short": "Feed-grade monocalcium phosphate — phosphorus + calcium for livestock feed manufacturers.",
        "industries": ["livestock-feed", "industrial-processing"],
    },
    {
        "slug": "crosfield-sodium-bicarbonate-fg",
        "name": "Crosfield Sodium Bicarbonate (Feed Grade)",
        "sku": "CF-IND-NAHCO3-FG",
        "category": "industrial-inputs",
        "price": "480.00",
        "stock": 6200,
        "short": "Feed-grade sodium bicarbonate — buffer for ruminant and poultry feed.",
        "industries": ["livestock-feed", "industrial-processing"],
    },
]

SERVICES = [
    {
        "slug": "agronomy-field-visit",
        "name": "Agronomy Field Visit",
        "category": ServiceCategory.AGRONOMY,
        "summary": "Named agronomist visits your field for nutrient planning and crop diagnosis.",
        "deliverables": [
            "On-site field walk",
            "Soil sampling brief",
            "Written application schedule",
            "Follow-up call within 14 days",
        ],
        "typical_timeline": "1–2 weeks from request",
        "pricing_model": "Fixed scope per field",
    },
    {
        "slug": "crop-protection-programme",
        "name": "Crop Protection Programme",
        "category": ServiceCategory.AGRONOMY,
        "summary": "Season-long crop-protection schedule built around your crop, region, and pest pressure.",
        "deliverables": ["Pest-pressure assessment", "Spray calendar", "Product list with rates"],
        "typical_timeline": "2 weeks",
        "pricing_model": "Fixed scope",
    },
    {
        "slug": "soil-health-audit",
        "name": "Soil Health Audit",
        "category": ServiceCategory.AGRONOMY,
        "summary": "Lab-backed soil characterisation and a 3-season nutrient rebuild plan.",
        "deliverables": ["Composite soil sampling", "Full lab analysis", "3-season rebuild plan"],
        "typical_timeline": "4–6 weeks",
        "pricing_model": "Per field, fixed",
    },
    {
        "slug": "contract-manufacturing-bulk-fertilizer",
        "name": "Contract Manufacturing — Bulk Fertilizer",
        "category": ServiceCategory.MANUFACTURING,
        "summary": "We produce your fertilizer SKU under your specification on our equipment, with full QA traceability.",
        "deliverables": [
            "Process qualification batch",
            "Pilot run + customer QA review",
            "Commercial-scale production",
            "Per-lot certificate of analysis",
        ],
        "typical_timeline": "8–12 weeks first batch",
        "pricing_model": "Tolling fee + raw material pass-through",
    },
    {
        "slug": "contract-manufacturing-agrochemical",
        "name": "Contract Manufacturing — Agrochemical Formulation",
        "category": ServiceCategory.MANUFACTURING,
        "summary": "EC, SC, WP, and WG formulations produced under your label and regulatory registration.",
        "deliverables": [
            "Formulation transfer",
            "Pilot batch",
            "Commercial production",
            "Stability data on request",
        ],
        "typical_timeline": "12–16 weeks",
        "pricing_model": "Tolling + actives pass-through",
    },
    {
        "slug": "formulation-development-fertilizer",
        "name": "Formulation Development — Fertilizer",
        "category": ServiceCategory.FORMULATION,
        "summary": "Bespoke fertilizer formulation from concept to commercial-ready specification.",
        "deliverables": [
            "Feasibility note",
            "Lab-scale prototype",
            "Stability + handling data",
            "Scale-up plan",
            "Specification handover",
        ],
        "typical_timeline": "12–24 weeks",
        "pricing_model": "Phased fixed-fee per milestone",
    },
    {
        "slug": "formulation-development-agrochemical",
        "name": "Formulation Development — Agrochemical",
        "category": ServiceCategory.FORMULATION,
        "summary": "Develop a stable, registerable agrochemical formulation around your active ingredient.",
        "deliverables": [
            "Pre-formulation screening",
            "Lead candidate selection",
            "Accelerated stability",
            "Registration-ready spec",
        ],
        "typical_timeline": "16–32 weeks",
        "pricing_model": "Phased fixed-fee",
    },
    {
        "slug": "scheduled-deliveries",
        "name": "Scheduled Deliveries",
        "category": ServiceCategory.LOGISTICS,
        "summary": "Pre-scheduled call-off shipments aligned with your application or production calendar.",
        "deliverables": ["Annual call-off plan", "Named logistics contact", "Lead-time SLA"],
        "typical_timeline": "Operational within 4 weeks",
        "pricing_model": "Volume-tier pricing",
    },
    {
        "slug": "consignment-stocking",
        "name": "Consignment Stocking",
        "category": ServiceCategory.LOGISTICS,
        "summary": "We hold product at your site or a nominated warehouse; you draw as you consume.",
        "deliverables": [
            "Stocking agreement",
            "Replenishment SLA",
            "Monthly consumption reporting",
        ],
        "typical_timeline": "6–8 weeks to set up",
        "pricing_model": "Per-unit holding fee + product",
    },
    {
        "slug": "regulatory-documentation-pack",
        "name": "Regulatory Documentation Pack",
        "category": ServiceCategory.OTHER,
        "summary": "Compiled regulatory dossier — CoAs, MSDS, registrations, audit reports — for buyer onboarding.",
        "deliverables": [
            "Per-product CoA archive",
            "MSDS in current format",
            "Registration certificates",
            "Latest ISO surveillance reports",
        ],
        "typical_timeline": "1 week",
        "pricing_model": "Fixed fee per pack",
    },
]


class Command(BaseCommand):
    help = "Seed development catalog data (categories, industries, products, services)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously-seeded rows (by slug prefix) before reseeding.",
        )

    @transaction.atomic
    def handle(self, *args, flush: bool = False, **opts):
        if flush:
            self._flush()

        cats = self._seed_categories()
        inds = self._seed_industries()
        prods = self._seed_products(cats, inds)
        offs = self._seed_services()
        self._seed_variants(prods)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(cats)} categories, {len(inds)} industries, "
                f"{len(prods)} products, {len(offs)} services."
            )
        )

    # ---------- seeders ----------
    def _seed_categories(self) -> dict[str, Category]:
        out = {}
        for entry in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "description": entry["description"],
                    "is_active": True,
                },
            )
            out[cat.slug] = cat
            self.stdout.write(f"  {'+ ' if created else '= '}category {cat.slug}")
        return out

    def _seed_industries(self) -> dict[str, Industry]:
        out = {}
        for position, entry in enumerate(INDUSTRIES, start=1):
            ind, created = Industry.objects.get_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "summary": entry["summary"],
                    "body": entry["summary"]
                    + " Talk to our agronomy team for crop-specific recommendations.",
                    "is_active": True,
                    "position": position,
                },
            )
            out[ind.slug] = ind
            self.stdout.write(f"  {'+ ' if created else '= '}industry {ind.slug}")
        return out

    def _seed_products(self, cats: dict[str, Category], inds: dict[str, Industry]) -> list[Product]:
        out = []
        for entry in PRODUCTS:
            product, created = Product.objects.get_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "sku": entry["sku"],
                    "category": cats[entry["category"]],
                    "short_description": entry["short"],
                    "description": (
                        entry["short"] + "\n\nManufactured at Crosfield Agro Pakistan under "
                        "ISO-certified processes with batch-level traceability. "
                        "Certificate of analysis shipped with every order."
                    ),
                    "specifications": _spec_for(entry),
                    "unit_price": Decimal(entry["price"]),
                    "currency": "PKR",
                    "track_inventory": True,
                    "stock_quantity": entry["stock"],
                    "min_order_quantity": 1,
                    "status": ProductStatus.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            # Link industries M2M (idempotent)
            for ind_slug in entry["industries"]:
                if ind_slug in inds:
                    product.industries.add(inds[ind_slug])
            out.append(product)
            self.stdout.write(f"  {'+ ' if created else '= '}product {product.slug}")
        return out

    def _seed_variants(self, products: list[Product]) -> None:
        """Give the fertilizer products a couple of pack-size variants."""
        for product in products:
            if (
                "fertilizer" not in product.category.name.lower()
                and "nutrients" not in product.category.name.lower()
            ):
                continue
            for suffix, size, mult in [
                ("25kg", "25 kg bag", Decimal("0.55")),
                ("50kg", "50 kg bag", Decimal("1.00")),
            ]:
                ProductVariant.objects.get_or_create(
                    sku=f"{product.sku}-{suffix.upper()}",
                    defaults={
                        "product": product,
                        "name": size,
                        "unit_price": (product.unit_price * mult).quantize(Decimal("0.01")),
                        "stock_quantity": product.stock_quantity // 2,
                        "attributes": {"pack_size": size},
                        "is_active": True,
                    },
                )

    def _seed_services(self) -> list[ServiceOffering]:
        out = []
        for position, entry in enumerate(SERVICES, start=1):
            offering, created = ServiceOffering.objects.get_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "category": entry["category"],
                    "summary": entry["summary"],
                    "body": (
                        entry["summary"] + "\n\nEvery engagement begins with a written scope and "
                        "named contacts on both sides. Pricing fixed where the scope allows; "
                        "time-and-materials where it doesn't."
                    ),
                    "deliverables": entry["deliverables"],
                    "typical_timeline": entry["typical_timeline"],
                    "pricing_model": entry["pricing_model"],
                    "is_active": True,
                    "position": position,
                },
            )
            out.append(offering)
            self.stdout.write(f"  {'+ ' if created else '= '}service {offering.slug}")
        return out

    # ---------- flush ----------
    def _flush(self) -> None:
        cat_slugs = [c["slug"] for c in CATEGORIES]
        ind_slugs = [i["slug"] for i in INDUSTRIES]
        prod_slugs = [p["slug"] for p in PRODUCTS]
        svc_slugs = [s["slug"] for s in SERVICES]

        ProductVariant.objects.filter(product__slug__in=prod_slugs).delete()
        Product.objects.filter(slug__in=prod_slugs).delete()
        Industry.objects.filter(slug__in=ind_slugs).delete()
        # Categories are protected by Product FK; delete after products gone.
        Category.objects.filter(slug__in=cat_slugs).delete()
        ServiceOffering.objects.filter(slug__in=svc_slugs).delete()
        self.stdout.write(self.style.WARNING("Flushed previously-seeded rows."))


def _spec_for(entry: dict) -> dict:
    """Tiny specs dict so product detail pages show something useful."""
    return {
        "Pack size": "50 kg (default)",
        "Composition": (
            entry["short"].split("—")[0].strip() if "—" in entry["short"] else "See product label"
        ),
        "Origin": "Manufactured in Pakistan",
        "Storage": "Cool, dry, well-ventilated; keep sealed",
    }
