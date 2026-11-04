# OEM XML extract: structure analysis

[Version française](xml_structure_fr.md)

First-pass analysis of `data/raw/XPDMXML_ECAR_PLM.xml` (4,411 lines, 215 KB). It describes what the file contains, how objects relate to each other, which attributes are usable for the three app capabilities, and what is missing or inconsistent.

## Format

The file is an XPDMXML export (schema version 2, namespace `http://www.3ds.com/xsd/XPDMXML`) produced by 3DEXPERIENCE. The `InfoHeader` shows a full expansion (`CompletionType = Expand=-1`) from a single root, `ECAR-EI_410KW_EDRIVE_FRONT`, with no files, documents or PLM parameters exported (`WithFiles`, `WithDocuments`, `WithPLMParams` all set to `No`).

All objects sit flat under `ProductStructure` and reference each other through their local `id` attribute (`ID_0`, `ID_1`, ...). The root is declared in `ProductStructure/@rootRefs="ID_0"`.

| Element | Count | Role | Key fields |
|---|---|---|---|
| `Product` | 79 | Reference (part or assembly) | `ID`, `Name`, `Description`, `RevisionName`, `RevisionIndex`, `RevisionFamily`, `Maturity`, `Lifecycle`, `Material`, `WCGEquivalentComputedExt.V_WCG_Mass` |
| `ProductInst` | 112 | Parent-to-child link (occurrence) | `Owned` (parent product id), `Instancing` (child product id), `ChildOrder`, `RelativeTransformation3D` (`Rotation3D`, `Translation3D`) |
| `Rep3DAggr` | 36 | 3D representation, no geometry file attached | `Owned` (product id), `RevisionName`, `Maturity` |

Fields shared by every object: `ID`, `Name`, `Description`, `UniqueID`, `RevisionFamily`, `TimeCreated`, `TimeModified`, `Owner`, `Organization`, `Project`, `SecurityLevel`.

### Identifiers

Each object carries three identifiers:

| Identifier | Example | Use |
|---|---|---|
| `@id` | `ID_0` | Local key, used by `Owned`, `Instancing` and `rootRefs`. Only valid inside this file. |
| `ID` | `prd-12535825-00000047` (products), `3sh-12535825-00000003` (3D reps) | Business identifier, unique across the 79 products. |
| `UniqueID/@XID` | `05C78E12D8C63ED9010179C96BD0AE790102170A` | 3DEXPERIENCE physical id, stable outside the export. |

For traceability, the data model should keep at least `@id` and `XID` on every object. Keeping the source line number as well makes "show me the XML" trivial in the UI.

