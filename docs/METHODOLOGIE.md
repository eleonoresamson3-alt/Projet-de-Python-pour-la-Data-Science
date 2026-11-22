# Méthodologie de constitution des données et d'analyse

Projet : **Le rail suit-il la France qui grandit ?** Démographie, fréquentation des gares et mobilités dans les territoires.

Version du 26 octobre 2026. Document généré depuis les contrôles et résultats enregistrés, avec conservation des fichiers bruts. Le brouillon de départ reste dans `docs/Brouillon idées projet python.docx` ; son texte est également extrait dans `docs/contexte_extrait.txt`.

## 1. Question, portée et engagement sur les données

L'objectif est de décrire comment la population et l'usage observé des gares évoluent conjointement, puis de rapprocher ces évolutions des caractéristiques territoriales et de la dépendance automobile. La fréquentation mesure un usage estimé par le producteur ; elle ne mesure directement ni l'offre de trains, ni la capacité, ni la satisfaction des besoins de transport.

Le projet ne génère aucune observation ni aucun tirage aléatoire pour compléter une série. Cette règle concerne nos traitements ; le recensement source repose lui-même en partie sur des enquêtes par sondage. Les données d'origine sont archivées ; les traitements calculent des agrégats, des ratios et des indicateurs vérifiables. Les projections Omphale sont des scénarios officiels de l'INSEE, identifiés comme tels. Les facteurs carbone sont des références moyennes, distinctes des émissions réellement observées dans un territoire.

La démarche est descriptive et exploratoire. La population étudiée n'est pas un échantillon probabiliste : aucun intervalle de confiance de sondage ni test de causalité n'est construit. Les incertitudes dominantes concernent les périmètres, la qualité des mesures, la censure et les changements de méthode.

## 2. Choix des périodes et des champs

La comparaison principale utilise 2016–2022, car ces deux dates sont présentes dans la fréquentation SNCF et les bases du recensement RP 2022. Cela évite de comparer une croissance démographique 2016–2022 à une croissance ferroviaire 2015–2024. Le recensement 2022 est conservé comme millésime commun des différents thèmes, même si certaines publications plus récentes existent au moment de la collecte.

Les séries SNCF 2015–2024 servent à décrire la concentration, les changements de rang et l'évolution avant/après le Covid ;2019 est la base100 de référence. L'analyse du parc utilise les années réellement extraites de l'édition SDES 2026-06. Les projections utilisent 2018 comme base et 2050 comme horizon.

La table démographique contient **34 858 communes**, dont **34 746 métropolitaines**, dans la géographie COG 2025. Mayotte est absente du champ RP 2022 exploité. Les statistiques de population de métropole incluent la Corse. Le proxy de distance aux gares est restreint à la métropole hors Corse, car les Chemins de fer de la Corse sont absents du périmètre de fréquentation SNCF retenu ; les communes insulaires telles que Ré et Oléron restent dans ce champ.

## 3. Inventaire raisonné des sources

| Source | Rôle effectif | Millésime / accès |
| --- | --- | --- |
| SNCF Gares & Connexions | Comptages annuels, UIC, coordonnées et code commune | Fréquentation 2015–2024 ; référentiel extrait le 26/10/2026 ; API paginée |
| SNCF Réseau | Coordonnées de secours et tracés du réseau | Liste des gares et GeoJSON archivés ; API et export |
| INSEE RP 2022 | Population 1968–2022, ménages, motorisation et déplacements domicile–travail | Fichiers ZIP ; géographie COG 2025 |
| INSEE COG 2025 et grille de densité 2025 | Codes parents, régions et typologie officielle urbain/rural | CSV et XLSX |
| Etalab / contours administratifs | Polygones pour rattachement spatial et cartographie | Version 2025, simplification100m, GeoJSON compressé |
| SDES / API Dido | Stocks de voitures particulières et détenteurs | Édition 2026-06 ; stocks au 1er janvier 2016,2019,2022,2023,2024 |
| ADEME Impact CO₂ | Facteurs moyens de comparaison des modes | API publique ; construction incluse ; voiture à 1 occupant |
| INSEE Omphale 2022 | Trois scénarios départementaux jusqu'à 2050 | Population de base 2018 ; fichiers officiels |
| DGAC | Trafic domestique LSN, liaisons PAP et émissions annuelles | Archives 1990–2025 ; analyse 2015–2024 |
| OurAirports | Géolocalisation et codes des aéroports | Référentiel courant archivé ; CSV, domaine public |
| Wikipédia, trois pages LGV | Dates de mise en service à titre de contexte | Scraping HTML, robots.txt vérifié ; pas de jointure analytique |


