"""Premium Streamlit interface for PLM Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plm.agent.qa import answer_question
from plm.analysis import impact_summary, material_summary, product_statistics, replacement_comparison, risk_insights, search_products
from plm.parser import XMLParseError, load_dataset
from styles import kpi, load_css, panel_end, panel_start
from visuals import product_svg

DATASET = ROOT / "data" / "raw" / "XPDMXML_ECAR_PLM.xml"
GITHUB_URL = "https://github.com/quentin-trlt/hackathon-plm-intelligence-dassault-systems"
AUTHOR_GITHUB_URL = "https://github.com/Kishan-kumar-manthri"
AUTHOR_GITHUB_NAME = "Kishan-kumar-manthri"


@st.cache_data(show_spinner="Importing PLM dataset...")
def get_dataset(import_signature: int):
    del import_signature
    return load_dataset(DATASET)


def label(product) -> str:
    return f"{product.name}  ·  {product.plm_id}  ·  Rev {product.revision}"


def product_rows(dataset) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Product": p.name, "PLM ID": p.plm_id, "Revision": p.revision,
            "Maturity": p.maturity, "Type": p.item_kind.title(),
            "Mass (kg)": p.mass_kg, "Material": p.material or "Not available",
        }
        for p in dataset.products.values()
    ])


def bom_rows(dataset, product_id: str | None = None, path: str = "", depth: int = 0) -> list[dict[str, object]]:
    """Create an expanded, traceable BOM view from the reference/instance graph."""
    product_id = product_id or dataset.root.source.xml_id
    product = dataset.products[product_id]
    current_path = f"{path} / {product.name}" if path else product.name
    rows = [{
        "Level": depth,
        "Path": current_path,
        "Product": product.name,
        "PLM ID": product.plm_id,
        "Type": product.item_kind.title(),
        "Revision": product.revision,
        "Quantity": 1 if depth == 0 else None,
        "Mass (kg)": product.mass_kg,
        "Material": product.material or "Not available",
        "Source": product.source.label(),
    }]
    for child in dataset.children(product_id):
        quantity = dataset.quantity(product_id, child.source.xml_id)
        child_rows = bom_rows(dataset, child.source.xml_id, current_path, depth + 1)
        if child_rows:
            child_rows[0]["Quantity"] = quantity
        rows.extend(child_rows)
    return rows


def hierarchy_node(dataset, product_id: str, depth: int = 0) -> None:
    """Render a readable hierarchy without nesting Streamlit expanders."""
    product = dataset.products[product_id]
    children = dataset.children(product_id)
    icon = "⬡" if not product.is_leaf else "◈"
    title = f"{icon}  {product.name}  ·  Rev {product.revision}  ·  {product.mass_kg:.3f} kg"
    if children:
        indent = min(depth * 1.2, 8)
        st.markdown(
            f'<div style="margin-left:{indent}rem;margin-top:.7rem;padding:.7rem .8rem;'
            f'border:1px solid #dce5ef;border-left:4px solid #0877b8;border-radius:8px;'
            f'background:#f7faff"><b>{title}</b><br>'
            f'<span style="color:#6b8194;font-size:.74rem">{product.item_kind.title()} · '
            f'{product.plm_id} · {len(children)} direct relationship(s) · '
            f'{product.source.label()}</span></div>',
            unsafe_allow_html=True,
        )
        for child in children:
            quantity = dataset.quantity(product_id, child.source.xml_id)
            st.markdown(
                f'<div style="margin-left:{min((depth + 1) * 1.2, 8)}rem;padding:.35rem 0">'
                f'<span class="tag">QTY {quantity}</span> '
                f'<span style="font-size:.84rem">{child.name}</span></div>',
                unsafe_allow_html=True,
            )
            hierarchy_node(dataset, child.source.xml_id, depth + 1)
    else:
        st.markdown(
            f'<div style="padding:.45rem 0 .45rem {max(depth, 1) * 1.1}rem;border-bottom:1px solid #172c41">'
            f'<span class="tag tag-green">PART</span> <b>{product.name}</b> '
            f'<span style="color:#8fa4b8">Rev {product.revision} · {product.mass_kg:.3f} kg · '
            f'{product.material or "material unavailable"}</span></div>',
            unsafe_allow_html=True,
        )


def process_rows(dataset, product) -> list[dict[str, object]]:
    """Build an evidence-backed PLM process timeline for one product."""
    rows = [
        {
            "Stage": "Created in PLM export",
            "Status": "Verified",
            "Date / value": product.created_at.isoformat() if product.created_at else "Not available",
            "Evidence": product.source.label(),
        },
        {
            "Stage": "Product structure relationship",
            "Status": "Verified",
            "Date / value": f"{len(dataset.children(product.source.xml_id))} child relationship(s)",
            "Evidence": f"{len([line for line in dataset.bom_lines if line.parent_id == product.source.xml_id])} BOM line(s)",
        },
        {
            "Stage": "3D representation",
            "Status": "Available" if product.has_representation else "Not available",
            "Date / value": "Rep3DAggr linked" if product.has_representation else "No representation linked",
            "Evidence": product.source.label(),
        },
        {
            "Stage": "Maturity state",
            "Status": product.maturity,
            "Date / value": product.lifecycle,
            "Evidence": product.source.label(),
        },
        {
            "Stage": "Last modified",
            "Status": "Verified",
            "Date / value": product.modified_at.isoformat() if product.modified_at else "Not available",
            "Evidence": product.source.label(),
        },
    ]
    return rows


def process_page(dataset) -> None:
    st.title("PLM Process & Digital Thread")
    st.caption(
        "Trace the available lifecycle evidence for every part and assembly. "
        "This export does not contain manufacturing operations or quality workflow records."
    )
    products = list(dataset.products.values())
    c1, c2, c3 = st.columns(3)
    with c1:
        scope = st.selectbox("Scope", ["All products", "Assemblies only", "Parts only"])
    with c2:
        query = st.text_input("Search part or assembly", key="process_search")
    with c3:
        stage = st.selectbox("Focus stage", ["All stages", "Maturity state", "3D representation", "Product structure"])
    if scope == "Assemblies only":
        products = [p for p in products if not p.is_leaf]
    elif scope == "Parts only":
        products = [p for p in products if p.is_leaf]
    if query:
        q = query.lower()
        products = [p for p in products if q in p.name.lower() or q in p.plm_id.lower()]
    st.caption(f"{len(products)} product process records")
    if not products:
        st.info("No parts or assemblies match the current filters.")
        return
    labels = [label(p) for p in products]
    selected = products[labels.index(st.selectbox("Open process record", labels))]
    left, right = st.columns([1, 1.65])
    with left:
        st.markdown(product_svg(selected, len(dataset.children(selected.source.xml_id))), unsafe_allow_html=True)
        kpi("CURRENT MATURITY", selected.maturity, "Lifecycle state from XML", "warn")
        kpi("PROCESS EVIDENCE", "5 stages", "Available digital-thread checkpoints", "good")
    with right:
        panel_start("Engineering process timeline", f"{selected.name} · {selected.plm_id}")
        timeline = process_rows(dataset, selected)
        if stage != "All stages":
            timeline = [row for row in timeline if stage.lower().split()[0] in row["Stage"].lower()]
        st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
        panel_end()
    st.subheader("Process coverage across the product structure")
    process_summary = pd.DataFrame([
        {
            "Stage": "Created timestamp",
            "Covered": sum(bool(p.created_at) for p in products),
            "Total": len(products),
        },
        {
            "Stage": "Modified timestamp",
            "Covered": sum(bool(p.modified_at) for p in products),
            "Total": len(products),
        },
        {
            "Stage": "Maturity",
            "Covered": sum(bool(p.maturity) for p in products),
            "Total": len(products),
        },
        {
            "Stage": "Material",
            "Covered": sum(bool(p.material) for p in products),
            "Total": len(products),
        },
        {
            "Stage": "3D representation",
            "Covered": sum(p.has_representation for p in products),
            "Total": len(products),
        },
    ])
    process_summary["Coverage"] = process_summary["Covered"] / process_summary["Total"]
    st.dataframe(process_summary, hide_index=True, use_container_width=True)
    fig = px.bar(
        process_summary,
        x="Coverage",
        y="Stage",
        orientation="h",
        range_x=[0, 1],
        text=process_summary["Coverage"].map(lambda value: f"{value:.0%}"),
        color_discrete_sequence=["#0877b8"],
    )
    st.plotly_chart(plot_layout(fig, 280), use_container_width=True, config={"displayModeBar": False})
    st.info(
        "Process limitation: the XML header says WithProcess=Yes, but no process objects, "
        "operations, work centers, inspections or production events are included."
    )


def commercialization_page(dataset) -> None:
    """Show assembly integration and a safe commercial-data readiness model."""
    st.title("Parts, Assemblies & Commercialization")
    st.caption(
        "Explore what exists in the PLM export, how parts are assembled, and which "
        "commercial fields still require an enrichment source."
    )
    products = list(dataset.products.values())
    c1, c2, c3, c4 = st.columns(4)
    for col, args in zip((c1, c2, c3, c4), [
        ("REFERENCE ITEMS", str(len(products)), "PLM products in XML", "normal"),
        ("ASSEMBLIES", str(sum(not p.is_leaf for p in products)), "Parent products", "normal"),
        ("SELLABLE ITEMS", "N/A", "No sales classification in XML", "warn"),
        ("SALES DATA", "N/A", "No price or volume fields", "warn"),
    ]):
        with col:
            kpi(*args)

    st.warning(
        "Commercial limitation: the supplied XML contains engineering structure only. "
        "It does not identify sellable products, customers, prices, sales volume, suppliers, "
        "currency, lead time or revenue. The fields below are intentionally not invented."
    )
    tab_catalog, tab_assembly, tab_enrichment = st.tabs(
        ["Commercial catalog", "Assembly explosion", "Required commercial enrichment"]
    )
    with tab_catalog:
        query = st.text_input("Search part or assembly", key="commercial_search")
        kind = st.selectbox("Product class", ["All", "Parts", "Assemblies"], key="commercial_kind")
        visible = products
        if kind == "Parts":
            visible = [p for p in visible if p.is_leaf]
        elif kind == "Assemblies":
            visible = [p for p in visible if not p.is_leaf]
        if query:
            q = query.lower()
            visible = [
                p for p in visible
                if q in p.name.lower() or q in p.plm_id.lower() or q in (p.material or "").lower()
            ]
        st.caption(f"{len(visible)} engineering items found")
        if visible:
            st.dataframe(pd.DataFrame([
                {
                    "Engineering item": p.name,
                    "PLM ID": p.plm_id,
                    "Class": "Part" if p.is_leaf else "Assembly",
                    "Revision": p.revision,
                    "Maturity": p.maturity,
                    "Mass (kg)": p.mass_kg,
                    "Material": p.material or "Not available",
                    "Commercial status": "Not provided by XML",
                    "Sale price": "N/A",
                    "Sales volume": "N/A",
                }
                for p in visible
            ]), hide_index=True, use_container_width=True, height=520)
    with tab_assembly:
        assembly_options = [p for p in products if not p.is_leaf]
        selected = st.selectbox(
            "Select assembly to explode",
            assembly_options,
            format_func=lambda p: f"{p.name} · Rev {p.revision} · {p.mass_kg:.3f} kg",
            key="commercial_assembly",
        )
        left, right = st.columns([1, 1.55])
        with left:
            st.markdown(product_svg(selected, len(dataset.children(selected.source.xml_id))), unsafe_allow_html=True)
            kpi("ASSEMBLY MASS", f"{selected.mass_kg:.3f} kg", "XML mass value", "good")
            kpi("CHILD REFERENCES", str(len(dataset.children(selected.source.xml_id))), "Direct BOM relationships", "normal")
        with right:
            panel_start(
                "Assembly contents",
                "Parts and subassemblies linked by ProductInst; quantities are calculated from repeated references.",
            )
            children = dataset.children(selected.source.xml_id)
            st.dataframe(pd.DataFrame([
                {
                    "Component": child.name,
                    "PLM ID": child.plm_id,
                    "Class": "Part" if child.is_leaf else "Assembly",
                    "Quantity": dataset.quantity(selected.source.xml_id, child.source.xml_id),
                    "Unit mass (kg)": child.mass_kg,
                    "Extended mass (kg)": child.mass_kg * dataset.quantity(selected.source.xml_id, child.source.xml_id),
                    "Material": child.material or "Not available",
                }
                for child in children
            ]), hide_index=True, use_container_width=True)
            panel_end()
    with tab_enrichment:
        st.subheader("Commercial data model to add later")
        st.dataframe(pd.DataFrame([
            {"Field": "Sellable / internal classification", "Required for": "What is sold", "Current status": "Not in XML"},
            {"Field": "Customer / programme", "Required for": "Commercial ownership", "Current status": "Not in XML"},
            {"Field": "Sales price and currency", "Required for": "Price analysis", "Current status": "Not in XML"},
            {"Field": "Sales volume / forecast", "Required for": "Demand analysis", "Current status": "Not in XML"},
            {"Field": "Supplier and lead time", "Required for": "Sourcing impact", "Current status": "Not in XML"},
        ]), hide_index=True, use_container_width=True)
        st.info(
            "Recommended enrichment key: PLM ID. A separate CSV could contain "
            "plm_id, commercial_status, customer, unit_price, currency, sales_volume, "
            "supplier_id and lead_time_days. It must remain visibly separate from XML evidence."
        )
        st.code(
            "plm_id,commercial_status,customer,unit_price,currency,sales_volume,supplier_id,lead_time_days\n"
            "prd-12535825-00000047,internal_assembly,,,,,,",
            language="csv",
        )


def plot_layout(fig, height: int = 300):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#16324a", family="DM Sans"),
        title_font=dict(family="Space Grotesk", size=15),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#dce5ef", zeroline=False)
    return fig


def header(dataset) -> None:
    st.markdown(
        f'<div class="topbar"><div><div class="eyebrow">Engineering intelligence platform</div>'
        f'<h1>PLM INTELLIGENCE</h1><div style="color:#8fa4b8">Engineering Intelligence & Product Lifecycle Analytics</div></div>'
        f'<div style="text-align:right"><a class="github-link" href="{GITHUB_URL}" target="_blank" rel="noopener noreferrer">↗ GitHub Repository</a>'
        f'<a class="github-profile" href="{AUTHOR_GITHUB_URL}" target="_blank" rel="noopener noreferrer">◉ {AUTHOR_GITHUB_NAME}</a>'
        f'<div class="status" style="margin-top:.7rem">● DATASET VERIFIED</div>'
        f'<div style="color:#8fa4b8;font-size:.75rem;margin-top:.35rem">ECAR_PLM · {len(dataset.products)} products · XML source</div></div></div>',
        unsafe_allow_html=True,
    )


def sidebar(dataset) -> str:
    st.sidebar.markdown(
        '<div class="brand"><span class="brand-mark">P</span><span class="brand-name">PLM<br>INTELLIGENCE</span>'
        '<div class="brand-sub">Engineering Intelligence & Product Lifecycle Analytics</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("WORKSPACE")
    page = st.sidebar.radio(
        "Navigate",
        ["Executive Dashboard", "Product Explorer", "BOM Command Center", "Parts & Assemblies", "Parts & Commercialization", "PLM Process & Digital Thread", "Product Structure", "Product Intelligence",
         "Change Impact Analysis", "Revision & Lifecycle", "AI Engineering Assistant", "Data Sources"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    st.sidebar.markdown(f'<span class="status">● XML SOURCE ONLINE</span><br><span style="color:#8fa4b8;font-size:.72rem">{DATASET.name}</span>', unsafe_allow_html=True)
    if st.sidebar.button("↻ Reload dataset", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    return page


def overview(dataset) -> None:
    st.title("Executive Dashboard")
    st.caption("A verified view of the electric motor product structure, lifecycle state and engineering data quality.")
    stats = product_statistics(dataset)
    products = list(dataset.products.values())
    st.markdown("#### Data slicers")
    filter_left, filter_right = st.columns(2)
    material_filter = filter_left.selectbox(
        "Filter by material",
        ["All materials", "Missing / unassigned"] + sorted({p.material for p in products if p.material}),
        key="dashboard_material",
    )
    maturity_filter = filter_right.selectbox(
        "Filter by maturity state",
        ["All states"] + sorted({p.maturity for p in products}),
        key="dashboard_maturity",
    )
    filtered_products = products
    if material_filter == "Missing / unassigned":
        filtered_products = [p for p in filtered_products if not p.material]
    elif material_filter != "All materials":
        filtered_products = [p for p in filtered_products if p.material == material_filter]
    if maturity_filter != "All states":
        filtered_products = [p for p in filtered_products if p.maturity == maturity_filter]
    missing = sum(not p.material or not p.description for p in filtered_products)
    if len(filtered_products) != len(products):
        st.caption(f"Showing {len(filtered_products)} of {len(products)} reference products based on the active slicers.")
    cols = st.columns(4)
    for col, args in zip(cols, [
        ("TOTAL PRODUCTS", str(len(filtered_products)), "Reference objects in current view", "normal"),
        ("ASSEMBLIES", str(sum(not p.is_leaf for p in filtered_products)), "Parent products in current view", "normal"),
        ("COMPONENTS", str(sum(p.is_leaf for p in filtered_products)), "Leaf products in current view", "good"),
        ("ROOT MASS", f"{stats['root_mass_kg']:.3f} kg", "XML mass value", "good"),
    ]):
        with col: kpi(*args)
    st.write("")
    hero_left, hero_right = st.columns([1.55, 1])
    with hero_left:
        panel_start("Product command center", "Root product and major system boundaries from the imported BOM")
        st.markdown(product_svg(dataset.root, len(dataset.children(dataset.root.source.xml_id))), unsafe_allow_html=True)
        major = [
            p for p in dataset.children(dataset.root.source.xml_id)
            if not p.is_leaf
        ]
        if major:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Major assembly": p.name.replace("ECAR-EI_", ""),
                        "Revision": p.revision,
                        "Mass (kg)": p.mass_kg,
                        "Children": len(dataset.children(p.source.xml_id)),
                        "Maturity": p.maturity,
                    }
                    for p in major
                ]),
                hide_index=True,
                use_container_width=True,
            )
        panel_end()
    with hero_right:
        panel_start("Engineering signal center", "Deterministic signals generated from the XML snapshot")
        signal_rows = [
            ("Lifecycle coverage", f"{sum(p.maturity == 'IN_WORK' for p in filtered_products)}/{len(filtered_products)} products IN_WORK", "warn"),
            ("Material coverage", f"{sum(bool(p.material) for p in filtered_products)}/{len(filtered_products)} products", "good"),
            ("Mass validation", "All assembly roll-ups match" if not dataset.warnings else f"{len(dataset.warnings)} mismatch(es)", "good" if not dataset.warnings else "risk"),
            ("Revision history", "Not available in this export", "warn"),
            ("Supplier / cost", "Not present in XML", "warn"),
        ]
        for title, detail, tone in signal_rows:
            tag = "tag-green" if tone == "good" else "tag-red" if tone == "risk" else "tag-amber"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:.72rem 0;border-bottom:1px solid #213952">'
                f'<span style="font-size:.82rem">{title}<br><span style="color:#8fa4b8;font-size:.72rem">{detail}</span></span>'
                f'<span class="tag {tag}">{"VERIFIED" if tone == "good" else "LIMITATION"}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="evidence" style="margin-top:1rem">Every signal is either an XML fact, a calculated relationship, or an explicitly stated data limitation.</div>', unsafe_allow_html=True)
        panel_end()
    cols = st.columns(4)
    for col, args in zip(cols, [
        ("UNIQUE REVISIONS", str(len({p.revision for p in filtered_products})), "Revision labels in current view", "normal"),
        ("MATERIAL COVERAGE", f"{sum(bool(p.material) for p in filtered_products)/len(filtered_products):.0%}" if filtered_products else "0%", "Current filtered view", "good"),
        ("DATA QUALITY FLAGS", str(missing), "Missing material or description", "warn"),
        ("MATURITY STATE", "IN_WORK", "79 of 79 products", "warn"),
    ]):
        with col: kpi(*args)
    left, right = st.columns([1.25, 1])
    with left:
        panel_start("Product structure overview", "Reference objects by engineering role")
        fig = px.pie(names=["Assemblies", "Leaf components"], values=[sum(not p.is_leaf for p in filtered_products), sum(p.is_leaf for p in filtered_products)], hole=.66, color_discrete_sequence=["#0877b8", "#42b5e8"])
        fig.update_traces(textinfo="label+value")
        st.plotly_chart(plot_layout(fig, 320), use_container_width=True, config={"displayModeBar": False})
        panel_end()
    with right:
        panel_start("Revision distribution", "Directly read from Product/RevisionName")
        revisions = pd.Series([p.revision for p in filtered_products]).value_counts().sort_index()
        fig = px.bar(x=revisions.index, y=revisions.values, labels={"x": "Revision", "y": "Products"}, color_discrete_sequence=["#0877b8"])
        st.plotly_chart(plot_layout(fig, 320), use_container_width=True, config={"displayModeBar": False})
        panel_end()
    left, right = st.columns([1.25, 1])
    with left:
        panel_start("Mass by major assembly", "XML mass values; no fabricated telemetry")
        assemblies = [p for p in filtered_products if not p.is_leaf and p.source.xml_id != dataset.root.source.xml_id]
        data = pd.DataFrame({"Assembly": [p.name.replace("ECAR-EI_", "") for p in assemblies], "Mass (kg)": [p.mass_kg for p in assemblies]})
        fig = px.bar(data.sort_values("Mass (kg)"), x="Mass (kg)", y="Assembly", orientation="h", color_discrete_sequence=["#4b8bff"])
        st.plotly_chart(plot_layout(fig, 330), use_container_width=True, config={"displayModeBar": False})
        panel_end()
    with right:
        panel_start("Lifecycle / maturity", "All values are sourced from the XML extract")
        maturity = pd.Series([p.maturity for p in filtered_products]).value_counts()
        fig = px.bar(x=maturity.index, y=maturity.values, labels={"x": "Maturity", "y": "Products"}, color_discrete_sequence=["#e89500"])
        st.plotly_chart(plot_layout(fig, 330), use_container_width=True, config={"displayModeBar": False})
        panel_end()
    st.subheader("Assembly intelligence")
    st.caption("Select a major assembly to inspect its visual aid, mass, material coverage and immediate dependencies.")
    major_options = [
        p for p in dataset.children(dataset.root.source.xml_id)
        if not p.is_leaf
    ]
    if major_options:
        chosen = st.selectbox("Major assembly", major_options, format_func=lambda p: p.name)
        c1, c2, c3 = st.columns([1, 1, 1.3])
        with c1:
            st.markdown(product_svg(chosen, len(dataset.children(chosen.source.xml_id))), unsafe_allow_html=True)
        with c2:
            kpi("ASSEMBLY MASS", f"{chosen.mass_kg:.3f} kg", "Source XML mass", "good")
            kpi("DIRECT CHILDREN", str(len(dataset.children(chosen.source.xml_id))), "Calculated BOM relationships", "normal")
        with c3:
            child_materials = [p.material for p in dataset.children(chosen.source.xml_id) if p.material]
            mat_counts = pd.Series(child_materials).value_counts().head(8)
            fig = px.bar(x=mat_counts.values, y=mat_counts.index, orientation="h", labels={"x": "Products", "y": "Material"}, color_discrete_sequence=["#35d5e8"])
            st.plotly_chart(plot_layout(fig, 270), use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="evidence">Source of truth: XPDMXML_ECAR_PLM.xml · Root: ECAR-EI_410KW_EDRIVE_FRONT · Export completion: Expand=-1</div>', unsafe_allow_html=True)


def explorer(dataset, structure_only: bool = False) -> None:
    st.title("Product Structure" if structure_only else "Product Explorer")
    st.caption("Navigate the reference/instance model with source identifiers and engineering properties.")
    query = st.text_input("⌕ Search product name or PLM identifier", key="explorer_search")
    c1, c2, c3 = st.columns(3)
    revision = c1.selectbox("Revision", ["All"] + sorted({p.revision for p in dataset.products.values()}))
    maturity = c2.selectbox("Maturity", ["All"] + sorted({p.maturity for p in dataset.products.values()}))
    kind = c3.selectbox("Product type", ["All", "Assembly", "Wrapper", "Part"])
    matches = search_products(dataset, query, maturity)
    if revision != "All": matches = [p for p in matches if p.revision == revision]
    if kind != "All": matches = [p for p in matches if p.item_kind.title() == kind]
    if structure_only:
        st.info("Quantities are calculated by counting repeated ProductInst parent-child relationships.")
    st.caption(f"{len(matches)} matching products")
    if not matches: st.info("No products match the current filters."); return
    selected = {label(p): p for p in matches}[st.selectbox("Select product", [label(p) for p in matches])]
    left, right = st.columns([1, 1.35])
    with left:
        st.markdown(product_svg(selected, len(dataset.children(selected.source.xml_id))), unsafe_allow_html=True)
        st.markdown(f'<span class="tag">{selected.item_kind.upper()}</span><span class="tag tag-green">{selected.maturity}</span><span class="tag">REV {selected.revision}</span>', unsafe_allow_html=True)
    with right:
        st.subheader(selected.name)
        st.caption(f"{selected.plm_id} · {selected.source.label()}")
        details = pd.DataFrame([
            ["Mass", f"{selected.mass_kg:.3f} kg"], ["Material", selected.material or "Not available"],
            ["Lifecycle", selected.lifecycle], ["Description", selected.description or "Not available"],
            ["XID", selected.xid], ["3D representation", "Available" if selected.has_representation else "Not available"],
        ], columns=["Engineering property", "Value"])
        st.dataframe(details, hide_index=True, use_container_width=True)
    children = dataset.children(selected.source.xml_id)
    parents = dataset.parents(selected.source.xml_id)
    c1, c2 = st.columns(2)
    with c1:
        panel_start("Child products", "Direct BOM relationships")
        st.dataframe(pd.DataFrame([{"Product": p.name, "Revision": p.revision, "Qty": dataset.quantity(selected.source.xml_id, p.source.xml_id)} for p in children]), hide_index=True, use_container_width=True)
        panel_end()
    with c2:
        panel_start("Where used", "Direct parent products")
        st.dataframe(pd.DataFrame([{"Product": p.name, "PLM ID": p.plm_id} for p in parents]), hide_index=True, use_container_width=True)
        panel_end()


def bom_command_center(dataset) -> None:
    st.title("BOM Command Center")
    st.caption("A complete assembly-to-part view of the electric motor product structure.")
    rows = bom_rows(dataset)
    assemblies = sum(row["Type"] in {"Assembly", "Wrapper"} for row in rows)
    parts = sum(row["Type"] == "Part" for row in rows)
    c1, c2, c3, c4 = st.columns(4)
    for col, args in zip((c1, c2, c3, c4), [
        ("BOM NODES", str(len(rows)), "Expanded occurrence paths", "normal"),
        ("ASSEMBLY NODES", str(assemblies), "Assemblies and wrappers", "normal"),
        ("PART NODES", str(parts), "Leaf components", "good"),
        ("RELATIONSHIPS", str(len(dataset.bom_lines)), "Aggregated BOM lines", "normal"),
    ]):
        with col:
            kpi(*args)

    view = st.radio("View mode", ["Hierarchy", "BOM Register", "Structure Map"], horizontal=True)
    if view == "Hierarchy":
        panel_start("Expanded product hierarchy", "Assemblies and parts are shown as a safe, traceable indented BOM.")
        hierarchy_node(dataset, dataset.root.source.xml_id)
        panel_end()
    elif view == "BOM Register":
        query = st.text_input("Filter BOM by product name, PLM ID or material", key="bom_filter")
        filtered = [row for row in rows if not query or query.lower() in " ".join(str(value).lower() for value in row.values())]
        st.caption(f"{len(filtered)} of {len(rows)} expanded BOM rows")
        st.dataframe(pd.DataFrame(filtered), hide_index=True, use_container_width=True, height=610)
    else:
        panel_start("Structure map", "Calculated relationship map; repeated references remain linked by their PLM identifiers.")
        products = list(dataset.products.values())
        ids = [p.source.xml_id for p in products]
        labels = [p.name for p in products]
        parent_map = {p.source.xml_id: "" for p in products}
        for line in dataset.bom_lines:
            if not parent_map[line.child_id]:
                parent_map[line.child_id] = line.parent_id
        fig = go.Figure()
        for line in dataset.bom_lines:
            parent = dataset.products[line.parent_id]
            child = dataset.products[line.child_id]
            fig.add_trace(go.Scatter(
                x=[parent.mass_kg, child.mass_kg], y=[parent.name, child.name],
                mode="lines", line=dict(color="#213952", width=1), hoverinfo="skip", showlegend=False,
            ))
        fig.add_trace(go.Scatter(
            x=[p.mass_kg for p in products], y=[p.name for p in products],
            mode="markers", marker=dict(
                size=[15 if not p.is_leaf else 9 for p in products],
                color=["#35d5e8" if not p.is_leaf else "#4b8bff" for p in products],
                line=dict(color="#e8f0f7", width=.4),
            ),
            text=[f"{p.name}<br>{p.plm_id}<br>Rev {p.revision}" for p in products],
            hovertemplate="%{text}<extra></extra>", showlegend=False,
        ))
        fig.update_layout(yaxis=dict(autorange="reversed", showticklabels=False), xaxis_title="Mass (kg)")
        st.plotly_chart(plot_layout(fig, 720), use_container_width=True, config={"displayModeBar": False})
        panel_end()


def parts_and_assemblies(dataset) -> None:
    st.title("Parts & Assemblies")
    st.caption("Engineering catalog with a dedicated view for reference products and their occurrences.")
    products = list(dataset.products.values())
    kind = st.radio("Catalog", ["All", "Assemblies", "Parts"], horizontal=True)
    query = st.text_input("Search catalog", key="catalog_search")
    if kind == "Assemblies":
        products = [p for p in products if not p.is_leaf]
    elif kind == "Parts":
        products = [p for p in products if p.is_leaf]
    if query:
        query = query.lower()
        products = [p for p in products if query in p.name.lower() or query in p.plm_id.lower() or query in (p.material or "").lower()]
    st.caption(f"{len(products)} reference products")
    if not products:
        st.info("No products match the catalog filters.")
        return
    selected = {label(p): p for p in products}[st.selectbox("Open engineering record", [label(p) for p in products])]
    left, right = st.columns([.9, 1.5])
    with left:
        st.markdown(product_svg(selected, len(dataset.children(selected.source.xml_id))), unsafe_allow_html=True)
        st.markdown(
            f'<span class="tag {"tag-green" if selected.is_leaf else ""}">{"PART" if selected.is_leaf else "ASSEMBLY"}</span>'
            f'<span class="tag">REV {selected.revision}</span><span class="tag">{selected.maturity}</span>',
            unsafe_allow_html=True,
        )
    with right:
        st.subheader(selected.name)
        st.caption(f"{selected.plm_id} · XML source {selected.source.xml_id}")
        details = pd.DataFrame([
            ["PLM identifier", selected.plm_id],
            ["Revision / index", f"{selected.revision} / {selected.revision_index}"],
            ["Mass", f"{selected.mass_kg:.3f} kg"],
            ["Material", selected.material or "Not available"],
            ["Direct children", len(dataset.children(selected.source.xml_id))],
            ["Used by", len(dataset.parents(selected.source.xml_id))],
            ["3D representation", "Available" if selected.has_representation else "Not available"],
        ], columns=["Property", "Value"])
        st.dataframe(details, hide_index=True, use_container_width=True)
    children = dataset.children(selected.source.xml_id)
    if children:
        panel_start("Assembly contents", "Direct child references and calculated quantities")
        st.dataframe(pd.DataFrame([
            {
                "Part / subassembly": child.name,
                "Type": child.item_kind.title(),
                "PLM ID": child.plm_id,
                "Qty": dataset.quantity(selected.source.xml_id, child.source.xml_id),
                "Mass (kg)": child.mass_kg,
                "Material": child.material or "Not available",
            } for child in children
        ]), hide_index=True, use_container_width=True)
        panel_end()
    else:
        panel_start("Part usage", "Assemblies that reference this leaf component")
        st.dataframe(pd.DataFrame([{"Assembly": p.name, "PLM ID": p.plm_id, "Qty": dataset.quantity(p.source.xml_id, selected.source.xml_id)} for p in dataset.parents(selected.source.xml_id)]), hide_index=True, use_container_width=True)
        panel_end()


def intelligence(dataset) -> None:
    st.title("Product Intelligence")
    st.caption("Evidence-based engineering observations, calculated metrics and data-quality signals.")
    insights = risk_insights(dataset)
    for insight in insights:
        tone = "tag-red" if insight.severity == "high" else "tag-amber" if insight.severity == "medium" else ""
        st.markdown(f'<div class="panel"><span class="tag {tone}">{insight.severity.upper()}</span><b>{insight.title}</b><p>{insight.detail}</p><div class="evidence">Evidence: {insight.sources[0].label() if insight.sources else "Calculated from dataset"}</div></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        panel_start("Material composition", "Products with a material value in the export")
        st.dataframe(pd.DataFrame(material_summary(dataset)), hide_index=True, use_container_width=True)
        panel_end()
    with right:
        panel_start("Data completeness", "Missing values are not silently replaced")
        products = list(dataset.products.values())
        completeness = pd.DataFrame({"Field": ["Material", "Description", "Mass", "Maturity"], "Complete": [sum(bool(p.material) for p in products), sum(bool(p.description) for p in products), len(products), sum(bool(p.maturity) for p in products)]})
        fig = px.bar(completeness, x="Complete", y="Field", orientation="h", range_x=[0, len(products)], color_discrete_sequence=["#41d3a2"])
        st.plotly_chart(plot_layout(fig, 270), use_container_width=True, config={"displayModeBar": False})
        panel_end()


def impact(dataset) -> None:
    st.title("Change Impact Analysis")
    st.caption("Trace parent dependencies before proposing a component change.")
    options = {label(p): p for p in dataset.products.values()}
    selected = options[st.selectbox("Select component or assembly", list(options))]
    result = impact_summary(dataset, selected.source.xml_id)
    left, right = st.columns([1, 1.35])
    with left:
        st.markdown(product_svg(selected), unsafe_allow_html=True)
        kpi("AFFECTED PARENTS", str(result["affected_count"]), "Calculated graph ancestors", "warn" if result["affected_count"] else "good")
    with right:
        panel_start("Impact chain", "Parent assemblies reached through ProductInst relationships")
        st.dataframe(pd.DataFrame([{"Product": i.product.name, "PLM ID": i.product.plm_id, "Level": i.distance, "Evidence": i.relationship_sources[0].label() if i.relationship_sources else ""} for i in result["affected"]]), hide_index=True, use_container_width=True)
        panel_end()
    st.subheader("Dependency graph")
    nodes = [selected] + [item.product for item in result["affected"]]
    fig = go.Figure()
    for index, product in enumerate(nodes):
        fig.add_trace(go.Scatter(x=[index], y=[0], mode="markers+text", text=[product.name[:24]], textposition="bottom center", marker=dict(size=30, color="#35d5e8" if index == 0 else "#4b8bff"), hovertext=[product.plm_id], hoverinfo="text", showlegend=False))
        if index:
            fig.add_shape(type="line", x0=index-1, y0=0, x1=index, y1=0, line=dict(color="#35d5e8", width=2))
    st.plotly_chart(plot_layout(fig, 250), use_container_width=True, config={"displayModeBar": False})
    c1, c2 = st.columns(2)
    proposed_mass = c1.number_input("Proposed mass (kg), 0 = not supplied", min_value=0.0, value=0.0)
    proposed_material = c2.text_input("Proposed material, blank = not supplied")
    comparison = replacement_comparison(selected, proposed_mass or None, proposed_material or None)
    if comparison: st.dataframe(pd.DataFrame(comparison), hide_index=True, use_container_width=True)
    st.warning("Data not available: supplier, cost, currency, lead time and requalification estimates are not present in the XML.")


def revisions(dataset) -> None:
    st.title("Revision & Lifecycle Tracking")
    st.caption("Current revision state from the single supplied export.")
    products = list(dataset.products.values())
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(pd.DataFrame({"Revision": [p.revision for p in products]}), x="Revision", category_orders={"Revision": ["A", "B", "C", "D"]}, color_discrete_sequence=["#35d5e8"])
        st.plotly_chart(plot_layout(fig, 300), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.dataframe(product_rows(dataset)[["Product", "PLM ID", "Revision", "Maturity"]].sort_values(["Revision", "Product"]), hide_index=True, use_container_width=True, height=300)
    st.info("Historical revision comparison is unavailable: the extract contains one distinct RevisionFamily per product, not multiple revisions of the same item.")


def assistant(dataset) -> None:
    st.title("AI Engineering Assistant")
    st.caption("Dataset-grounded mode · no external AI API required")
    suggestions = ["What are the main assemblies?", "Which products are IN_WORK?", "What is the mass of the root product?", "What are the costs?"]
    st.write("Suggested questions")
    for suggestion in suggestions:
        if st.button(suggestion, key=suggestion):
            st.session_state["question"] = suggestion
    question = st.text_area("Ask about the loaded PLM data", value=st.session_state.get("question", ""), placeholder="Which assemblies depend on ECAR-EI_Screw D10 L155?")
    if st.button("Run analysis", type="primary") and question:
        st.markdown(f'<div class="panel"><div class="panel-title">Answer</div><div class="panel-caption">Computed from the local XML model</div>{answer_question(dataset, question)}</div>', unsafe_allow_html=True)


def sources(dataset) -> None:
    st.title("Data Sources & Import")
    st.caption("The dashboard is intentionally not factory telemetry. It reflects the imported XML snapshot.")
    st.markdown(f'<div class="panel"><div class="panel-title">Primary source</div><p>{DATASET.name}</p><div class="evidence">Path: {dataset.source_path}<br>Schema: XPDMXML {dataset.export_info.values.get("CompletionType", "unknown")}<br>Objects: {len(dataset.products)} Products · {len(dataset.instances)} ProductInst · {len(dataset.representations)} Rep3DAggr</div></div>', unsafe_allow_html=True)
    st.subheader("Unavailable source domains")
    st.dataframe(pd.DataFrame({"Domain": ["Supplier", "Cost", "Lead time", "Quality records", "CAD geometry", "Revision history"], "Status": ["Not in XML"] * 6, "Required addition": ["Enrichment file"] * 4 + ["3D export", "Additional PLM exports"]}), hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="PLM Intelligence", page_icon="⚙", layout="wide", initial_sidebar_state="expanded")
    load_css()
    try:
        signature = DATASET.stat().st_mtime_ns
        dataset = get_dataset(signature)
    except (OSError, XMLParseError) as exc:
        st.error(f"Could not load the PLM XML: {exc}")
        st.stop()
    page = sidebar(dataset)
    header(dataset)
    if page == "Executive Dashboard": overview(dataset)
    elif page == "Product Explorer": explorer(dataset)
    elif page == "BOM Command Center": bom_command_center(dataset)
    elif page == "Parts & Assemblies": parts_and_assemblies(dataset)
    elif page == "Parts & Commercialization": commercialization_page(dataset)
    elif page == "PLM Process & Digital Thread": process_page(dataset)
    elif page == "Product Structure": explorer(dataset, True)
    elif page == "Product Intelligence": intelligence(dataset)
    elif page == "Change Impact Analysis": impact(dataset)
    elif page == "Revision & Lifecycle": revisions(dataset)
    elif page == "AI Engineering Assistant": assistant(dataset)
    else: sources(dataset)


if __name__ == "__main__":
    main()