`Name` is not unique and must not be used as a key (see [Pitfalls](#pitfalls)).

## Product structure

The tree has a single root, 4 levels below it, and 144 occurrences once fully expanded. Total mass is 100.1 kg, split across three major subassemblies:

| Subassembly | Mass (kg) | Content |
|---|---|---|
| `ECAR-EI_EMOTOR FRONT` | 39.73 | Stator (core, coils), high-speed shaft and its bearing, machine cooling |
| `ECAR-EI_REDUCER FRONT` | 29.85 | Differential assembly, 4 gear wheels, intermediate shaft, 6 bearings |
| `ECAR-EI_HOUSING FRONT EDRIVE` | 30.52 | Left and right housings, bearing housing, transmission support, joint, pipes, around 40 screws |

### EI / 3D pattern

The modelling follows a strict convention:

- The 43 `ECAR-EI_*` products are logical items (engineering items). They are all assemblies.
- The 36 `ECAR-3D_*` products are the leaves. Each one owns exactly one `Rep3DAggr`, and no assembly owns one.

37 of the 43 EI products contain a single 3D child and act as wrappers around it, with the same mass and material. The six real assemblies are the root, `EMOTOR FRONT`, `STATOR`, `REDUCER FRONT`, `DIFFERENTIAL_ASSEMBLY` and `HOUSING FRONT EDRIVE`. The UI can merge each EI/3D pair into a single component without losing information.

### Quantities and reuse

There is no quantity field. A quantity is the number of `ProductInst` elements sharing the same (`Owned`, `Instancing`) pair. Products instanced more than once:

| Product | Quantity | Parent |
|---|---|---|
| `ECAR-EI_Screw D10 L155` | 14 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_Screw D8 L50` | 13 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_Screw D10 L115` | 4 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_MOTOR SCREW 1` | 3 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_90 degrees pipe` | 2 | `HOUSING FRONT EDRIVE` |
| `ECAR-3D_MOTOR SCREW 2` | 2 | `HOUSING FRONT EDRIVE` |
| `ECAR-3D_DifferentialSideShaft` | 2 | `DIFFERENTIAL SIDE SHAFT LEFT` and `RIGHT` (one each) |
| `ECAR-3D_DifferentialBevelGearTM_Bevel` | 2 | the two `DIFFERENTIAL BEVEL GEAR TM BEVEL` EIs (one each) |

The last two rows matter for change impact: replacing one of those 3D parts affects two distinct EI items.

### Mass roll-up

`V_WCG_Mass` is a computed field and it rolls up exactly. For each of the 43 assemblies, its mass equals the sum of its children's masses, quantities included, with zero mismatches. This makes a good validation test for the parser: if the rebuilt tree does not reproduce 100.1 kg at the root, something is wrong.

`ChildOrder` gives the display order of children. `RelativeTransformation3D` gives each instance's position relative to its parent (76 of 112 instances have a non-identity rotation), which could feed a spatial view if needed.

## Usable attributes

### Material

Material is filled in on every leaf and on every EI wrapper (always identical to its 3D child). It is empty only on the six real assemblies. 14 distinct materials appear on the 36 leaves:

| Material | Leaves |
|---|---|
| Case-hardening steel 20MnCr5 | 7 |
| Bearing steel 100Cr6 (AISI 52100) | 7 |
| Steel class 10.9 (zinc-flake coated) | 6 |
| Aluminium alloy EN AC-AlSi9Cu3(Fe) (HPDC) | 4 |
| Electrical steel M235-35A (laminated) | 2 |
| Copper Cu-ETP (enamelled wire) | 2 |
| Aluminium alloy EN AC-AlSi10Mg (cast) | 1 |
| Aluminium alloy EN AW-6082-T6 | 1 |
| Polyamide PA66-GF30 | 1 |
| Alloy steel 42CrMo4 (quenched and tempered) | 1 |
| Structural steel S355J2 | 1 |
| FKM fluoroelastomer (steel-reinforced) | 1 |
| Case-hardening steel 16MnCr5 | 1 |
| Ductile cast iron EN-GJS-600-3 | 1 |

Combined with mass, this is the strongest basis for a sustainability indicator (for example embodied CO2 per material), provided emission factors are brought in from an external, cited source.

### Revisions

`RevisionName` ranges from A to D (41 A, 23 B, 11 C, 4 D), with `RevisionIndex` matching (1 to 4).

## Gaps

These gaps directly constrain what the app can show while staying traceable to the XML.

- **No supplier, cost, make/buy, lead time or criticality data.** None of these fields exist. Supplier dependency analysis and cost impact in Change Impact Analysis need an enrichment file, clearly labelled as a non-PLM source in the UI.
- **No version history.** All 79 products have distinct `RevisionFamily` values, so no part appears in two revisions. The app can show the current revision of each part, but cannot compare two versions of the same part from this extract alone.
- **Uniform lifecycle.** All 79 products and 36 representations are `IN_WORK`, all on the `VPLM_SMB_Definition_MajorRev` lifecycle. Maturity alone does not separate one part from another for risk.
- **Generic metadata.** `Owner` is always `admin_platform`, `Organization` is always `Company Name`, `Project` is always `ECAR_PLM`. Every `TimeCreated` falls between 16:29:23 and 16:29:25 on 2026-10-14, and every `TimeModified` is 16:29:32 that same day. These are export timestamps, not design history.
- **Few descriptions.** Only 3 products have one (`High Speed Shaft`, `Full 3D 360deg Stator Core`, `This is only a single Tooth -> required for meshing`). No `ProductInst` has a `Name`; their `ID` follows the `<reference name>.<n>` pattern (`EI_HSH.1`, `EI_EMOTOR FRONT.2`).

## Pitfalls

- **`GEAR_WHEEL` names.** `ECAR-EI_GEAR_WHEEL` appears four times, in revisions A, B, C and D, each wrapping an `ECAR-3D_GearWheel`. These are not four versions of one part but four different gear wheels (1.3, 1.6, 3.9 and 7.4 kg, distinct `RevisionFamily`). Grouping by name would wrongly merge them.

| `@id` | `ID` | Name | Rev | Mass (kg) |
|---|---|---|---|---|
| `ID_41` | `prd-12535825-00000062` | `ECAR-EI_GEAR_WHEEL` | A | 1.3 |
| `ID_45` | `prd-12535825-00000064` | `ECAR-EI_GEAR_WHEEL` | B | 1.6 |
| `ID_43` | `prd-12535825-00000063` | `ECAR-EI_GEAR_WHEEL` | C | 3.9 |
| `ID_47` | `prd-12535825-00000065` | `ECAR-EI_GEAR_WHEEL` | D | 7.4 |

- **Missing EI wrapper.** `ECAR-3D_MOTOR SCREW 2` is instanced twice directly under `HOUSING FRONT EDRIVE`, with no EI wrapper, unlike every other part. Any code that assumes "assembly → EI → 3D" must handle this case.
- **Probable mass double count in the stator.** `ECAR-EI_STATOR` contains a full core (`STATOR Core`, 21.5 kg) and full coils (`STATOR Coils`, 7.2 kg), plus a single tooth (0.12 kg) and a single coil (0.16 kg) modelled for meshing. The single tooth and coil are counted in the stator mass (28.98 kg), which likely overstates it by 0.28 kg. Worth flagging as a data quality finding in the demo.
- **Inconsistent naming.** Some names have a leading space after the prefix (`ECAR-EI_ MACHINE COOLING`, `ECAR-EI_ DIFFERENTIAL BEVEL GEAR TM BEVEL`) and some use a space instead of an underscore (`ECAR-3D Stator Core`, `ECAR-3D Screw D10 L155`). The two bevel gear EIs differ only by that leading space. Name-based search should normalise whitespace.
- **Header mismatch.** The header declares `WithProcess=Yes`, but the file contains no process objects.

## Implications for the parser

- Index every element by `@id` in a first pass, then resolve `Owned`, `Instancing` and `rootRefs`.
- Model the structure as a graph: `Product` as nodes, `ProductInst` as edges, aggregating quantities per (parent, child) pair while keeping the list of instance ids for traceability.
- Attach each `Rep3DAggr` to its owning product.
- Store a source reference (`@id`, `XID`, line number) on every node and edge.
- Validate on load: one root, no dangling references, mass roll-up equal to 100.1 kg at the root.