Les licences et notices des producteurs sont conservées dans les métadonnées brutes et les notes par famille : `notes_demographie.md`, `notes_climat.md`, `notes_aviation.md`, `notes_contexte_lgv.md`. La fréquentation SNCF et les couches Réseau sont soumises à l'ODbL ; les attributions restent nécessaires lors de la redistribution. Les données OurAirports sont diffusées dans le domaine public ; le contenu Wikipédia relève de sa licence propre et n'est utilisé ici que pour de courtes extractions factuelles contextualisées.

## 4. Collecte, traçabilité et reproductibilité

Trois modes d'accès sont effectivement employés : fichiers téléchargeables ZIP/CSV/XLSX/GeoJSON ; API SNCF, SDES et ADEME ; extraction de HTML pour les pages documentaires INSEE et les trois pages LGV. Pour les LGV, `robots.txt` est archivé, l'autorisation est vérifiée et un délai d'au moins deux secondes sépare les requêtes.

L'API SNCF est paginée par blocs de 100 lignes ; chaque réponse est archivée séparément. Le nombre de lignes reconstitué est confronté au total annoncé dans les métadonnées. Les requêtes sont espacées et réessayées en cas d'erreur. Les sources brutes ne sont renouvelées qu'à la demande explicite `--refresh` ; une reconstruction ordinaire se fait hors ligne.

Chaque collecte utilisée possède une URL exacte et une empreinte SHA-256, avec taille et date de récupération ou date de modification locale documentée selon le collecteur. La date de référence du travail est le 26/10/2026 ; les horodatages techniques UTC sont conservés séparément. Les empreintes attestent l'intégrité de l'instantané, pas l'absence d'erreur chez le producteur. L'audit actuel vérifie **176 fichiers bruts**.

## 5. Modèle de données et unités d'observation

La base finale est organisée en plusieurs tables, plutôt que de forcer des données de grains différents dans un seul fichier. `dataset_final_communes.parquet` contient une ligne par commune COG 2025. `gares_annees.parquet` contient une ligne par UIC et année : **30 210 lignes**, soit 3 021 UIC sur dix années. `communes_annees_rail.parquet` contient les agrégats des seules gares rattachées. Les projections restent au département et au scénario ; l'avion reste au mois/faisceau ou à la paire d'aéroports.

Les codes INSEE et UIC sont des chaînes de caractères ; les zéros initiaux sont conservés. Les codes postaux ne servent jamais de code commune. Les UIC attendus comportent huit chiffres ; les codes communaux cinq caractères avec possibilité de 2A/2B. Paris, Lyon et Marseille sont traitées comme communes entières, avec rattachement de leurs arrondissements par le COG officiel.

Un comptage de voyageurs en gare n'est ni un voyageur unique ni un nombre de déplacements de résidents. Des voyageurs peuvent être comptés à plusieurs gares et les bassins de recrutement dépassent les limites communales. Le ratio comptages/habitant est donc un indicateur de concentration de l'usage des gares implantées dans une commune, et non un taux individuel d'utilisation du train.

## 6. Nettoyage, valeurs manquantes et divergences de sources

Les années en colonnes dans la source SNCF sont passées au format long. Seules les colonnes « voyageurs » sont retenues ; les colonnes incluant les non-voyageurs ne sont pas mélangées à la mesure principale. Les types et valeurs non négatives sont contrôlés. Les zéros publiés sont conservés, sans les interpréter automatiquement comme des fermetures. Les valeurs non publiées restent manquantes, sans interpolation ni imputation.

Les bases INSEE sont lues en conservant leurs décimales et leurs codes. Les parts sont laissées non définies lorsque le dénominateur est nul ou absent. La catégorie « au moins deux voitures » ne permet pas de connaître le parc exact des ménages : son usage dans un nombre de voitures par ménage fournit une borne inférieure, correctement nommée dans le fichier.

