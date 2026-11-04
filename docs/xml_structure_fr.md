# Extrait XML de l'OEM : analyse de la structure

[English version](xml_structure.md)

Première analyse de `data/raw/XPDMXML_ECAR_PLM.xml` (4 411 lignes, 215 Ko). Ce document décrit le contenu du fichier, les liens entre objets, les attributs utilisables pour les trois capacités de l'application, ainsi que ce qui manque ou pose problème.

## Format

Le fichier est un export XPDMXML (version de schéma 2, namespace `http://www.3ds.com/xsd/XPDMXML`) produit par 3DEXPERIENCE. L'`InfoHeader` indique une expansion complète (`CompletionType = Expand=-1`) depuis une racine unique, `ECAR-EI_410KW_EDRIVE_FRONT`, sans fichiers, documents ni paramètres PLM exportés (`WithFiles`, `WithDocuments` et `WithPLMParams` à `No`).

Tous les objets sont à plat sous `ProductStructure` et se référencent par leur attribut local `id` (`ID_0`, `ID_1`…). La racine est déclarée dans `ProductStructure/@rootRefs="ID_0"`.

| Élément | Nombre | Rôle | Champs clés |
|---|---|---|---|
| `Product` | 79 | Référence (pièce ou assemblage) | `ID`, `Name`, `Description`, `RevisionName`, `RevisionIndex`, `RevisionFamily`, `Maturity`, `Lifecycle`, `Material`, `WCGEquivalentComputedExt.V_WCG_Mass` |
| `ProductInst` | 112 | Lien parent → enfant (occurrence) | `Owned` (id du parent), `Instancing` (id de l'enfant), `ChildOrder`, `RelativeTransformation3D` (`Rotation3D`, `Translation3D`) |
| `Rep3DAggr` | 36 | Représentation 3D, sans fichier de géométrie | `Owned` (id du product), `RevisionName`, `Maturity` |

Champs communs à tous les objets : `ID`, `Name`, `Description`, `UniqueID`, `RevisionFamily`, `TimeCreated`, `TimeModified`, `Owner`, `Organization`, `Project`, `SecurityLevel`.

### Identifiants

Chaque objet porte trois identifiants :

| Identifiant | Exemple | Usage |
|---|---|---|
| `@id` | `ID_0` | Clé locale, utilisée par `Owned`, `Instancing` et `rootRefs`. Valable uniquement dans ce fichier. |
| `ID` | `prd-12535825-00000047` (products), `3sh-12535825-00000003` (représentations 3D) | Identifiant métier, unique sur les 79 products. |
| `UniqueID/@XID` | `05C78E12D8C63ED9010179C96BD0AE790102170A` | Identifiant physique 3DEXPERIENCE, stable en dehors de l'export. |

Pour la traçabilité, le modèle de données doit conserver au minimum `@id` et `XID` sur chaque objet. Garder aussi le numéro de ligne source permet d'afficher facilement l'élément XML d'origine dans l'interface.

`Name` n'est pas unique et ne doit pas servir de clé (voir [Pièges](#pièges)).

## Structure produit

L'arbre a une racine unique, 4 niveaux en dessous et 144 occurrences une fois entièrement déplié. La masse totale est de 100,1 kg, répartie entre trois sous-ensembles majeurs :

| Sous-ensemble | Masse (kg) | Contenu |
|---|---|---|
| `ECAR-EI_EMOTOR FRONT` | 39,73 | Stator (noyau, bobinage), arbre haute vitesse et son roulement, refroidissement machine |
| `ECAR-EI_REDUCER FRONT` | 29,85 | Différentiel, 4 roues dentées, arbre intermédiaire, 6 roulements |
| `ECAR-EI_HOUSING FRONT EDRIVE` | 30,52 | Carters gauche et droit, logement de roulement, support de transmission, joint, tuyaux, une quarantaine de vis |

### Motif EI / 3D

La modélisation suit une convention stricte :

- Les 43 products `ECAR-EI_*` sont des éléments logiques (engineering items). Ce sont tous des assemblages.
- Les 36 products `ECAR-3D_*` sont les feuilles. Chacun possède exactement une `Rep3DAggr`, et aucun assemblage n'en possède.

37 des 43 EI ne contiennent qu'un seul enfant 3D et servent d'enveloppe, avec la même masse et le même matériau. Les six vrais assemblages sont la racine, `EMOTOR FRONT`, `STATOR`, `REDUCER FRONT`, `DIFFERENTIAL_ASSEMBLY` et `HOUSING FRONT EDRIVE`. L'interface peut fusionner chaque paire EI/3D en un seul composant sans perte d'information.

### Quantités et réutilisation

Il n'existe pas de champ quantité. La quantité correspond au nombre de `ProductInst` partageant le même couple (`Owned`, `Instancing`). Products instanciés plusieurs fois :

| Product | Quantité | Parent |
|---|---|---|
| `ECAR-EI_Screw D10 L155` | 14 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_Screw D8 L50` | 13 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_Screw D10 L115` | 4 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_MOTOR SCREW 1` | 3 | `HOUSING FRONT EDRIVE` |
| `ECAR-EI_90 degrees pipe` | 2 | `HOUSING FRONT EDRIVE` |
| `ECAR-3D_MOTOR SCREW 2` | 2 | `HOUSING FRONT EDRIVE` |
| `ECAR-3D_DifferentialSideShaft` | 2 | `DIFFERENTIAL SIDE SHAFT LEFT` et `RIGHT` (une fois chacun) |
| `ECAR-3D_DifferentialBevelGearTM_Bevel` | 2 | les deux EI `DIFFERENTIAL BEVEL GEAR TM BEVEL` (une fois chacun) |

Les deux dernières lignes comptent pour l'analyse d'impact : remplacer l'une de ces pièces 3D touche deux EI distincts.

### Cumul des masses

`V_WCG_Mass` est un champ calculé, et il se cumule exactement. Pour chacun des 43 assemblages, la masse est égale à la somme des masses des enfants, quantités comprises, sans aucun écart. C'est un bon test de validation pour le parser : si l'arbre reconstruit ne redonne pas 100,1 kg à la racine, il y a une erreur.

`ChildOrder` donne l'ordre d'affichage des enfants. `RelativeTransformation3D` donne la position de chaque instance par rapport à son parent (76 instances sur 112 ont une rotation non identité), ce qui pourrait alimenter une vue spatiale si besoin.

## Attributs exploitables

### Matériau

Le matériau est renseigné sur toutes les feuilles et sur toutes les enveloppes EI (toujours identique à celui de leur enfant 3D). Il n'est vide que sur les six vrais assemblages. On trouve 14 matériaux distincts sur les 36 feuilles :

| Matériau | Feuilles |
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

Associé à la masse, c'est la base la plus solide pour un indicateur de durabilité (par exemple le CO2 intrinsèque par matériau), à condition d'utiliser des facteurs d'émission issus d'une source externe citée.

### Révisions

`RevisionName` va de A à D (41 A, 23 B, 11 C, 4 D), avec un `RevisionIndex` correspondant (1 à 4).

## Lacunes

Ces lacunes limitent directement ce que l'application peut afficher tout en restant traçable jusqu'au XML.

- **Aucune donnée fournisseur, coût, make/buy, délai ou criticité.** Aucun de ces champs n'existe. L'analyse des dépendances fournisseurs et l'impact coût dans le Change Impact Analysis nécessitent un fichier d'enrichissement, présenté clairement dans l'interface comme une source hors PLM.
- **Pas d'historique de versions.** Les 79 products ont tous une `RevisionFamily` différente : aucune pièce n'apparaît en deux révisions. L'application peut afficher la révision courante de chaque pièce, mais pas comparer deux versions d'une même pièce à partir de cet extrait seul.
- **Cycle de vie uniforme.** Les 79 products et les 36 représentations sont `IN_WORK`, tous sur le lifecycle `VPLM_SMB_Definition_MajorRev`. La maturité seule ne permet pas de distinguer les pièces en termes de risque.
- **Métadonnées génériques.** `Owner` vaut toujours `admin_platform`, `Organization` toujours `Company Name`, `Project` toujours `ECAR_PLM`. Tous les `TimeCreated` tombent entre 16:29:23 et 16:29:25 le 14/10/2026, et tous les `TimeModified` valent 16:29:32 le même jour. Ce sont des horodatages d'export, pas un historique de conception.
- **Peu de descriptions.** Seuls 3 products en ont une (`High Speed Shaft`, `Full 3D 360deg Stator Core`, `This is only a single Tooth -> required for meshing`). Aucun `ProductInst` n'a de `Name` ; leur `ID` suit le motif `<nom de la référence>.<n>` (`EI_HSH.1`, `EI_EMOTOR FRONT.2`).

## Pièges

- **Les noms `GEAR_WHEEL`.** `ECAR-EI_GEAR_WHEEL` apparaît quatre fois, en révisions A, B, C et D, chacun enveloppant un `ECAR-3D_GearWheel`. Ce ne sont pas quatre versions d'une même pièce mais quatre roues dentées différentes (1,3, 1,6, 3,9 et 7,4 kg, `RevisionFamily` distinctes). Un regroupement par nom les fusionnerait à tort.

| `@id` | `ID` | Nom | Rév. | Masse (kg) |
|---|---|---|---|---|
| `ID_41` | `prd-12535825-00000062` | `ECAR-EI_GEAR_WHEEL` | A | 1,3 |
| `ID_45` | `prd-12535825-00000064` | `ECAR-EI_GEAR_WHEEL` | B | 1,6 |
| `ID_43` | `prd-12535825-00000063` | `ECAR-EI_GEAR_WHEEL` | C | 3,9 |
| `ID_47` | `prd-12535825-00000065` | `ECAR-EI_GEAR_WHEEL` | D | 7,4 |

- **Enveloppe EI manquante.** `ECAR-3D_MOTOR SCREW 2` est instancié deux fois directement sous `HOUSING FRONT EDRIVE`, sans enveloppe EI, contrairement à toutes les autres pièces. Tout code qui suppose « assemblage → EI → 3D » doit gérer ce cas.
- **Double comptage probable de masse dans le stator.** `ECAR-EI_STATOR` contient un noyau complet (`STATOR Core`, 21,5 kg) et un bobinage complet (`STATOR Coils`, 7,2 kg), plus une dent seule (0,12 kg) et une bobine seule (0,16 kg) modélisées pour le maillage. La dent et la bobine seules sont comptées dans la masse du stator (28,98 kg), qui est donc probablement surestimée de 0,28 kg. À signaler comme constat de qualité des données pendant la démo.
- **Nommage incohérent.** Certains noms ont un espace après le préfixe (`ECAR-EI_ MACHINE COOLING`, `ECAR-EI_ DIFFERENTIAL BEVEL GEAR TM BEVEL`), d'autres un espace à la place du tiret bas (`ECAR-3D Stator Core`, `ECAR-3D Screw D10 L155`). Les deux EI de pignons coniques ne diffèrent que par cet espace. La recherche par nom doit normaliser les espaces.
- **En-tête incohérent.** L'en-tête déclare `WithProcess=Yes`, mais le fichier ne contient aucun objet process.

## Conséquences pour le parser

- Indexer tous les éléments par `@id` dans une première passe, puis résoudre `Owned`, `Instancing` et `rootRefs`.
- Modéliser la structure comme un graphe : les `Product` comme nœuds, les `ProductInst` comme arêtes, en agrégeant les quantités par couple (parent, enfant) tout en conservant la liste des ids d'instance pour la traçabilité.
- Rattacher chaque `Rep3DAggr` au product qui la possède.
- Stocker une référence source (`@id`, `XID`, numéro de ligne) sur chaque nœud et chaque arête.
- Valider au chargement : une seule racine, aucune référence pendante, cumul des masses égal à 100,1 kg à la racine.
