"""Typed records used by the parser and analysis layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SourceRef:
    file: str
    element: str
    xml_id: str
    xid: Optional[str] = None
    line: Optional[int] = None

    def label(self) -> str:
        location = f" line {self.line}" if self.line else ""
        return f"{self.file}:{self.element} {self.xml_id}{location}"


@dataclass
class ExportInfo:
    values: dict[str, str]
    root_xml_id: str
    root_xid: Optional[str]


@dataclass
class Product:
    source: SourceRef
    plm_id: str
    name: str
    description: Optional[str]
    xid: str
    revision: str
    revision_index: int
    revision_family: str
    maturity: str
    lifecycle: str
    created_at: Optional[datetime]
    modified_at: Optional[datetime]
    owner: str
    organization: str
    project: str
    security_level: int
    mass_kg: float
    material: Optional[str]
    is_root: bool = False
    is_leaf: bool = False
    item_kind: str = "part"
    has_representation: bool = False


@dataclass
class Instance:
    source: SourceRef
    instance_name: str
    xid: str
    parent_id: str
    child_id: str
    child_order: float
    rotation: tuple[float, ...] = ()
    translation: tuple[float, ...] = ()


@dataclass
class Representation:
    source: SourceRef
    plm_id: str
    name: str
    xid: str
    product_id: str
    revision: str
    revision_index: int
    revision_family: str
    maturity: str
    lifecycle: str


@dataclass
class BomLine:
    parent_id: str
    child_id: str
    quantity: int
    instance_ids: list[str]
    order: float


@dataclass
class ParsedDataset:
    source_path: str
    export_info: ExportInfo
    products: dict[str, Product]
    instances: dict[str, Instance]
    representations: dict[str, Representation]
    bom_lines: list[BomLine]
    warnings: list[str] = field(default_factory=list)

    @property
    def root(self) -> Product:
        return self.products[self.export_info.root_xml_id]

    def children(self, product_id: str) -> list[Product]:
        lines = sorted(
            (line for line in self.bom_lines if line.parent_id == product_id),
            key=lambda line: line.order,
        )
        return [self.products[line.child_id] for line in lines]

    def parents(self, product_id: str) -> list[Product]:
        return [
            self.products[line.parent_id]
            for line in self.bom_lines
            if line.child_id == product_id
        ]

    def quantity(self, parent_id: str, child_id: str) -> int:
        for line in self.bom_lines:
            if line.parent_id == parent_id and line.child_id == child_id:
                return line.quantity
        return 0

