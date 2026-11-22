# Données démographiques et déplacements : décisions méthodologiques

Document de travail du 26 octobre 2026. Le programme `src/demographie.py` construit les tables ; les effectifs et résultats de contrôle sont enregistrés automatiquement dans `outputs/tables/controle_demographie.json`.

## Périmètre et calendrier

L'unité est la **commune entière dans la géographie du 1er janvier 2025**. Les bases RP2022 contiennent les résultats des recensements antérieurs recalculés dans cette même géographie. On utilise cette rétropolation officielle plutôt que d'additionner des populations publiées à des géographies différentes. Paris, Lyon et Marseille sont conservées comme communes entières ; leurs arrondissements municipaux sont exclus pour éviter un double compte. Les communes des quatre DROM présentes dans le fichier sont conservées, avec `metropole=False`. Mayotte est hors du champ de ces bases.

Le millésime 2022 est l'année de référence du recensement, et **ne désigne pas une observation exhaustive réalisée le même jour dans toutes les communes**. Les bases exploitées sont les fichiers RP2022, publiés en géographie 2025. Les résultats harmonisés RP2023 en géographie 2026 sont également annoncés dans le catalogue ; ils ne sont pas mélangés à ce socle, afin de maintenir le même périmètre et la même définition des variables entre les sources.

La comparaison principale avec le rail porte sur **2016–2022**, période commune aux populations et aux fréquentations. La description ferroviaire 2015–2024 et les indices base 100 en 2019 constituent des analyses distinctes. Aucune population communale 2015, 2019 ou 2024 n'est interpolée ou assimilée à une autre année. La série longue conserve seulement les années effectivement diffusées.

## Sources archivées

Les fichiers ZIP originaux et les pages de présentation restent dans `data/raw/insee/`. Leur taille, URL et empreinte SHA-256 figurent dans `manifest_insee.json`. Les dictionnaires de variables officiels contenus dans les ZIP sont également extraits sans modification. Le mode `--offline` repart de ces fichiers ; le mode normal réutilise le cache. `--refresh` est nécessaire pour remplacer explicitement une version.

