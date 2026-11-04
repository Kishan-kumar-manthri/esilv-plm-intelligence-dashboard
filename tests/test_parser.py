from pathlib import Path

import pytest

from plm.parser import XMLParseError, load_dataset


DATASET = Path(__file__).parents[1] / "data" / "raw" / "XPDMXML_ECAR_PLM.xml"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(DATASET)


def test_loads_actual_xml(dataset):
    assert dataset.root.name == "ECAR-EI_410KW_EDRIVE_FRONT"
    assert len(dataset.products) == 79
    assert len(dataset.instances) == 112
    assert len(dataset.representations) == 36


def test_product_fields_and_namespace(dataset):
    root = dataset.root
    assert root.plm_id.startswith("prd-")
    assert root.revision == "D"
    assert root.revision_index == 4
    assert root.maturity == "IN_WORK"
    assert root.mass_kg == pytest.approx(100.1)
    assert root.source.xml_id == "ID_0"


def test_relationships_and_quantities(dataset):
    housing = next(p for p in dataset.products.values() if "HOUSING FRONT EDRIVE" in p.name)
    screw = next(p for p in dataset.products.values() if "Screw D10 L155" in p.name)
    assert dataset.quantity(housing.source.xml_id, screw.source.xml_id) == 14
    assert screw in dataset.children(housing.source.xml_id)
    assert housing in dataset.parents(screw.source.xml_id)


def test_mass_rollup_and_traceability(dataset):
    assert not dataset.warnings
    assert all(product.source.file == DATASET.name for product in dataset.products.values())
    assert sum(line.quantity for line in dataset.bom_lines) == 112


def test_every_product_is_reachable_and_leaves_have_representations(dataset):
    assert sum(product.is_leaf for product in dataset.products.values()) == 36
    assert sum(product.has_representation for product in dataset.products.values()) == 36
    assert sum(product.item_kind == "wrapper" for product in dataset.products.values()) == 37


def test_invalid_xml_fails_loudly(tmp_path):
    path = tmp_path / "invalid.xml"
    path.write_text("<not-plm/>")
    with pytest.raises(XMLParseError):
        load_dataset(path)