Un contrôle croisé entre deux publications INSEE révèle12 communes divergentes pour 2016 et une pour 2022, malgré un millésime géographique annoncé identique. L'historique de population est conservé comme série de référence ; les écarts sont exportés dans `demographie_ecarts_inter_sources.csv`. Les ratios de mobilité ou de motorisation concernés sont neutralisés et des drapeaux de comparabilité restent disponibles. Le croisement principal rail/population exclut les communes signalées ; une analyse de sensibilité les réintègre. Les écarts ne sont jamais « corrigés » par substitution arbitraire.

## 7. Jointures et harmonisation géographique

La jointure gare→commune privilégie le code INSEE du référentiel Gares & Connexions. Les listes de plusieurs UIC sont éclatées ; l'unicité de chaque UIC est contrôlée, les conflits éventuels étant mis à l'écart. Les codes d'arrondissement ou de communes déléguées sont ramenés au parent officiel COG 2025. Aucun appariement approximatif sur un nom de gare n'est utilisé.

Lorsque les coordonnées Gares & Connexions manquent, le référentiel Réseau sert de secours. Il peut contenir plusieurs projections ferroviaires pour un même UIC : la médiane des coordonnées est utilisée uniquement si la dispersion de ces projections est au plus1 km ; une table d'audit recense les projections plus dispersées. Ce seuil est un contrôle de prudence, pas une précision géodésique annoncée.

Pour les codes commune absents ou obsolètes non résolus par le COG, les points sont rattachés par inclusion dans un polygone COG 2025 simplifié à 100m. Les arrondissements sont retirés de la couche de jointure pour éviter leur superposition à la commune entière. Un résultat spatial ambigu est laissé non résolu ; il n'y a pas d'affectation automatique au polygone le plus proche.

Le bilan est de **3019 gares rattachées sur 3021**, soit **99,934%** des UIC et **99,699%** des comptages 2024. Les deux exceptions concernent Monaco–Monte-Carlo et la Halte de Fontanil–Lycée de Drap, absentes des référentiels utilisés. Elles restent dans la table source, avec une commune manquante ; Monaco n'est pas artificiellement affectée à une commune française.

Le SDES présente les stocks de Paris, Lyon et Marseille à la fois sur les arrondissements et sur un petit résidu au code parent. Ces lignes représentent des ventilations disjointes : on les additionne après rattachement officiel, en contrôlant la conservation des sommes.45 codes sont ainsi rattachés. Les101 codes fictifs ou non localisés sont gardés à part ;17 codes officiels de Mayotte sont hors du champ RP 2022. **34854 communes** sont appariées ; les quatre communes du RP sans ligne SDES ont toutes une population nulle et ne sont pas remplies par zéro. La notice SDES ne précise pas le millésime géographique exact : les correspondances de codes ne garantissent donc pas une harmonisation historique complète des périmètres.

## 8. Cohorte ferroviaire et champ du croisement principal

Pour chaque UIC, on retient un comptage 2016 strictement positif et un comptage 2022 observé, pouvant être nul. Les sommes 2016 et 2022 sont ensuite calculées sur exactement les mêmes UIC dans chaque commune. Cette cohorte évite de comparer deux ensembles de gares différents, mais exclut les nouvelles gares et les bases 2016 nulles ; elle ne décrit donc pas l'intégralité des transformations du réseau.

Après restriction à la métropole, population de base définie et retrait des alertes géographiques INSEE, le champ principal compte **2 618 communes**, représentant **46,76%** de la population métropolitaine 2022. Il s'agit de communes d'implantation des gares observées ; les résultats ne sont pas extrapolés aux communes sans gare ni à l'ensemble des habitants. Les agrégats régionaux de population couvrent toutes les communes, alors que le rail régional reste limité à cette cohorte de gares : cette différence de champ est rappelée à l'interprétation.

## 9. Indicateurs construits et calculs statistiques

Pour une quantité positive à la base et observée à l'arrivée, la croissance totale est100×(Xfin/Xdébut−1). Le taux de croissance annuel moyen est100×[(Xfin/Xdébut)^(1/n)−1] ; n=6 entre 2016 et 2022. Un point final nul donne un TCAM de−100% : cette limite mathématique est conservée, sans conclusion automatique de fermeture. Une base nulle rend le taux non défini.

