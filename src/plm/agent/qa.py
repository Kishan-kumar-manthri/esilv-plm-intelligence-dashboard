"""Simple deterministic assistant with evidence citations."""

from __future__ import annotations

import re

from plm.analysis.change_impact import ancestors
from plm.parser.models import ParsedDataset, Product


def _find_product(dataset: ParsedDataset, question: str) -> Product | None:
    lowered = question.lower()
    matches = [
        product for product in dataset.products.values()
        if product.name.lower() in lowered or product.plm_id.lower() in lowered
    ]
    return max(matches, key=lambda product: len(product.name)) if matches else None


def answer_question(dataset: ParsedDataset, question: str) -> str:
    """Answer common engineering questions from the parsed dataset only."""
    q = question.lower().strip()
    if not q:
        return "Please enter a question about the loaded PLM dataset."
    product = _find_product(dataset, question)

    if "in_work" in q or ("maturity" in q and "which" in q):
        products = [p for p in dataset.products.values() if p.maturity == "IN_WORK"]
        lines = [f"- {p.name} ({p.plm_id}) — {p.maturity}; source: {p.source.label()}" for p in products[:20]]
        suffix = f"\n…and {len(products) - 20} more." if len(products) > 20 else ""
        return f"{len(products)} products have maturity IN_WORK.\n" + "\n".join(lines) + suffix

    if ("component" in q or "children" in q or "parts" in q) and product:
        children = dataset.children(product.source.xml_id)
        if not children:
            return f"{product.name} has no child products. Source: {product.source.label()}"
        lines = [
            f"- {child.name} ({child.plm_id}), quantity {dataset.quantity(product.source.xml_id, child.source.xml_id)}"
            for child in children
        ]
        return f"Children of {product.name}:\n" + "\n".join(lines) + f"\nSource: {product.source.label()}"

    if ("depend" in q or "affected" in q or "impact" in q) and product:
        impacted = ancestors(dataset, product.source.xml_id)
        if not impacted:
            return f"No parent assemblies were found for {product.name}. Source: {product.source.label()}"
        lines = [f"- {item.product.name} ({item.product.plm_id})" for item in impacted]
        return f"Potential parent impact for {product.name}:\n" + "\n".join(lines) + (
            f"\nSource: {product.source.label()}"
        )

    if "material" in q or "mass" in q:
        if product:
            return (
                f"{product.name}: mass={product.mass_kg:.3f} kg; "
                f"material={product.material or 'not available'}; source: {product.source.label()}"
            )
        return (
            f"The dataset contains {len({p.material for p in dataset.products.values() if p.material})} "
            f"distinct material values and root mass {dataset.root.mass_kg:.3f} kg. "
            f"Source: {dataset.root.source.label()}"
        )

    if "assembly" in q or "main" in q:
        assemblies = [p for p in dataset.products.values() if not p.is_leaf]
        lines = [f"- {p.name} ({p.mass_kg:.3f} kg), source: {p.source.label()}" for p in assemblies[:10]]
        return "Assemblies in the dataset:\n" + "\n".join(lines)

    if any(term in q for term in ("supplier", "cost", "price", "lead time")):
        return "The XML does not contain supplier, cost, currency or lead-time data. No value was invented."

    return (
        "I can answer questions about assemblies, children, maturity, materials, mass and parent impact. "
        "The requested information was not matched to a supported dataset query."
    )

