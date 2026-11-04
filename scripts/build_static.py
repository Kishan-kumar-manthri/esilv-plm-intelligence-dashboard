"""Build a public, static dashboard snapshot from the supplied PLM XML."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plm.parser import load_dataset


def main() -> None:
    dataset = load_dataset(ROOT / "data" / "raw" / "XPDMXML_ECAR_PLM.xml")
    products = []
    for product in dataset.products.values():
        products.append(
            {
                "id": product.source.xml_id,
                "name": product.name,
                "plm_id": product.plm_id,
                "revision": product.revision,
                "maturity": product.maturity,
                "lifecycle": product.lifecycle,
                "mass_kg": product.mass_kg,
                "material": product.material,
                "description": product.description,
                "is_root": product.is_root,
                "is_leaf": product.is_leaf,
                "item_kind": product.item_kind,
                "has_representation": product.has_representation,
                "source": product.source.label(),
            }
        )
    relationships = [
        {
            "parent": line.parent_id,
            "child": line.child_id,
            "quantity": line.quantity,
        }
        for line in dataset.bom_lines
    ]
    payload = {
        "root_id": dataset.root.source.xml_id,
        "root_mass_kg": dataset.root.mass_kg,
        "products": products,
        "relationships": relationships,
        "warnings": dataset.warnings,
    }
    output = ROOT / "static" / "data.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