L'écart rail/population est le TCAM des comptages moins celui de la population, en points de pourcentage annuels. Les quatre profils de signe distinguent les TCAM négatifs des TCAM nuls ou positifs ; la stabilité exacte est donc incluse dans la catégorie≥0. Les trajectoires démographiques « déclin/stable/croissance » utilisent un autre seuil, annoncé à±0,2%/an, qui est un choix de description, pas un seuil de significativité.

La part voiture est100×actifs occupés de 15 ans ou plus utilisant principalement la voiture / ensemble des actifs occupés de 15 ans ou plus. Le dénominateur comprend notamment les personnes sans déplacement. La catégorie transports en commun regroupe plusieurs modes et n'est pas une part ferroviaire. Pour agréger un groupe, on calcule le ratio des sommes des effectifs valides sur le même ensemble de communes ; on ne moyenne pas les pourcentages communaux.

Le solde naturel 2016–2022 est le nombre de naissances 2016–2021 moins les décès sur cette même période. Le solde migratoire apparent est la variation de population moins ce solde naturel ; le terme « apparent » rappelle qu'il absorbe également les ajustements de mesure.

La dispersion est décrite par médiane, quantiles, distribution logarithmique des valeurs positives, courbe de Lorenz et Gini. Le Gini est calculé sur les comptages 2024 non négatifs, zéros inclus ; il mesure la concentration entre gares, pas une inégalité d'accès des personnes. La part des10% utilise l'arrondi supérieur du nombre de gares, soit 303 UIC. Les quintiles sont recalculés séparément en 2015 et 2024 sur les gares positives aux deux dates ; les transitions sont normalisées par ligne.

Les corrélations Pearson et Spearman sont non pondérées au niveau communal. Les effectifs sont publiés pour chaque paire de variables. Spearman limite l'influence des valeurs extrêmes, sans résoudre la dépendance spatiale ni les facteurs de confusion. Les sensibilités excluent l'Île-de-France, imposent au moins10 000 comptages en 2016, retirent le 1% supérieur des volumes 2022 ou réintègrent les alertes géographiques.

## 10. Distance aux gares : définition exacte du proxy

L'indicateur est la **distance du centroïde géométrique communal à la gare SNCF observée la plus proche avec comptage positif en 2024**. Les polygones et points sont projetés en Lambert93, EPSG:2154 ; la recherche du plus proche voisin emploie une distance euclidienne en mètres, convertie en kilomètres.

La population entière d'une commune est affectée au classement de son centroïde, faute de population carroyée dans ce projet. « Population des communes dont le centroïde est à plus de 10 km » est donc la formulation exacte ; « population vivant à plus de 10 km d'une gare » serait une conclusion non mesurée. Les seuils5/10/15 km montrent la sensibilité de ce proxy, pas une frontière naturelle d'accès au train.

La Corse est laissée manquante et grisée, car le réseau CFC n'est pas couvert par la source SNCF. Le réseau RATP et les Chemins de fer de Provence Nice–Digne ne sont pas exhaustivement couverts non plus. Le proxy ne décrit pas l'ensemble du rail français. Un comptage positif n'est pas une certification exhaustive de toutes les gares ouvertes ; une valeur nulle ne prouve pas leur fermeture. Il n'est calculé ni temps de marche, ni trajet routier, ni fréquence de desserte, ni évolution historique de l'accessibilité.

La « part de croissance positive » est la somme des variations de population communales positives dans un groupe, divisée par la somme de toutes les variations communales positives du champ ; les baisses sont écrêtées à zéro. Ce n'est pas une part de la croissance nette nationale.

## 11. Voiture, facteurs carbone et émissions

Le parc SDES est un stock au 1er janvier, diffusé avec arrondis. Une voiture enregistrée dans une commune ne mesure ni ses kilomètres parcourus ni les émissions émises sur ce territoire ; les véhicules de personnes morales et les véhicules de particuliers sont distingués. Les ratios par habitant ou ménage sont descriptifs et subissent les limites du rapprochement géographique SDES/RP.

