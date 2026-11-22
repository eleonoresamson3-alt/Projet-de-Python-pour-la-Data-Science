# Sources, préparation et limites du volet voiture, climat et projections

Version de travail vérifiée le **26 octobre 2026**. Le module reproductible est `src/climat.py`. Les fichiers originaux téléchargés se trouvent dans `data/raw/climat/` ; leurs URL complètes, dates de récupération, tailles et empreintes SHA-256 sont enregistrées dans `manifest.json`. Le programme ne génère aucune observation aléatoire et n'impute aucune donnée manquante.

## 1. Trois objets statistiques distincts

Le parc SDES mesure un **stock de véhicules au 1er janvier**. Les facteurs ADEME donnent des **émissions moyennes par voyageur.kilomètre** pour une convention précisée. Omphale décrit des **projections démographiques officielles conditionnelles à des hypothèses**. Ces trois objets restent dans des tables séparées : un nombre de voitures n'est pas une émission mesurée ; une projection n'est pas un recensement ; une différence de facteurs n'est pas un report modal observé.

La partie climat du projet s'appuie donc sur la part modale domicile-travail du recensement, les indicateurs de motorisation INSEE et, en complément, le parc SDES. Elle fournit une comparaison unitaire carbone des modes, sans prétendre reconstituer les émissions communales du transport routier ni les émissions effectivement évitées par le rail.

## 2. Parc de voitures particulières : SDES / RSVERO

### Origine et sélection

