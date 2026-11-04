from pathlib import Path

import pytest

from plm.agent.qa import answer_question
from plm.analysis import impact_summary, material_summary, product_statistics, risk_insights
from plm.parser import load_dataset


DATASET = Path(__file__).parents[1] / "data" / "raw" / "XPDMXML_ECAR_PLM.xml"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(DATASET)


def test_statistics_are_dataset_derived(dataset):
    stats = product_statistics(dataset)
    assert stats["products"] == 79
    assert stats["root_mass_kg"] == pytest.approx(100.1)
    assert stats["materials"] == 14


def test_intelligence_reports_actual_data_gaps(dataset):
    titles = {insight.title for insight in risk_insights(dataset)}
    assert "Material data is incomplete" in titles
    assert "Lifecycle signal is not discriminating" in titles


def test_material_summary_is_not_fabricated(dataset):
    summary = material_summary(dataset)
    assert len(summary) == 14
    assert sum(row["count"] for row in summary) == 73


def test_change_impact_finds_parent_assemblies(dataset):
    product = next(p for p in dataset.products.values() if "Screw D10 L155" in p.name)
    result = impact_summary(dataset, product.source.xml_id)
    names = {item.product.name for item in result["affected"]}
    assert "ECAR-EI_HOUSING FRONT EDRIVE" in names
    assert result["cost_available"] is False


def test_assistant_cites_dataset_and_refuses_missing_business_data(dataset):
    answer = answer_question(dataset, "What is the cost of this component?")
    assert "does not contain" in answer
    answer = answer_question(dataset, "What is the mass of ECAR-EI_410KW_EDRIVE_FRONT?")
    assert "100.100" in answer
    assert "XPDMXML_ECAR_PLM.xml" in answer