Les facteurs ADEME sont archivés avec paramètres explicites : un kilomètre, construction incluse, un occupant pour la voiture. Ils sont exprimés en grammes de CO₂ équivalent par voyageur.km. Les comparer à activité transportée identique est possible ; les multiplier par les comptages de gare seuls ne l'est pas, car les origines–destinations, distances, doubles comptes et comportements de report sont inconnus.

Ainsi, aucun total d'« émissions réellement évitées grâce au train » ni d'émissions routières communales n'est fabriqué. Les comparaisons normalisées de facteurs figurent séparément dans les sorties climat. Le CO₂ DGAC est net, avec prise en compte des carburants d'aviation durables (SAF), et hors effets non-CO₂ ; les intensités en g CO₂/Peq.km incluent l'équivalence du fret dans les passagers équivalents. Cet objet est distinct d'un facteur ADEME en CO₂e de cycle de vie : leurs périmètres ne sont pas fusionnés.

## 12. Complément avion et réglementation

La série DGAC LSN fournit le trafic intérieur métropolitain agrégé ; elle sert aux évolutions nationales. La série PAP décrit les liaisons observées avec leurs deux sens réunis dans la notice actuelle, même si une ancienne URL évoque « par sens ». Une paire ne doit donc pas être doublée artificiellement.

PAP est censurée : conditions de pluralité d'opérateurs et de concentration, et seuil mensuel de 10 000 passagers équivalents. Une absence n'est pas un zéro. Les couvertures mensuelles et annuelles sont publiées ; des totaux PAP qui changent de couverture ne deviennent pas une série représentative du marché. OurAirports apporte des coordonnées et codes courants ; les identifiants historiques absents restent non appariés.

Le contrôle externe du bulletin DGAC 2025 conserve l'écart entre les 19 636 085 passagers intérieurs recalculés et les 19,63 millions publiés :6 085 passagers comptés, soit 0,031%, au-delà du seul arrondi mais en deçà du seuil d'alerte fixé à 0,1%. Le bulletin et le ZIP n'ont pas la même date ; une révision est plausible mais non démontrée. De même,22,2 Mt de CO₂ en 2024 dans le CSV et22,1 Mt dans une page ministérielle sont conservés comme deux publications différentes.

Le décret n°2023-385 n'est pas utilisé comme expérience causale. Les suppressions de liaisons, les événements de 2020, le Covid, les correspondances et les changements d'offre empêchent une attribution simple avant/après 2023. La prolongation après mai 2026 n'a pas été établie dans les sources primaires consultées ; aucun statut légal postérieur ni indicateur de traitement n'est inventé.

## 13. Projections et contexte LGV

Omphale 2022 est exploité au département, sur trois scénarios officiels central, bas et haut. Les variations 2018–2050 sont conditionnelles aux hypothèses de fécondité, mortalité et migrations de l'INSEE ; les scénarios bas/haut ne sont pas des intervalles de confiance. Ils ne sont pas ventilés artificiellement à la commune et ne produisent pas de prévision de fréquentation ferroviaire.

Les trois pages LGV illustrent la collecte HTML : Atlantique, Bretagne–Pays de la Loire et Sud Europe Atlantique. Une date exacte est conservée uniquement si elle est explicitement publiée ; l'intervalle 1989–1990 n'est pas transformé en une date inventée. Cette sélection de contexte est raisonnée, non exhaustive et n'est pas jointe automatiquement aux communes pour attribuer un effet TGV.

## 14. Visualisations et limites d'interprétation

Les axes, années, unités et sources figurent sur les graphiques. Les palettes divergentes sont centrées sur zéro. Certaines cartes saturent les couleurs à des valeurs annoncées dans la légende ; cela ne tronque pas la table. Les nuages utilisent des échelles symlog pour rendre visibles les valeurs négatives et extrêmes sans les supprimer. Les tailles de points sont comprimées et leur convention est indiquée.

La commune d'implantation n'est pas le bassin de desserte. Les grandes gares, le tourisme, les correspondances, le travail à distance, les prix et les modifications d'offre peuvent modifier la fréquentation indépendamment de la démographie communale. Les données de 2022 peuvent encore refléter la reprise après le Covid. Les recensements reposent sur des enquêtes étalées, dont les estimations de petits effectifs peuvent être imprécises ; leurs mobilités ne représentent pas tous les motifs de déplacement. Une association entre rail et voiture ne démontre aucun report modal ni effet d'éviction.

