"""Deterministic, traceable product intelligence calculations."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from plm.parser.models import ParsedDataset, Product, SourceRef


@dataclass(frozen=True)
class Insight:
    severity: str
    title: str
    detail: str
    sources: tuple[SourceRef, ...]


def product_statistics(dataset: ParsedDataset) -> dict[str, int | float]:
    products = list(dataset.products.values())
    return {
        "products": len(products),
        "assemblies": sum(not product.is_leaf for product in products),
        "leaves": sum(product.is_leaf for product in products),
        "instances": len(dataset.instances),
        "bom_lines": len(dataset.bom_lines),
        "representations": len(dataset.representations),
        "materials": len({p.material for p in products if p.material}),
        "root_mass_kg": dataset.root.mass_kg,
    }


def material_summary(dataset: ParsedDataset) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for product in dataset.products.values():
        if not product.material:
            continue
        entry = grouped.setdefault(product.material, {"material": product.material, "count": 0, "mass_kg": 0.0})
        entry["count"] = int(entry["count"]) + 1
        entry["mass_kg"] = float(entry["mass_kg"]) + product.mass_kg
    return sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["material"])))


def missing_information(dataset: ParsedDataset) -> list[Insight]:
    missing_material = tuple(p.source for p in dataset.products.values() if not p.material)
    missing_description = tuple(p.source for p in dataset.products.values() if not p.description)
    insights: list[Insight] = []
    if missing_material:
        insights.append(Insight(
            "medium",
            "Material data is incomplete",
            f"{len(missing_material)} products have no material value in the XML.",
            missing_material,
        ))
    if missing_description:
        insights.append(Insight(
            "low",
            "Descriptions are incomplete",
            f"{len(missing_description)} products have no description in the XML.",
            missing_description[:10],
        ))
    return insights


def risk_insights(dataset: ParsedDataset) -> list[Insight]:
    insights = missing_information(dataset)
    maturity_counts = Counter(product.maturity for product in dataset.products.values())
    if len(maturity_counts) == 1:
        sources = tuple(product.source for product in dataset.products.values())
        insights.append(Insight(
            "medium",
            "Lifecycle signal is not discriminating",
            f"All {len(sources)} products have maturity {next(iter(maturity_counts))}; "
            "maturity alone cannot rank product risk.",
            sources[:10],
        ))
    if dataset.export_info.values.get("WithProcess") == "Yes":
        insights.append(Insight(
            "low",
            "Export metadata/process mismatch",
            "The header says WithProcess=Yes, but no process objects are present in this extract.",
            tuple(product.source for product in dataset.products.values())[:1],
        ))
    if dataset.warnings:
        insights.append(Insight(
            "high",
            "Mass roll-up mismatch",
            f"{len(dataset.warnings)} assembly mass checks do not match their children.",
            tuple(product.source for product in dataset.products.values() if not product.is_leaf),
        ))
    return insights


def search_products(dataset: ParsedDataset, query: str, maturity: str = "All") -> list[Product]:
    normalized = " ".join(query.lower().split())
    return [
        product
        for product in dataset.products.values()
        if (not normalized or normalized in product.name.lower() or normalized in product.plm_id.lower())
        and (maturity == "All" or product.maturity == maturity)
    ]

