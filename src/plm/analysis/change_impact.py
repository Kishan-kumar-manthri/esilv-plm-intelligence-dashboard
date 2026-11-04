"""Where-used and change impact calculations over the product graph."""

from __future__ import annotations

from dataclasses import dataclass

from plm.parser.models import ParsedDataset, Product, SourceRef


@dataclass(frozen=True)
class ImpactItem:
    product: Product
    distance: int
    relationship_sources: tuple[SourceRef, ...]


def ancestors(dataset: ParsedDataset, product_id: str) -> list[ImpactItem]:
    """Return all parent products, nearest first, with relationship evidence."""
    result: list[ImpactItem] = []
    frontier = [(product_id, 0)]
    seen = {product_id}
    while frontier:
        current, distance = frontier.pop(0)
        for line in dataset.bom_lines:
            if line.child_id != current or line.parent_id in seen:
                continue
            seen.add(line.parent_id)
            sources = tuple(dataset.instances[i].source for i in line.instance_ids)
            result.append(ImpactItem(dataset.products[line.parent_id], distance + 1, sources))
            frontier.append((line.parent_id, distance + 1))
    return result


def impact_summary(dataset: ParsedDataset, product_id: str) -> dict[str, object]:
    if product_id not in dataset.products:
        raise KeyError(f"Unknown product: {product_id}")
    affected = ancestors(dataset, product_id)
    parent_ids = {item.product.source.xml_id for item in affected}
    return {
        "selected": dataset.products[product_id],
        "affected": affected,
        "affected_count": len(affected),
        "affected_mass_kg": sum(dataset.products[item.product.source.xml_id].mass_kg for item in affected),
        "cost_available": False,
        "supplier_available": False,
        "unavailable": [
            "Supplier data is not present in the XML.",
            "Cost, currency and requalification estimates are not present in the XML.",
        ],
        "parent_ids": parent_ids,
    }


def replacement_comparison(
    selected: Product, proposed_mass_kg: float | None = None, proposed_material: str | None = None
) -> list[dict[str, object]]:
    """Compare only properties supplied by the user; never invent replacement values."""
    rows: list[dict[str, object]] = []
    if proposed_mass_kg is not None:
        rows.append({
            "property": "Mass (kg)",
            "current": selected.mass_kg,
            "proposed": proposed_mass_kg,
            "delta": proposed_mass_kg - selected.mass_kg,
            "source": selected.source.label(),
        })
    if proposed_material:
        rows.append({
            "property": "Material",
            "current": selected.material or "Unavailable",
            "proposed": proposed_material,
            "delta": "Changed" if proposed_material != selected.material else "Unchanged",
            "source": selected.source.label(),
        })
    return rows