## 15. Contrôles, exécution et livrables

L'audit indépendant produit `outputs/tables/validation_globale.json` : statut **CONFORME**, **72 contrôles**, **0 échec**. Il vérifie notamment les empreintes, les grains, la conservation des sommes après jointure et agrégation, l'absence de valeurs infinies, les types de codes, les cohortes, les drapeaux d'accès et les contrôles DGAC. Le total de population 2022 retrouve exactement65 846 255 habitants en métropole et67 760 573 hors Mayotte, selon les tables INSEE de référence.

Le point d'entrée est `python run.py --offline`. Le notebook `main.ipynb` reconstruit les tables depuis les archives puis expose les résultats. `--download` permet de compléter une collecte ; `--download --refresh` renouvelle les instantanés et impose une nouvelle validation. L'environnement testé est CPython3.13.9, pandas2.3.3 et NumPy2.2.6 ; les dépendances et leur verrouillage sont fournis.

Le dictionnaire des données détaille les colonnes ; le README décrit les commandes. Le rapport d'analyse existe en Markdown, HTML autonome et DOCX. Les figures sont exportées en PNG/SVG et une carte interactive autonome est fournie. Les archives volumineuses restent hors du suivi Git. Aucun dépôt distant, compte S3 ni historique de contributions humaines n'est créé ou prétendu : ces éléments d'organisation d'équipe restent à configurer par les membres.

## 16. Compléments non retenus et raisons

OpenSky exige un accès authentifié à l'historique et n'est pas nécessaire aux agrégats DGAC accessibles ; il n'est pas utilisé. Eurostat constitue une source alternative de contrôle mais n'est pas fusionné avec DGAC au risque de mélanger unités, sens et périmètres. Le GTFS courant ne mesure pas l'offre historique 2016–2022 et n'a pas été présenté comme tel. Les flux individuels domicile–travail, Filosofi, inventaires routiers territoriaux et qualité de l'air restent hors de cette version faute de série collectée et harmonisée pour ces calculs précis.

L'absence de ces enrichissements n'est pas remplacée par des données synthétiques. Le projet livre une base réelle, un socle descriptif complet et les compléments effectivement disponibles ; il distingue les questions auxquelles les données répondent de celles qui nécessitent une collecte supplémentaire.

## 17. Références et documentation détaillée

- [Fréquentation en gares, source SNCF](https://ressources.data.sncf.com/explore/dataset/frequentation-gares/).
- [Référentiel des gares voyageurs](https://ressources.data.sncf.com/explore/dataset/gares-de-voyageurs/).
- [Liste des gares SNCF Réseau](https://ressources.data.sncf.com/explore/dataset/liste-des-gares/).
- [INSEE, base de référence population 2022](https://www.insee.fr/fr/statistiques/8581709?geo=METRO-1).
- [INSEE, grille communale de densité](https://www.insee.fr/fr/information/8571524).
- [Contours administratifs Etalab 2025](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/).
- [SDES, parc de véhicules routiers](https://www.data.gouv.fr/datasets/parc-de-vehicules-routiers).
- [ADEME, documentation Impact CO₂](https://impactco2.fr/doc/api).
- [DGAC, trafic aérien mensuel](https://www.data.gouv.fr/datasets/64808a5811da153f1439914c).
- [DGAC, bulletin statistique 2025](https://www.ecologie.gouv.fr/sites/default/files/documents/Bulletin_Statistiques_transport_aerien_2025.pdf).
- [DGAC, émissions nettes annuelles de CO₂](https://www.data.gouv.fr/datasets/emissions-nettes-annuelles-de-co2-du-trafic-aerien-commercial-en-france).
- [Décret n°2023-385, Légifrance](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000047571222).
- [Code des transports, article R.6412-21](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048324552).
- [OurAirports, données](https://ourairports.com/data/).
- [Chemins de fer de Provence, gares hors SNCF](https://www.cpzou.fr/category/nos-gares/).
- Sources exactes des fichiers, paramètres API et détails de licences dans les manifestes bruts et les notes méthodologiques par famille présentes dans ce dossier.
