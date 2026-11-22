# Soutenance — Le rail suit-il la France qui grandit ?

Support proposé en **10 diapositives**, à adapter à la durée imposée. Les liens vers les figures et tables sont relatifs à ce document. Les notes orales accompagnent le support ; elles ne sont pas destinées à être projetées intégralement.

Les résultats ferroviaires et démographiques ci-dessous proviennent des sorties calculées du projet. **Avant présentation, relancer le pipeline et vérifier les tables associées.** L'indicateur d'éloignement est en cours de mise à jour pour exclure la Corse de son champ : aucun pourcentage antérieur n'est repris ici.

---

## Diapositive 1 — Une question territoriale, trois dimensions

**Le rail suit-il la France qui grandit ?**

- Où la population augmente-t-elle ou diminue-t-elle ?
- Dans les communes disposant de gares observées, la fréquentation évolue-t-elle dans le même sens ?
- Comment ces trajectoires s'articulent-elles avec l'usage de la voiture et les enjeux climatiques ?

**Visuel :** [carte démographique](../outputs/figures/07_carte_demographie.png).

**Notes orales :** « Notre point d'entrée est la commune d'implantation de la gare. Nous confrontons des trajectoires démographiques, des comptages ferroviaires et des indicateurs de mobilité. Nous cherchons à décrire des associations territoriales. La fréquentation ne mesure pas directement l'offre de trains, et notre analyse n'identifie pas un effet causal du rail sur la population ou sur les émissions. »

---

## Diapositive 2 — Des sources réelles et des périodes distinctes

| Dimension | Source et unité | Période utilisée |
|---|---|---|
| Fréquentation | SNCF Gares & Connexions ; gare identifiée par UIC | Description 2015–2024 ; comparaison 2016–2022 |
| Population, ménages, déplacements | INSEE ; commune entière, COG 2025 | Population historique ; comparaison 2016–2022 |
| Géographie et accessibilité approchée | Contours administratifs Etalab 2025 et coordonnées SNCF | Situation du référentiel actuel et comptages 2024 |
| Approfondissements | SDES, ADEME, Omphale, DGAC et OurAirports | Millésime propre à chaque source |

**À afficher :** « Aucune donnée aléatoire ; aucune interpolation de population pour fabriquer 2015, 2019 ou 2024. »

**Notes orales :** « Le choix de 2016–2022 n'est pas arbitraire : les deux dates sont disponibles dans les bases INSEE à géographie constante et dans la fréquentation SNCF. Les courbes 2015–2024 servent à la mise en perspective ferroviaire. Les sources complémentaires conservent leurs unités et leurs calendriers ; nous ne construisons pas une fausse série annuelle homogène. »