Producteur : Service des données et études statistiques du ministère chargé de la transition écologique. Le jeu est diffusé sous Licence Ouverte sur [data.gouv.fr](https://www.data.gouv.fr/datasets/parc-de-vehicules-routiers). La [publication 2026](https://www.statistiques.developpement-durable.gouv.fr/donnees-sur-le-parc-automobile-francais-au-1er-janvier-2026) et la [notice méthodologique](https://data.statistiques.developpement-durable.gouv.fr/dido/api/files/6e8c4d0d-95df-4cc0-9559-54562d4ae48f) expliquent l'estimation issue des immatriculations et des contrôles techniques. Le fichier communal est désormais diffusé par l'API DiDo, et non par une succession de CSV annuels indépendants.

L'[API DiDo](https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/1582861b-e042-4490-9161-6429d8229703?millesime=2026-06) est appelée avec le millésime explicite `2026-06`, le filtre `GROUPE=eq:VP` et une sélection de colonnes. Sont retenus les stocks de **2016, 2019, 2022, 2023 et 2024** : 2016–2022 pour la comparaison principale compatible avec les recensements du projet, 2019 comme référence avant Covid, 2023 comme dernier stock léger annoncé définitif dans cette édition, 2024 pour l'enrichissement temporel. Le fichier source complet contient aussi d'autres années, non téléchargées afin de limiter le volume. Aucun filtre départemental n'est appliqué : les DROM et les localisations non renseignées restent présents dans la source.

Le grain de la réponse est `commune × carburant × Crit'Air × statut utilisateur × groupe × catégorie`. Le filtre VP conserve à la fois les **particuliers et les professionnels**. L'export compressé contient **786 703 lignes**, exactement le nombre annoncé par l'endpoint `/count` utilisant les mêmes filtres. Le gzip conserve les octets du CSV source après décompression ; il ne constitue pas un échantillonnage.

### Traitement

1. Lecture des codes de commune en chaînes pour préserver les zéros initiaux et les codes corses.
2. Vérification du filtre VP et de l'unicité du grain source ; absence de doublon détectée.
3. Conversion explicite des cinq colonnes de stock en nombres ; échec si une valeur manque ou est négative.
4. Somme de toutes les ventilations carburant/Crit'Air/statut par code communal pour le parc total. Une somme distincte retient les lignes `STATUT_UTILISATEUR=Particulier`. Une autre retient la motorisation exactement libellée `Electrique`, sans y ajouter les hybrides.
5. Séparation des codes fictifs finissant par `000`, des cinq codes DROM `97100`, `97200`, `97300`, `97400`, `97600`, et des codes de forme invalide. **101 codes** sont conservés dans une annexe séparée et exclus de la table communale. **34 916 codes de forme communale** restent à confronter au COG de la table INSEE ; ce nombre n'est pas présenté comme le nombre de communes françaises.
6. Conservation des sommes avant et après agrégation, à tolérance numérique explicite. Les ventilations absentes ne sont pas remplacées silencieusement par zéro.

La notice rattache les véhicules au Code officiel géographique de la dernière année disponible. Le numéro exact de cette géographie n'est pas précisé dans les métadonnées de l'extraction. La jointure avec la géographie INSEE 2025 est donc effectuée **par code et avec une table des rejets**, sans prétendre qu'un millésime COG identique a été vérifié. Si des codes manquent, on ne les rapproche pas sur le seul nom.

### Passage contrôlé à l'univers communal du projet

La table source précédente reste inchangée. Une deuxième table, `climat_parc_communes_cog2025.csv` et `.parquet`, utilise le COG officiel `data/raw/insee/v_commune_2025.csv` et la correspondance `demographie_passage_cog2025.csv` produite par le volet INSEE. Un code officiel de commune conserve son identité ; un arrondissement municipal, une commune associée ou déléguée est rattaché uniquement si le COG fournit un parent officiel. Dans l'extraction présente, les **45 rattachements effectivement nécessaires sont les 45 arrondissements de Paris, Lyon et Marseille**.

Le SDES contient également des voitures affectées directement au code parent de ces trois villes. Ce ne sont pas des totaux municipaux : ce sont des affectations distinctes des codes d'arrondissement. On additionne donc les arrondissements **et le résidu parent**. Les stocks 2022 obtenus sont : Paris **572 394 VP**, provenant de 21 codes ; Lyon **205 495 VP**, provenant de 10 codes ; Marseille **375 142 VP**, provenant de 17 codes. Prendre seulement la ligne parent aurait conduit à des stocks manifestement faux de 250, 120 et 41 voitures. La conservation des sommes est vérifiée séparément pour chaque année et sous-parc.

La table finale contient **34 854 communes appariées sur 34 858 communes de l'univers RP 2022**. Les quatre absences SDES sont Bezonvaux, Cumières-le-Mort-Homme, Haumont-près-Samogneux et Louvemont-Côte-du-Poivre, toutes de population 2022 nulle ; elles sont signalées, sans stock artificiellement imputé. Les 17 communes de Mayotte sont des codes COG officiels, mais ne font pas partie de l'univers de ce recensement : elles restent dans l'annexe de rejets de jointure, pour **23 314 VP en 2022**. Aucun code de forme communale ne reste géographiquement inconnu après contrôle au COG. Cette réussite sur les codes n'annule pas la réserve sur l'absence de numéro de géographie explicitement fourni par le SDES.

Les audits sont dans `outputs/climat/audit_passage_sdes_cog2025.csv` (chaque code source, cible officielle, cible dans l'univers, statut et stocks), `audit_parc_paris_lyon_marseille.csv`, `parc_codes_non_resolus_cog2025.csv` (ici exclusivement Mayotte hors univers), `audit_communes_rp_sans_parc_sdes.csv` et `qualite_passage_cog2025.json`. La table harmonisée ajoute `nb_codes_source_agreges`, `nb_arrondissements_source`, `nb_communes_deleguees_source`, `nb_communes_associees_source`, `cog_cible=2025` et `cog_exact_source_sdes_non_precise=True`. Le taux de croissance du parc y est recalculé après agrégation, plutôt que moyenné entre codes source.

### Sorties et dictionnaire

`data/processed/climat_parc_communes.csv` et `.parquet` : une ligne par code de forme communale.

| Variable | Définition et unité |
|---|---|
| `code_commune` | Code géographique SDES, chaîne ; jointure auditée requise |
| `vp_2016`, `vp_2019`, `vp_2022`, `vp_2023`, `vp_2024` | Voitures particulières, tous utilisateurs, stock au 1er janvier, véhicules |
| `vp_particuliers_YYYY` | Sous-ensemble dont le certificat indique un utilisateur particulier, véhicules |
| `vp_electriques_YYYY` | Sous-ensemble dont la motorisation est exactement `Electrique`, véhicules |
| `vp_croissance_2016_2022_pct` | `100 × (vp_2022 / vp_2016 − 1)` si le stock 2016 est strictement positif ; sinon manquant |
| `millesime_source_sdes` | Édition de diffusion, `2026-06` |
| `code_fictif_ou_invalide` | Indicateur de séparation des localisations impropres à une jointure communale |

Les codes fictifs sont archivés dans `climat_parc_codes_fictifs.csv` et `.parquet`. Les contrôles sont dans `outputs/climat/qualite_parc.json`. Le tableau `outputs/climat/parc_national.csv` donne, sur le périmètre de la source, **37 165 052 VP en 2016**, **38 820 387 en 2022** et **39 360 740 en 2024**, dont respectivement 7 798, 22 994 et 17 927 affectées à des codes fictifs ou invalides. Ce contrôle démontre la conservation interne de la source ; il n'est pas une validation indépendante par une autre enquête. Les totaux publiés séparément par le SDES peuvent différer par arrondi et révision.

### Précautions

- Le stock léger 2024 est révisable dans l'édition collectée ; 2023 et les années précédentes sont annoncés définitifs. Les résultats 2016–2022 évitent cette révision récente.
- L'adresse est celle du titulaire/utilisateur du certificat, avec le locataire en cas de longue durée ou crédit-bail. Elle ne décrit pas le lieu où la voiture circule.
- Les véhicules professionnels et les voitures de fonction peuvent être localisés au siège d'une entreprise. `vp_particuliers` n'est donc pas identique au nombre de voitures possédées ou utilisées par les ménages du recensement.
- `VP / population` est un ratio de stocks localisés ; `VP particuliers / ménages` n'est pas le taux de ménages motorisés. Le second s'obtient dans la source INSEE ménage et non par division de ces stocks.
- Ni la distance annuelle parcourue, ni la consommation réelle, ni une émission communale n'est contenue dans l'extraction retenue. Il serait incorrect de multiplier simplement ce stock par un facteur voyageur.km.

## 3. Facteurs d'émission : ADEME Impact CO₂

### Accès vérifié

La [documentation de l'API Impact CO₂](https://impactco2.fr/doc/api) et son [référencement public](https://www.data.gouv.fr/dataservices/api-impact-co2) permettent une extraction sans compte au moment de la collecte. La réponse prévient que l'accès anonyme peut être interrompu ultérieurement ; le projet fonctionne donc ensuite avec la réponse brute archivée. Aucun secret n'est utilisé.

L'URL exacte est enregistrée dans le manifeste. Les paramètres essentiels sont : `km=1`, `transports=2,3,4,5,14,15`, `includeConstruction=1`, `occupencyRate=1`, `displayAll=1`. Les six modes sont TGV, Intercités, voiture thermique, voiture électrique, RER/Transilien et TER. Les identifiants et les conventions sont vérifiés dans le [code source officiel de l'API](https://github.com/datagir/impactco2/blob/3106130d308c2cf5605d409779b7b22b32221258/app/api/v1/transport/route.ts), archivé localement avec le [fichier des modes](https://github.com/datagir/impactco2/blob/3106130d308c2cf5605d409779b7b22b32221258/src/data/categories/deplacement.ts), tous deux fixés à une version précise.

La valeur `value` est l'émission en kg CO₂e pour la distance demandée, donc ici **kg CO₂e par voyageur.km**, avec une voiture occupée par **une personne** et la **construction incluse**. Les g CO₂e/voyageur.km sont obtenus par multiplication par 1 000. Le projet ne suppose pas que toutes les infrastructures sont incluses dans cette convention.

| Mode | g CO₂e / voyageur.km, extraction du 26/10/2026 |
|---|---:|
| TGV | 2,93 |
| Intercités | 8,98 |
| RER ou Transilien | 9,78 |
| TER | 27,69 |
| Voiture électrique, 1 occupant | 67,37 |
| Voiture thermique, 1 occupant | 142,25 |

Ces nombres viennent directement de la réponse archivée, sans saisie manuelle. `climat_facteurs_ademe.csv` et `.parquet` contiennent le mode, son identifiant ADEME, les deux unités, les paramètres de périmètre et la date de collecte. L'infographie officielle SNCF d'octobre 2025 est également conservée, comme référence documentaire secondaire. Ses facteurs diffèrent, car la période, le remplissage et certains postes de maintenance ne sont pas identiques ; on ne les mélange pas avec ceux de l'ADEME.

### Une comparaison de scénarios unitaires, pas un bilan observé

`outputs/climat/comparaison_unitaire_scenarios.csv` calcule, pour des distances **conventionnelles** de 20, 100 et 500 km et des occupations de voiture de 1, 1,6 et 2 personnes :

`écart unitaire = distance × (facteur voiture à 1 occupant / occupation − facteur train)`.

Ces distances et taux d'occupation sont des **hypothèses de sensibilité annoncées**, pas des observations créées pour compléter le dataset. L'égalité des distances entre modes est une convention pédagogique ; un trajet routier et ferroviaire réel n'ont pas nécessairement la même longueur. Les scénarios ne servent pas à classer des communes en émissions évitées.

Les comptages de gare n'identifient ni un nombre de trajets uniques, ni leur distance, ni le mode qui aurait été utilisé en l'absence du rail. Ils ne suffisent donc pas à calculer un bilan national ou régional de report modal. Une telle extension nécessiterait des flux origine-destination, distances de réseau, taux d'occupation et un contrefactuel explicite. Les facteurs collectés en 2026 ne sont pas une série historique 2015–2024.

## 4. Projections départementales INSEE Omphale à 2050

### Deux publications et une règle de précision

Les [tableaux départementaux détaillés publiés le 8 janvier 2024](https://www.insee.fr/fr/statistiques/7747107) sont issus d'Omphale 2022 et d'une base démographique 2018. Les fichiers `donnees_det_Central.xlsx`, `donnees_det_Pop_basse.xlsx` et `donnees_det_Pop_haute.xlsx` fournissent les populations annuelles par sexe et âge quinquennal de 2018 à 2070. La source est donc **modélisée par l'INSEE**, et explicitement séparée des observations de recensement du projet.

Les [classeurs de synthèse publiés en 2022](https://www.insee.fr/fr/statistiques/6652134) fournissent les codes et noms des départements. Ils sont téléchargés et conservés pour les trois scénarios. Leur population est arrondie au millier : on ne les utilise pas pour donner une illusion de précision plus grande. La population utilisée pour les calculs provient des fichiers détaillés de 2024 : chaque cellule sexe-âge est arrondie à la dizaine, et leur documentation recommande une interprétation à l'ordre de grandeur du millier.

### Traitement et contrôles

Chaque fichier détaillé contient **4 040 lignes = 101 départements × 2 sexes × 20 classes d'âge**. Le script vérifie ce grain et l'absence de doublons, puis additionne les quarante cellules disjointes par département et année. Une table de correspondance sur les libellés internes des deux publications INSEE fournit les codes départementaux, avec suppression des accents/ponctuations et une harmonisation explicite de Réunion/La Réunion. Les 101 départements doivent être appariés : sinon le programme échoue.

La sortie `climat_projections_departements.csv` et `.parquet` contient **303 lignes = 101 départements × 3 scénarios**. Les colonnes principales sont `code_departement` (chaîne), `nom_departement`, `scenario_insee`, `population_projetee_2018` à `population_projetee_2070` (personnes), `croissance_projetee_2018_2050_pct`, `statut_donnee` et `precision_source`. Le taux est calculé par `100 × (population_projetee_2050 / population_projetee_2018 − 1)`. Une légère différence avec les synthèses arrondies au millier est normale.

Les trois scénarios partent des hypothèses standardisées INSEE. Le scénario central, bas et haut ne constituent **ni des probabilités, ni un intervalle de confiance**, et ne doivent pas être présentés comme des prévisions certaines. Les comportements migratoires et la base sont ceux du modèle 2018/2022 ; les évolutions récentes postérieures à cette base ne sont pas réestimées dans ce projet. On ne projette pas la fréquentation ferroviaire par une simple règle de trois démographique.

Dans le scénario central, en métropole, la croissance 2018–2050 est d'environ **24,3 % en Loire-Atlantique**, **23,9 % en Gironde** et **23,6 % en Haute-Garonne**. Les baisses les plus fortes de la table sont d'environ **22,2 % dans le Territoire de Belfort**, **20,3 % dans les Ardennes** et **20,3 % en Haute-Marne**. Ce sont des résultats du scénario officiel, à lire avec les limites de sa base temporelle, et non une conclusion empirique sur le réseau en 2050.

## 5. Reproduction et figures

Exécution hors ligne après installation des dépendances du projet :

```powershell
python -m src.climat
```

Collecte explicite, en réutilisant les archives déjà présentes après vérification d'empreinte :

```powershell
python -m src.climat --download
```

L'option `--refresh` associée à `--download` remplace les archives par une nouvelle extraction : une nouvelle version du manifeste et des résultats doit alors être conservée pour documenter cette mise à jour. Le millésime SDES reste fixé ; l'API ADEME peut évoluer, d'où la nécessité de garder le jeu brut de référence.

Les trois figures exportées en PNG et SVG dans `outputs/climat/` montrent les facteurs ADEME, les cinq stocks nationaux SDES retenus et les douze extrêmes départementaux du scénario central Omphale avec les scénarios bas/haut. Elles portent leurs unités, périmètres et sources. La sélection des douze départements est mécanique et annoncée ; elle ne constitue pas une couverture exhaustive de la carte française.

Les limites sont conservées dans les résultats : la présence d'une association entre motorisation, population et fréquentation ne permet pas de conclure à une causalité ; le stock SDES et les facteurs moyens ne remplacent pas un inventaire territorial des émissions. Aucun inventaire national communal homogène Citepa n'a été ajouté sans preuve d'accès, de millésime et de périmètre comparables.
