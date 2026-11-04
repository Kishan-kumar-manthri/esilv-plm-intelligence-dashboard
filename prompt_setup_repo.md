# Mission : créer la structure du repo `hackathon-plm-intelligence-dassault-systems` et son README

Tu crées uniquement l'arborescence du projet et le `README.md`. Tu n'écris aucun code, aucune donnée d'exemple et aucun fichier fictif. Tu ne lances aucune commande git ni `gh` : l'équipe gère le versioning elle-même.

## Pitch du projet

Hackathon ESILV A5 DPM/PLM, du 4 au 6 novembre 2026, projet 7 : « PLM Intelligence Challenge », proposé par Dassault Systèmes.

Notre équipe joue le rôle de l'équipe engineering et digital d'un fournisseur de moteurs électriques pour l'automobile. L'OEM, notre client, gère le développement de ses véhicules dans 3DEXPERIENCE, mais nous n'avons pas accès à son environnement PLM. Tout ce qu'il nous transmet, c'est un extrait XML brut : structure produit, assemblages, composants, attributs, versions et états de maturité.

Notre objectif est de transformer cet extrait en informations traçables qui aident à prendre des décisions d'ingénierie sur le coût, le risque, la qualité et la durabilité. La webapp couvre trois capacités :

1. **Product Explorer** : naviguer dans la BOM et les assemblages, chercher et filtrer, inspecter les composants et leurs propriétés, comparer les versions et les états de cycle de vie.
2. **Product Intelligence** : identifier les composants critiques, les dépendances fournisseurs et les risques liés au cycle de vie.
3. **Change Impact Analysis** : partir d'un remplacement de composant envisagé et trouver les assemblages, fournisseurs et coûts impactés.

En option, un assistant IA permet d'interroger les données en langage naturel. Chaque réponse doit afficher les sources PLM qui la justifient.

L'application doit répondre à trois questions métier :
- **Understand** : quels sont les sous-ensembles majeurs du moteur ? Quelles versions et propriétés existent ?
- **Identify risks** : quels composants sont critiques ? Où sont les dépendances fournisseurs ou de cycle de vie ?
- **Assess a change** : si un composant est remplacé, quels assemblages, fournisseurs et coûts sont touchés ?

Livrables : une webapp ou un dashboard et une présentation du cas d'usage.

Principe directeur : chaque information affichée doit pouvoir être reliée à son élément d'origine dans le XML.

## Arborescence à créer

Les dossiers vides contiennent un fichier `.gitkeep` pour être suivis par git.

```
plm-intelligence/
├── README.md
├── .gitignore
├── data/
│   └── raw/            # extrait XML de l'OEM (jamais commité)
├── docs/               # mapping XML, règles de risque, scénarios de démo
├── src/
│   └── plm/
│       ├── parser/     # lecture du XML et mapping vers le modèle de données
│       ├── analysis/   # exploration BOM, risques, change impact
│       └── agent/      # assistant IA avec sources (optionnel)
├── app/                # interface web
├── tests/
└── presentation/       # supports du pitch
```

## `.gitignore`

Environnements virtuels, caches Python, fichiers IDE (`.idea/`, `.vscode/`), `.env`, tout le contenu de `data/raw/` sauf `.gitkeep`, et tout fichier `*.xml` en dehors de `docs/`.

## Contenu du `README.md` (en français)

1. **Titre et accroche** : « PLM Intelligence — transformer un extrait PLM en décisions traçables », suivi du pitch ci-dessus en version courte (5 à 8 lignes).
2. **Contexte** : le rôle fournisseur / OEM, l'absence d'accès à 3DEXPERIENCE, l'extrait XML comme seule source.
3. **Fonctionnalités** : les trois capacités et l'assistant optionnel, avec une phrase chacune.
4. **Questions métier couvertes** : Understand / Identify risks / Assess a change.
5. **Architecture** : schéma texte du flux `XML OEM → parser → modèle de données → analyses / agent → interface`, puis le rôle de chaque dossier de l'arborescence.
6. **Données** : l'extrait XML se place dans `data/raw/` et n'est jamais commité ni déployé publiquement, parce qu'il s'agit de données partenaires.
7. **Installation et lancement** : section laissée à compléter, avec un TODO explicite (stack pas encore figée).
8. **Organisation de l'équipe** : tableau des workstreams, avec la colonne « Responsable » vide.

   | Workstream | Périmètre | Dossiers |
   |---|---|---|
   | Data | Parsing et mapping du XML, modèle de données | `src/plm/parser`, `docs/` |
   | Analysis | Graphe BOM, risques, change impact | `src/plm/analysis` |
   | UI | Interface et parcours de démo | `app/` |
   | Agent | Assistant IA sourcé (optionnel) | `src/plm/agent` |
   | Pitch | Scénarios de démo, slides | `presentation/`, `docs/` |

9. **Conventions Git** : `main` toujours démontrable ; branches courtes `feat/<workstream>-<sujet>` ou `fix/<workstream>-<sujet>` ; une PR vers `main` relue par au moins une personne ; squash merge ; merges fréquents (toutes les 2 à 3 heures) pour éviter les divergences.
10. **Planning** : J1 (4 nov.) analyse du XML et explorer ; J2 (5 nov.) risques, change impact et assistant ; J3 (6 nov.) finalisation de la démo et pitch.
11. **Équipe** : liste des membres à compléter.

Ton : sobre et direct, sans emojis ni superlatifs.

## Vérification avant de rendre la main

L'arborescence correspond exactement au schéma, chaque dossier vide contient un `.gitkeep`, il n'existe aucun autre fichier que `README.md`, `.gitignore` et les `.gitkeep`, et aucune commande git n'a été exécutée. Termine par la liste des fichiers créés.
