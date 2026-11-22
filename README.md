# Le rail suit-il la France qui grandit ?

Projet statistique en Python : démographie, fréquentation des gares, dépendance automobile et climat. Les données sont réelles et archivées ; aucune observation simulée ni imputation aléatoire n'est utilisée.

La comparaison principale porte sur **2016–2022**, période commune SNCF–INSEE. Les séries **2015–2024** décrivent la fréquentation et la reprise après le Covid. Le document initial est conservé dans `docs/`.

## Lire les résultats

- [Rapport d'analyse illustré, HTML autonome](docs/RAPPORT_ANALYSE.html) — également [en Word](docs/RAPPORT_ANALYSE.docx) et [en Markdown](docs/RAPPORT_ANALYSE.md).
- [Méthodologie complète, Word](docs/METHODOLOGIE.docx) — également [en HTML](docs/METHODOLOGIE.html) et [en Markdown](docs/METHODOLOGIE.md).
- [Notebook de restitution exécuté](main.ipynb).
- [Dictionnaire des données](docs/DICTIONNAIRE_DONNEES.md) et [version CSV](docs/dictionnaire_donnees.csv).
- [Support de soutenance : dix diapositives et notes orales](docs/SOUTENANCE.md).
- [Carte interactive des gares, autonome](outputs/carte_gares_interactive.html).

Les fichiers HTML contiennent les images ou bibliothèques nécessaires ; aucun serveur n'est requis pour les ouvrir. Les liens vers les sites sources nécessitent naturellement un accès Internet.

## Bases finales

| Fichier dans `data/processed/` | Grain et contenu |
| --- | --- |
| `dataset_final_communes.parquet` et `.csv` | 34 858 communes COG2025 ; population, ménages, mobilité, densité, rail, stocks automobiles et drapeaux de qualité |
| `gares_annees.parquet` et `.csv` | 30 210 observations : 3 021 UIC × dix années, 2015–2024 |
| `gares_referentiel.parquet` | UIC, code commune, coordonnées, origine et méthode du rattachement |
| `communes_annees_rail.parquet` | Comptages agrégés par commune et année, périmètre SNCF |
| `demographie_population_long.parquet` | Population aux neuf dates de recensement retenues, 1968–2022 |
| `climat_parc_communes_cog2025.parquet` | Stocks SDES rapprochés du COG2025 ; arrondissements regroupés, sommes contrôlées |
| `climat_facteurs_ademe.parquet` | Facteurs moyens par voyageur.km, paramètres explicités |
| `climat_projections_departements.parquet` | Scénarios officiels INSEE Omphale, département × scénario |
| `aviation_*.parquet` | Trafic, liaisons observées, aéroports et émissions DGAC ; grains séparés |
| `contexte_lgv.csv` | Dates de mise en service extraites de trois pages HTML, à titre de contexte |

Pour conserver les codes et types, privilégier **Parquet**. Avec un CSV, lire notamment `code_commune`, `code_uic` et `code_departement` comme chaînes ; Excel peut sinon supprimer les zéros initiaux.

```python
import pandas as pd
communes = pd.read_parquet('data/processed/dataset_final_communes.parquet')
gares = pd.read_parquet('data/processed/gares_annees.parquet')
```

## Résultats à retenir

Dans les 2 618 communes comparables, la relation entre croissance démographique et croissance des comptages 2016–2022 est faible : Pearson 0,111 et Spearman 0,114. Ce champ représente environ 46,76 % de la population métropolitaine. Parmi ces communes, 484 combinent hausse démographique stricte et baisse des comptages.

Les 303 gares du décile supérieur concentrent 84,58 % des comptages 2024 ; le Gini entre gares est de 0,894. La part voiture des actifs occupés atteint environ 86,18 % dans le rural, contre 47,26 % dans l'urbain dense, selon les ratios d'effectifs INSEE comparables.

Ces résultats décrivent des associations. Les comptages ne mesurent ni des voyages uniques, ni la capacité ou l'offre de trains, ni un report modal causal. Les bassins de desserte dépassent les communes d'implantation.

## Exécuter sur cet ordinateur

L'environnement portable est déjà installé dans `.runtime/python313/` : CPython 3.13.9, pandas 2.3.3 et NumPy 2.2.6. Il évite de modifier le Python 3.15 du système.

Dans PowerShell, à la racine du projet :

```powershell
.\.runtime\python313\python.exe run.py --offline
```

Cette commande relit les archives, nettoie et rapproche les sources, reconstruit les tables et figures, vérifie les données et régénère les documents. Le réseau n'est pas utilisé. Les données dérivées et documents générés sont réécrits ; les sources brutes restent intactes.

Pour régénérer et exécuter le notebook, y compris sa reconstruction depuis les bruts :

```powershell
.\.runtime\python313\python.exe -m src.notebook --execute
```

Dans VS Code ou Jupyter, choisir cet environnement Python pour une exploration interactive. La cellule `DEPUIS_LES_BRUTS=True` reconstruit le projet ; la passer à `False` permet de lire rapidement les sorties existantes.

## Installer sur un autre poste

Python **3.13** est l'environnement de référence. Le dossier `.runtime/` est spécifique à Windows et n'est pas destiné à Git.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --offline
```

Sous Linux, créer le même environnement avec `python3.13 -m venv .venv`, puis utiliser `.venv/bin/python`. Le fichier `requirements-lock.txt` enregistre aussi l'environnement complet effectivement installé.

Pour une reproduction sans les archives livrées :

```powershell
python run.py --download
```

Les sources publiques peuvent changer ; cette commande complète le cache existant. Pour renouveler les instantanés, utiliser `python run.py --download --refresh`, puis examiner les nouveaux contrôles avant d'interpréter les différences. Un renouvellement peut légitimement modifier les résultats.

## Méthode et qualité

Trois accès ont été mobilisés : API paginées, fichiers téléchargeables et extraction HTML. Les URL, métadonnées, dates et empreintes SHA-256 accompagnent les sources. La validation est accessible dans [le bilan des contrôles](outputs/tables/validation_globale.json) ; elle vérifie l'intégrité et la cohérence des traitements, sans garantir l'exactitude de toutes les observations du producteur.

Les clés de jointure sont les UIC, les codes INSEE et les rattachements officiels COG2025. Les cas non résolus sont conservés et documentés. Les divergences entre deux publications INSEE ne sont pas remplacées arbitrairement ; des drapeaux guident les exclusions et sensibilités. Les zéros publiés restent distincts d'une valeur manquante.

La distance est celle du centroïde communal à une gare SNCF observée avec comptage positif en 2024, en métropole hors Corse. Elle ne mesure pas l'accès individuel à tous les réseaux : CFC, RATP, Chemins de fer de Provence et d'autres périmètres ne sont pas exhaustivement couverts. Les parts pondérées sont des populations de communes classées par leur centroïde.

PAP est censurée par le secret statistique : l'absence d'une liaison n'est jamais changée en zéro. Les émissions évitées ne sont pas inventées à partir des comptages des gares ; les facteurs ADEME et les émissions DGAC restent des objets distincts. Les scénarios Omphale ne sont pas des prévisions de trafic.

## Organisation

```text
docs/                 contexte initial, méthodologie, rapport, dictionnaire, soutenance
src/                  collecteurs, nettoyage, analyses, validation, génération des livrables
data/raw/             instantanés intacts, métadonnées et empreintes
data/processed/       bases finales CSV et Parquet
outputs/tables/       résultats, sensibilités et contrôles
outputs/figures/      graphiques et cartes PNG/SVG
outputs/demographie/  résultats démographiques complémentaires
outputs/climat/       parc, facteurs carbone, projections et audits
outputs/aviation/     résultats et contrôles DGAC
main.ipynb            restitution exécutée, reproductible depuis les archives
run.py                point d'entrée hors ligne par défaut
```

Les archives et les fichiers volumineux sont exclus par `.gitignore`. Aucun dépôt GitHub, stockage S3 ni historique de contributions de l'équipe n'a été créé. Ces éléments d'organisation restent à configurer avec les comptes réels ; le support de soutenance laisse les contributions à compléter.

## Sources et attributions

Sources principales : [SNCF Gares & Connexions](https://ressources.data.sncf.com/explore/dataset/frequentation-gares/), [INSEE](https://www.insee.fr/), [SDES](https://www.data.gouv.fr/datasets/parc-de-vehicules-routiers), [ADEME Impact CO₂](https://impactco2.fr/doc/api), [DGAC](https://www.data.gouv.fr/datasets/64808a5811da153f1439914c), [Etalab](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/) et [OurAirports](https://ourairports.com/data/).

Les licences des producteurs s'appliquent aux données dérivées et redistributions. Voir les notices archivées et les notes de chaque famille dans `docs/`, notamment l'ODbL des données SNCF. Les trois pages Wikipédia sont utilisées pour des faits de contexte, sans attribution causale.