**Sources :** [SNCF](https://data.sncf.com/explore/dataset/frequentation-gares/), [séries historiques INSEE RP2022](https://www.insee.fr/fr/statistiques/8582555), [caractéristiques de l'emploi RP2022](https://www.insee.fr/fr/statistiques/8581424).

---

## Diapositive 3 — Une chaîne contrôlée, du fichier brut au résultat

**Collecter → archiver → typer → harmoniser → joindre → contrôler → analyser.**

- Fichiers bruts conservés ; URL et empreintes SHA-256 ; fonctionnement à partir du cache.
- Codes UIC et INSEE en chaînes ; communes entières en COG 2025 ; Paris, Lyon et Marseille sans double compte des arrondissements.
- Cohorte ferroviaire : mêmes UIC aux deux dates, comptage 2016 strictement positif, comptage 2022 disponible ; les zéros publiés restent des zéros.

**Encadré qualité :** 3 019 gares sur 3 021 rattachées à une commune ; total démographique métropolitain 2022 retrouvé : **65 846 255 habitants**. Douze communes présentent des divergences entre bases INSEE et sont exclues du croisement principal par prudence.

**À montrer si demandé :** [contrôles des jointures](../outputs/tables/qualite_jointures.json), [contrôles démographiques](../outputs/tables/controle_demographie.json), [audit global](../outputs/tables/validation_globale.json), [écarts entre sources INSEE](../data/processed/demographie_ecarts_inter_sources.csv).

**Notes orales :** « Les clés uniques et la cardinalité des jointures sont imposées dans le code. Les codes anciens passent par le COG ; les cas restants peuvent utiliser la position dans un polygone, sans affectation automatique au voisin le plus proche. Un taux de jointure élevé n'établit pas l'exactitude de chaque observation. Les divergences de versions INSEE sont exportées et signalées, plutôt que corrigées silencieusement. »

---

## Diapositive 4 — Résultat 1 : la fréquentation est très concentrée

**En 2024, les 303 gares les plus fréquentées, soit environ 10 % du fichier, concentrent 84,6 % des comptages.**

- L'indice de Gini des comptages en gare vaut **0,894**.
- La moyenne seule décrit mal cette distribution : on présente aussi médiane, quantiles et courbe de Lorenz.
- Les grandes gares peuvent dominer les résultats agrégés ; cela motive des analyses de sensibilité.

**Visuel :** [distribution et courbe de Lorenz](../outputs/figures/02_concentration.png).

**Vérification :** [distribution 2024](../outputs/tables/distribution_gares_2024.csv), [indicateurs calculés](../outputs/tables/indicateurs.json).

**Notes orales :** « Le Gini mesure ici la concentration des comptages entre gares, pas une inégalité sociale entre habitants. Le nombre de gares du décile supérieur est arrondi à l'entier supérieur. Les zéros publiés entrent dans Lorenz et Gini ; ils sont exclus uniquement du logarithme. Les comptages en gare ne représentent pas des voyageurs uniques : une même personne ou un même déplacement peut contribuer à plusieurs comptages. »

---

## Diapositive 5 — Résultat 2 : les deux croissances sont faiblement associées

**Dans les 2 618 communes du champ principal, l'association entre croissance démographique et croissance des comptages reste faible.**

- Même période 2016–2022 : **Pearson = 0,111 ; Spearman = 0,114**.
- **484 communes** combinent une population strictement en hausse et des comptages ferroviaires en baisse.
- Champ sélectionné : communes avec une cohorte de gares exploitable ; ces résultats ne décrivent pas toutes les communes françaises.

**Visuel :** [nuage de points rail–population](../outputs/figures/03_rail_population.png).

**Vérification :** [sensibilités](../outputs/tables/sensibilite_correlations.csv), [profils](../outputs/tables/profils_rail_population.csv). Attention : le profil « population ≥ 0 / rail < 0 » inclut aussi les populations exactement stables et ne correspond donc pas exactement aux 484 communes.

**Notes orales :** « Le taux annuel moyen vaut cent fois le rapport de population finale à initiale élevé à la puissance un sur six, moins un. On applique la même formule aux comptages. Les communes du champ principal réunissent environ 30,79 millions d'habitants en 2022 ; elles ne constituent pas un échantillon aléatoire de la France. La corrélation de rang reste faible hors Île-de-France et lorsque l'on modifie les seuils de fréquentation. Une baisse des comptages ne prouve ni une réduction de l'offre ni un défaut d'investissement. »

---

## Diapositive 6 — Résultat 3 : la voiture occupe une place différente selon les territoires

**En 2022, la part de la voiture parmi les actifs occupés est de 86,2 % dans le rural, contre 47,3 % dans l'urbain dense.**

| Grille officielle INSEE 2025 | Part modale voiture 2022 |
|---|---:|
| Rural | 86,2 % |
| Urbain intermédiaire | 78,7 % |
| Urbain dense | 47,3 % |

**Visuel suggéré :** transformer cette table en trois barres ; conserver l'axe de 0 à 100 %. Alternative disponible : [voiture par trajectoire démographique](../outputs/figures/04_voiture_trajectoire.png), qui répond à une question différente.

**Vérification :** [mobilités par densité](../outputs/tables/mobilites_par_densite.csv).

**Notes orales :** « Nous calculons le ratio des sommes des actifs utilisant la voiture et de l'ensemble des actifs occupés de 15 ans ou plus, dans les communes dont les données sont valides. Ce n'est pas une moyenne simple des pourcentages communaux. Le mode est celui déclaré principalement pour aller travailler ; il ne mesure pas tous les déplacements ni les distances parcourues. Les transports en commun incluent notamment bus, métro et train. Ce contraste ne permet pas d'attribuer causalement la place de la voiture à la seule présence du rail. »

---

## Diapositive 7 — Lire les évolutions à travers le choc sanitaire

**Les comptages ferroviaires s'effondrent en 2020, puis dépassent le niveau 2019 en 2024.**

- Série publiée, base 100 en 2019 : **52,3 en 2020**, puis **112,3 en 2024**.
- On confronte la série entière à une cohorte d'UIC observés sur toutes les années.
- Le choix de 2022 comme année finale du croisement doit être interprété dans ce contexte de reprise.

**Visuel :** [évolutions ferroviaires](../outputs/figures/01_evolution_rail.png).

**Vérification :** [fréquentation annuelle et indice de cohorte](../outputs/tables/frequentation_annuelle.csv).

**Notes orales :** « Un indice de 52,3 signifie une baisse d'environ 47,7 % par rapport à 2019, et non une baisse de 52,3 %. La cohorte constante limite les effets de composition liés aux gares présentes dans la série ; elle ne résout pas toutes les révisions méthodologiques. Les chiffres concernent les comptages publiés par SNCF Gares & Connexions, dont le producteur signale le caractère non exhaustif et l'absence des billets vendus par des tiers. »

---

## Diapositive 8 — L'éloignement des gares : un indicateur approché

**Nous mesurons la distance à vol d'oiseau entre un centroïde communal et une gare SNCF observée avec comptage positif en 2024.**

- Distance en Lambert 93 ; seuils de 5, 10 et 15 km.
- Champ de cet indicateur : **France métropolitaine hors Corse** ; la Corse doit apparaître en gris, comme hors champ.
- Les populations sont celles des communes classées par leur centroïde : ce n'est pas la part réelle des personnes vivant à plus de 10 km d'une gare.

**Visuel :** [carte de distance actualisée](../outputs/figures/09_carte_distance.png).

**Résultat de la version livrée :** 9 036 258 habitants résident dans les 13 670 communes dont le centroïde est à plus de 10 km d'une gare SNCF observée, soit 13,80 % des 65 494 979 habitants du champ métropolitain hors Corse. Cette proportion porte sur les populations de communes classées par leur centroïde, pas sur la localisation individuelle des habitants.

**Vérification après un renouvellement des données :** [table d'accessibilité](../outputs/tables/accessibilite_proxy.csv). Utiliser `population_champ_2022` comme dénominateur ; ne pas reprendre un ancien pourcentage incluant la Corse.

**Notes orales :** « La Corse possède un réseau ferroviaire, mais les Chemins de fer de la Corse sont hors de notre source SNCF. Une absence de source ne doit donc pas devenir une absence de train. Le fichier ne couvre pas exhaustivement le réseau RATP ou les Chemins de fer de Provence. Les distances ne sont ni routières, ni des temps d'accès ; le centroïde ne représente pas la localisation de chaque habitant. Pour la croissance, la table rapporte la somme des hausses communales positives, et non la croissance nette nationale. »

**Sources de périmètre :** [réseau des Chemins de fer de la Corse](https://cf-corse.corsica/plan-du-reseau/), [gares des Chemins de fer de Provence hors SNCF](https://www.cpzou.fr/category/nos-gares/).

---

## Diapositive 9 — Climat, avenir et avion : des approfondissements encadrés

- **Climat :** facteurs ADEME documentés et scénarios explicites ; aucune tonne « évitée par le train » présentée comme une observation sans distances et report modal mesurés.
- **Avenir :** projections Omphale départementales selon plusieurs scénarios ; elles restent conditionnelles et ne sont pas transformées en prévisions communales.
- **Avion :** trafic DGAC complémentaire, unité et sens des liaisons vérifiés ; des évolutions opposées du rail et de l'avion ne prouvent pas un report modal.

**Un visuel à choisir selon le temps :** [facteurs ADEME](../outputs/climat/facteurs_ademe.png), [scénarios départementaux 2050](../outputs/climat/projections_2050.png), [carte de projection centrale](../outputs/figures/10_carte_projections.png).

**Notes orales :** « Nous distinguons une observation, un indicateur construit et un scénario. Les facteurs d'émission servent à comparer des situations sous hypothèses ; ils ne révèlent pas le comportement qu'auraient eu les voyageurs sans train. De même, comparer le volume d'une liaison aérienne à la fréquentation des gares d'une ville ne reconstitue pas un flux ferroviaire origine-destination. Les valeurs protégées par le secret statistique restent manquantes ; l'absence d'une ligne aérienne dans le fichier ne devient pas un zéro. »

**Sources :** [API transport ADEME Impact CO₂, requête archivée](https://impactco2.fr/api/v1/transport?km=1&transports=2%2C3%2C4%2C5%2C14%2C15&displayAll=1&includeConstruction=1&occupencyRate=1), [projections territoriales INSEE Omphale](https://www.insee.fr/fr/statistiques/7747107), [trafic DGAC](https://www.data.gouv.fr/datasets/64808a5811da153f1439914c), [émissions nettes DGAC](https://www.data.gouv.fr/datasets/691dcc1b4a50a5b0a65889c8). Les paramètres, millésimes et fichiers exacts restent dans les documents de méthodologie et les manifestes de `data/raw/`. Distinguer les hypothèses du projet des définitions des producteurs.

---

## Diapositive 10 — Ce que le projet établit, et ce qu'il reste à vérifier

**Trois constats descriptifs :** forte concentration des comptages ; faible association rail–population dans le champ comparable ; forte place de la voiture dans les communes rurales.

**Limites à annoncer :** bassin de desserte plus large que la commune ; comptages non exhaustifs et révisables ; cohortes excluant les nouvelles gares sans base 2016 ; effet Covid ; indicateur de distance approché ; aucune identification causale.

**Prolongements :** mesurer l'offre réelle avec des horaires GTFS, améliorer les bassins d'accès avec la population carroyée et des temps de parcours, intégrer les autres réseaux avec des définitions compatibles.

**Contributions effectives à compléter, avec des preuves :**

| Membre | Travail effectivement réalisé | Fichiers, commits ou PR correspondants |
|---|---|---|
| Mathilde | À compléter par l'équipe | À compléter |
| Tamsir | À compléter par l'équipe | À compléter |
| Éléonore | À compléter par l'équipe | À compléter |

**Notes orales :** « Notre apport est d'abord une base traçable et une comparaison reproductible, dont les limites sont explicites. Nous ne concluons pas que le rail suit ou ne suit pas globalement la France à partir d'une seule corrélation. Nous montrons quels territoires et quelles situations méritent une étude plus précise. La répartition présentée doit refléter le travail réellement effectué ; le plan de départ n'est pas une preuve de contribution. »

---

## Questions probables du jury — à préparer hors diapositives

**Pourquoi 2016–2022 et non 2015–2024 pour le croisement ?** Parce que la même période est disponible dans les sources INSEE harmonisées et dans les comptages. Interpoler ou reprendre une population d'une autre année introduirait une information artificielle.

**Pourquoi pas une régression causale ?** Le projet décrit des territoires ; l'implantation des gares et leurs trajectoires ne sont pas aléatoires. Sans stratégie d'identification et mesures adaptées de l'offre, une régression ne suffirait pas à identifier un effet du rail.

**Pourquoi deux chiffres de comptage pour une même ville ?** Plusieurs gares peuvent être situées dans la même commune. L'agrégation porte sur des comptages, sans dédupliquer les personnes ou les correspondances. Les flux d'une gare ne sont pas les déplacements des seuls résidents de sa commune.

**Un zéro est-il une fermeture ?** Non. On conserve la valeur publiée, mais seule une source sur l'exploitation permettrait de conclure à une fermeture. Une valeur manquante, un secret statistique et un zéro sont trois situations distinctes.

**Qu'ont changé les contrôles ?** Ils ont notamment révélé des divergences entre publications INSEE malgré une géographie annoncée identique, et la nécessité de traiter la Corse hors champ de l'indicateur d'accès SNCF. Ces décisions sont documentées et reproductibles.

**Peut-on calculer exactement les émissions évitées ?** Pas avec les seuls comptages en gare. Il faudrait notamment les distances parcourues, les modes réellement remplacés, l'occupation des véhicules et un scénario de référence justifié.
