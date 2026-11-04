"""Parser for the namespaced XPDMXML export."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .models import (
    BomLine,
    ExportInfo,
    Instance,
    ParsedDataset,
    Product,
    Representation,
    SourceRef,
)

NS = "http://www.3ds.com/xsd/XPDMXML"
Q = f"{{{NS}}}"


class XMLParseError(ValueError):
    """Raised when an export cannot be safely mapped to the data model."""


def _text(element: ET.Element, name: str, required: bool = False) -> str:
    child = element.find(Q + name)
    value = (child.text or "").strip() if child is not None else ""
    if required and not value:
        raise XMLParseError(f"Missing required {name} in {element.tag}")
    return value


def _optional(value: str) -> str | None:
    return value or None


def _datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise XMLParseError(f"Invalid timestamp: {value}") from exc


def _numbers(value: str) -> tuple[float, ...]:
    if not value:
        return ()
    try:
        return tuple(float(part) for part in value.split())
    except ValueError as exc:
        raise XMLParseError(f"Invalid numeric transform: {value}") from exc


def _source(element: ET.Element, path: Path) -> SourceRef:
    unique = element.find(Q + "UniqueID")
    xid = unique.attrib.get("XID") if unique is not None else None
    return SourceRef(path.name, element.tag.rsplit("}", 1)[-1], element.attrib["id"], xid)


def _normalise_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    name = name.replace("ECAR-3D ", "ECAR-3D_")
    name = re.sub(r"(ECAR-(?:EI|3D)_)\s+", r"\1", name)
    return name


def load_dataset(path: str | Path) -> ParsedDataset:
    """Load, resolve and validate one XPDMXML product structure."""
    source_path = Path(path)
    try:
        root = ET.parse(source_path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise XMLParseError(f"Unable to read XML file {source_path}: {exc}") from exc

    if root.tag != Q + "XPDMXML":
        raise XMLParseError("Unexpected XML root or namespace")
    structure = root.find(Q + "ProductStructure")
    if structure is None:
        raise XMLParseError("ProductStructure is missing")

    header = {
        info.attrib["name"]: info.attrib.get("value", "")
        for info in root.findall(f"{Q}InfoHeader/{Q}Info")
    }
    root_id = structure.attrib.get("rootRefs", "")
    if not root_id:
        raise XMLParseError("ProductStructure/rootRefs is missing")

    product_elements = structure.findall(Q + "Product")
    products: dict[str, Product] = {}
    seen_plm_ids: set[str] = set()
    seen_xids: set[str] = set()
    for element in product_elements:
        xml_id = element.attrib.get("id")
        if not xml_id or xml_id in products:
            raise XMLParseError(f"Duplicate or missing product @id: {xml_id}")
        source = _source(element, source_path)
        plm_id = _text(element, "ID", required=True)
        xid = source.xid or _text(element, "UniqueID", required=True)
        if plm_id in seen_plm_ids or xid in seen_xids:
            raise XMLParseError(f"Duplicate product identifier: {plm_id}")
        seen_plm_ids.add(plm_id)
        seen_xids.add(xid)
        try:
            revision_index = int(_text(element, "RevisionIndex", required=True))
            security_level = int(_text(element, "SecurityLevel", required=True))
            mass = float(_text(element, "WCGEquivalentComputedExt.V_WCG_Mass", required=True))
        except ValueError as exc:
            raise XMLParseError(f"Invalid numeric product field for {xml_id}") from exc
        products[xml_id] = Product(
            source=source,
            plm_id=plm_id,
            name=_text(element, "Name", required=True),
            description=_optional(_text(element, "Description")),
            xid=xid,
            revision=_text(element, "RevisionName", required=True),
            revision_index=revision_index,
            revision_family=_text(element, "RevisionFamily", required=True),
            maturity=_text(element, "Maturity", required=True),
            lifecycle=_text(element, "Lifecycle", required=True),
            created_at=_datetime(_text(element, "TimeCreated")),
            modified_at=_datetime(_text(element, "TimeModified")),
            owner=_text(element, "Owner"),
            organization=_text(element, "Organization"),
            project=_text(element, "Project"),
            security_level=security_level,
            mass_kg=mass,
            material=_optional(_text(element, "Material")),
        )

    if root_id not in products:
        raise XMLParseError(f"Root product {root_id} does not exist")
    if header.get("SourceObjectRef") and header["SourceObjectRef"] != root_id:
        raise XMLParseError("Header SourceObjectRef does not match rootRefs")

    instances: dict[str, Instance] = {}
    grouped: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for element in structure.findall(Q + "ProductInst"):
        xml_id = element.attrib.get("id")
        if not xml_id or xml_id in instances:
            raise XMLParseError(f"Duplicate or missing instance @id: {xml_id}")
        source = _source(element, source_path)
        parent_id = _text(element, "Owned", required=True)
        child_id = _text(element, "Instancing", required=True)
        if parent_id not in products or child_id not in products:
            raise XMLParseError(f"Dangling ProductInst reference in {xml_id}")
        try:
            child_order = float(_text(element, "ChildOrder", required=True))
        except ValueError as exc:
            raise XMLParseError(f"Invalid ChildOrder in {xml_id}") from exc
        transform = element.find(Q + "RelativeTransformation3D")
        rotation = _numbers(_text(transform, "Rotation3D")) if transform is not None else ()
        translation = _numbers(_text(transform, "Translation3D")) if transform is not None else ()
        instance = Instance(
            source=source,
            instance_name=_text(element, "ID"),
            xid=source.xid or "",
            parent_id=parent_id,
            child_id=child_id,
            child_order=child_order,
            rotation=rotation,
            translation=translation,
        )
        instances[xml_id] = instance
        grouped[(parent_id, child_id)].append(xml_id)

    representations: dict[str, Representation] = {}
    for element in structure.findall(Q + "Rep3DAggr"):
        xml_id = element.attrib.get("id")
        if not xml_id or xml_id in representations:
            raise XMLParseError(f"Duplicate or missing representation @id: {xml_id}")
        source = _source(element, source_path)
        product_id = _text(element, "Owned", required=True)
        if product_id not in products:
            raise XMLParseError(f"Dangling representation reference in {xml_id}")
        try:
            revision_index = int(_text(element, "RevisionIndex", required=True))
        except ValueError as exc:
            raise XMLParseError(f"Invalid representation revision in {xml_id}") from exc
        representations[xml_id] = Representation(
            source=source,
            plm_id=_text(element, "ID", required=True),
            name=_text(element, "Name", required=True),
            xid=source.xid or "",
            product_id=product_id,
            revision=_text(element, "RevisionName", required=True),
            revision_index=revision_index,
            revision_family=_text(element, "RevisionFamily", required=True),
            maturity=_text(element, "Maturity", required=True),
            lifecycle=_text(element, "Lifecycle", required=True),
        )

    child_ids = {instance.parent_id for instance in instances.values()}
    representation_product_ids = {rep.product_id for rep in representations.values()}
    for product_id, product in products.items():
        product.is_root = product_id == root_id
        product.is_leaf = product_id not in child_ids
        product.has_representation = product_id in representation_product_ids
        product.item_kind = "part" if product.is_leaf else "assembly"
    bom_lines = [
        BomLine(
            parent_id=parent_id,
            child_id=child_id,
            quantity=len(instance_ids),
            instance_ids=instance_ids,
            order=min(instances[i].child_order for i in instance_ids),
        )
        for (parent_id, child_id), instance_ids in grouped.items()
    ]
    for product in products.values():
        child_lines = [line for line in bom_lines if line.parent_id == product.source.xml_id]
        if (
            not product.is_leaf
            and len(child_lines) == 1
            and child_lines[0].quantity == 1
            and products[child_lines[0].child_id].is_leaf
        ):
            product.item_kind = "wrapper"

    _validate_acyclic(products, instances, root_id)
    warnings = _mass_warnings(products, bom_lines)
    return ParsedDataset(
        source_path=str(source_path),
        export_info=ExportInfo(
            values=header,
            root_xml_id=root_id,
            root_xid=products[root_id].xid,
        ),
        products=products,
        instances=instances,
        representations=representations,
        bom_lines=sorted(bom_lines, key=lambda line: (line.parent_id, line.order)),
        warnings=warnings,
    )


def _validate_acyclic(
    products: dict[str, Product], instances: dict[str, Instance], root_id: str
) -> None:
    children: defaultdict[str, list[str]] = defaultdict(list)
    for instance in instances.values():
        children[instance.parent_id].append(instance.child_id)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(product_id: str) -> None:
        if product_id in visiting:
            raise XMLParseError(f"Cycle detected at product {product_id}")
        if product_id in visited:
            return
        visiting.add(product_id)
        for child_id in children[product_id]:
            visit(child_id)
        visiting.remove(product_id)
        visited.add(product_id)

    visit(root_id)
    if visited != set(products):
        missing = sorted(set(products) - visited)
        raise XMLParseError(f"Products are disconnected from root: {missing[:3]}")


def _mass_warnings(products: dict[str, Product], bom_lines: list[BomLine]) -> list[str]:
    warnings: list[str] = []
    for product_id, product in products.items():
        lines = [line for line in bom_lines if line.parent_id == product_id]
        if not lines:
            continue
        calculated = sum(products[line.child_id].mass_kg * line.quantity for line in lines)
        if abs(calculated - product.mass_kg) > 1e-3:
            warnings.append(
                f"Mass mismatch for {product.name}: XML={product.mass_kg:.3f} kg, "
                f"calculated={calculated:.3f} kg"
            )
    return warnings