| Source officielle | Fichier | Utilisation |
|---|---|---|
| [Séries historiques RP2022](https://www.insee.fr/fr/statistiques/8582555) | `base-cc-serie-historique-2022_csv.zip` | Populations 1968, 1975, 1982, 1990, 1999, 2006, 2011, 2016, 2022 ; naissances, décès et superficie |
| [Évolution et structure de la population RP2022](https://www.insee.fr/fr/statistiques/8581696) | `base-cc-evol-struct-pop-2022_csv.zip` | Contrôle des populations 2011, 2016 et 2022 dans une seconde base officielle |
| [Logement RP2022](https://www.insee.fr/fr/statistiques/8581474) | `base-cc-logement-2022_csv.zip` | Ménages et équipement automobile, 2011, 2016, 2022 |
| [Caractéristiques de l'emploi RP2022](https://www.insee.fr/fr/statistiques/8581424) | `base-cc-caract_emp-2022_csv.zip` | Actifs occupés de 15 ans ou plus et mode principal de déplacement, 2016 et 2022 |
| [Emploi et population active RP2022](https://www.insee.fr/fr/statistiques/8581444) | `base-cc-emploi-pop-active-2022_csv.zip` | Base complémentaire archivée ; elle n'est pas utilisée comme source de la part modale |
| [Code officiel géographique 2025](https://www.insee.fr/fr/information/8377162) | Communes, départements, régions et mouvements | Noms, clés administratives, exclusion des arrondissements et passage des communes déléguées à leur commune parente |
| [Grille de densité 2025](https://www.insee.fr/fr/information/8571524) | `fichier_diffusion_2025.xlsx`, onglet `Maille communale` | Classification officielle à trois et sept niveaux, et distinction du rural périurbain |

Les téléchargements directs ont la forme `https://www.insee.fr/fr/statistiques/fichier/IDENTIFIANT/NOM_FICHIER`. Le script conserve ces adresses exactes. Les fichiers sont publics, diffusés sous Licence Ouverte ; l'Insee reste à citer comme producteur.

## Nettoyage et jointures

Les codes communaux, départementaux et régionaux sont lus en chaînes de caractères. On préserve ainsi les zéros initiaux et les codes corses `2A` et `2B`. Une clé communale doit avoir cinq caractères. Les colonnes numériques conservent leurs décimales : certains effectifs résultent d'estimations ou de pondérations du recensement. L'arrondi intervient uniquement à l'affichage.

La base historique est jointe au COG avec la condition `TYPECOM=COM`, puis aux données logement et mobilité. Chaque jointure impose une clé unique et la cardinalité `one_to_one`. Les effectifs des jointures sont contrôlés et exportés. Un code absent, une valeur non publiée ou un dénominateur nul donnent une valeur manquante ; aucune imputation arbitraire ne transforme cette situation en zéro. Les six communes détruites et non habitées qui possèdent une population nulle ne sont pas supprimées du fichier communal ; leurs taux non définis restent manquants.

Le fichier `demographie_passage_cog2025.csv` fournit le passage officiel des communes associées, déléguées et arrondissements encore présents dans le COG 2025 vers `COMPARENT`. Si un code désigne déjà une commune entière en vigueur, son identité a priorité. **Cette table n'est pas une correspondance exhaustive de toutes les communes disparues depuis 2015** : les autres codes doivent être examinés avec les mouvements du COG ou la localisation de la gare. Une scission ne permet pas de répartir sans information supplémentaire une ancienne population agrégée entre ses nouvelles communes. Les populations historiques employées ici proviennent de la rétropolation de l'Insee ; on ne les répartit pas soi-même.

## Indicateurs construits

Pour une population positive aux deux dates :

\[
TCAM_{a,b}=100\left[\left(\frac{P_b}{P_a}\right)^{1/(b-a)}-1\right].
\]

La croissance cumulée entre 2016 et 2022 est `100*(P2022/P2016-1)`, et la variation en effectif `P2022-P2016`. Pour l'analyse par trajectoire, `declin` désigne un TCAM inférieur à −0,2 %, `stable` un TCAM compris entre −0,2 % et +0,2 % inclus, et `croissance` un TCAM supérieur à +0,2 %. Ce seuil descriptif évite de classer une variation minime dans une trajectoire forte ; **il ne constitue pas un test de significativité**. La variable quantitative reste disponible et doit accompagner l'interprétation.

Le solde naturel 2016–2022 est calculé avec les naissances et décès domiciliés du **1er janvier 2016 au 31 décembre 2021**, période correspondant à la variation entre les références du 1er janvier 2016 et du 1er janvier 2022. Le solde migratoire est un **solde apparent** : `P2022-P2016-(naissances-deces)`. Il contient les mouvements de population ainsi que les écarts de mesure, ajustements et effets méthodologiques. On ne le présente pas comme un comptage de personnes ayant déménagé. Le changement de questionnaire de 2018 lié à la multirésidence peut affecter les évolutions infranationales ; la source historique attire explicitement l'attention sur cette limite.

La densité est `population_2022/superficie_km2`. Elle est continue et n'est pas assimilée à la grille officielle de densité de l'Insee.

La classification officielle est jointe séparément avec `classe_densite_3`, `libelle_densite_3`, `classe_densite_7` et `libelle_densite_7`. Le fichier retenu est **la grille 2025 dans la géographie2025**, et non son actualisation géographique2026 proposée en premier sur la page actuelle. Elle repose sur la répartition de la population du RP 2021 sur des carreaux, et non sur un simple seuil de densité moyenne communale. Les catégories et leurs libellés sont repris du fichier, sans reclassement personnel. `classe_densite_aav` et `libelle_densite_aav` conservent le croisement avec les aires d'attraction des villes. Cette grille sert de typologie structurelle fixe ; on ne l'interprète pas comme un changement observé de ruralité entre 2016 et 2022.

La part de ménages motorisés est `100*RP_VOIT1P/MEN`. Le suffixe `VOIT1P` désigne **au moins une voiture**, `VOIT1` exactement une et `VOIT2P` deux ou plus. On vérifie les cohérences entre effectifs. Le nombre exact de voitures n'étant pas fourni par la classe « deux ou plus », `(VOIT1+2*VOIT2P)/MEN` est nommé **borne inférieure du nombre de voitures par ménage** ; il ne doit pas être présenté comme la motorisation moyenne exacte ou le parc SDES.

Les parts modales voiture et transports collectifs sont respectivement `100*ACTOCC15P_VOITURE/ACTOCC15P` et `100*ACTOCC15P_COMMUN/ACTOCC15P`. Le dénominateur inclut l'ensemble des actifs occupés de 15 ans ou plus résidents, y compris les personnes sans déplacement. C'est le mode principal déclaré du trajet domicile-travail, pas une part des distances parcourues ou de tous les motifs de déplacement. **Transports en commun ne signifie pas train** : le bus, le métro et les autres modes collectifs sont inclus. Une diminution de la part voiture n'établit donc pas, à elle seule, un report vers le rail.

En 2016, la classe « deux-roues » ne sépare pas vélo et deux-roues motorisé ; en 2022 les deux classes sont distinctes. Le script ne construit aucune fausse évolution vélo 2016–2022. Il vérifie pour chaque année que la somme des modes reconstitue l'effectif total des actifs occupés.

## Contrôles et interprétation statistique

Le script contrôle les clés, la concordance des deux bases de population, les taux compris entre 0 et 100 %, la somme des modes et les totaux de population. Les références publiées sont **65 846 255 habitants en France métropolitaine en 2022** et **67 760 573 dans le champ France hors Mayotte** : [fiche INSEE France métropolitaine](https://www.insee.fr/fr/statistiques/8581709?geo=METRO-1), [fiche France entière](https://www.insee.fr/fr/statistiques/8581709?geo=FE-1). L'égalité des agrégats est exigée à une unité près pour tolérer uniquement l'arithmétique flottante.

**Résultat de l'audit des versions effectivement téléchargées.** La série historique contient 34 858 communes entières, dont 34 746 en métropole, et 45 arrondissements retirés. Ses totaux 2022 reproduisent exactement les deux références nationales. Les deux autres jointures trouvent une ligne pour chacune des 34 858 communes ; cela ne supprime pas les valeurs non publiées présentes dans les colonnes sources.

La seconde base de population n'est **pas parfaitement concordante** avec la série historique, malgré l'annonce du même millésime géographique. Avec un seuil de signalement de 0,5 habitant, on repère1commune en2022,12en2016 et15en2011. Exemple : `15141`, Neussargues-Moissac, donne 834 habitants 2022 dans la série historique et 1 577 dans la base évolution-structure, après une scission connue du COG 2025. Les écarts et les deux valeurs sont publiés dans `demographie_ecarts_inter_sources.csv` ; on ne les efface pas en remplaçant arbitrairement l'une des données. Les populations de l'analyse restent celles de la série historique unique pour toutes les années.

`alerte_population_inter_sources_ANNEE` signale ces écarts. Le seuil de 0,5 habitant évite de traiter comme une rupture de périmètre de simples résidus numériques inférieurs à un demi-habitant ; les différences substantielles restent visibles. `alerte_menages_inter_sources_ANNEE` vérifie de même les ménages de la base logement contre les résidences principales de la série historique. Par prudence, les ratios motorisation et mobilité de l'année concernée sont neutralisés si l'un de ces deux signaux est présent. Les effectifs bruts restent disponibles avec leur indicateur d'alerte. Le flag synthétique `alerte_comparabilite_rail_population` identifie les 12 communes présentant une divergence de population en 2016 ou 2022 ; il permet une analyse de sensibilité du croisement rail-démographie. Une divergence de versions est un signal à examiner, pas une preuve automatique que tous les indicateurs de la commune sont faux.

Pour agréger un ratio par région, on calcule le ratio des sommes des numérateurs et des dénominateurs. La moyenne simple des parts communales répondrait à une autre question en donnant le même poids à une petite commune et à une métropole. Les corrélations entre communes sont descriptives ; elles ne mesurent pas l'effet causal d'une gare, de l'offre ferroviaire ou d'une politique.

Les petites cellules du recensement peuvent être imprécises. Les comparaisons des parts modales de très petites communes doivent être agrégées ou accompagnées d'une réserve explicite. Un effectif faible n'est pas un signal fiable d'évolution. La fréquentation d'une gare relève d'un bassin de desserte qui dépasse sa commune d'implantation : le croisement communal est une convention reproductible, pas l'identification du territoire réel de tous les voyageurs.

## Fichiers propres

- `demographie_communes.parquet` et `.csv` : une ligne par commune entière, avec les indicateurs et les indicateurs de réussite de jointure.
- `demographie_population_long.parquet` et `.csv` : une ligne par commune et année effectivement publiée, 1968 à 2022.
- `demographie_passage_cog2025.csv` : correspondances administratives définies ci-dessus.
- `demographie_codes_exclus.csv` : codes d'arrondissements municipaux retirés pour éviter les doubles comptes.
- `demographie_densite2025.csv` : classification officielle de densité dans la géographie2025.
- `demographie_ecarts_inter_sources.csv` : divergences documentées entre deux bases officielles de population.

Dans les DROM, les colonnes intitulées 1968 et 1975 renvoient respectivement aux recensements 1967 et 1974, conformément à la source. Les comparaisons historiques nationales et les cartes de France métropolitaine doivent préciser leur champ. La Corse appartient bien au champ métropolitain.
