# Volet complémentaire aérien : protocole, sources et limites

Date de référence du projet : **26 octobre 2026**. Les heures effectives des fichiers et du manifeste sont enregistrées en UTC. Les archives collectées sont de vraies publications ; aucune observation n'est simulée. Le volet aérien complète l'analyse du rail et de la démographie. Il ne transforme pas une concomitance entre deux évolutions en preuve de report modal.

## Question et champ retenus

Question descriptive : comment le trafic commercial intérieur à la Métropole a-t-il évolué entre 2015 et 2024, notamment depuis 2019, et comment les émissions nettes de CO₂ publiées par la DGAC ont-elles évolué ? La Corse appartient au champ métropolitain. Les dessertes de l'Outre-mer sont conservées dans les sources mais ne sont pas assimilées à des liaisons substituables par le train.

Les fichiers disponibles vont jusqu'en 2025. Le résultat principal est borné à **2015–2024** pour rester comparable au projet ferroviaire ; 2025 est utilisé séparément pour un contrôle avec le bulletin statistique DGAC. Les émissions sont conservées sur toute la période disponible 2000–2024, et représentées depuis 2015. Une année de publication, une année d'observation et une date de téléchargement sont trois informations différentes.

## Sources collectées et choix

| Source primaire | Ressources réellement téléchargées | Utilisation |
|---|---|---|
| [DGAC, trafic commercial mensuel](https://www.data.gouv.fr/datasets/64808a5811da153f1439914c) | ZIP `ASP_LSN_1990_2025`, `ASP_PAP_1990_2025`, `ASP_APT_1990_2025`, notices PDF et métadonnées JSON | LSN : tendances agrégées ; PAP : observations publiées par liaison ; APT : archive complémentaire, non additionnée à LSN |
| [DGAC, émissions nettes annuelles](https://www.data.gouv.fr/datasets/emissions-nettes-annuelles-de-co2-du-trafic-aerien-commercial-en-france) | `EMI_TOT_2000_2024.csv`, `EMI_UNI_2000_2024.csv`, notice et métadonnées | Émissions en Mt CO₂ net et intensité en g CO₂ net/Peq.km |
| [Bulletin statistique DGAC 2025, édition mai 2026](https://www.ecologie.gouv.fr/sites/default/files/documents/Bulletin_Statistiques_transport_aerien_2025.pdf) | PDF | Définitions et contrôle externe du total de passagers 2025 |
| [OurAirports](https://ourairports.com/data/) | [`airports.csv`](https://davidmegginson.github.io/ourairports-data/airports.csv) | Pays, codes, coordonnées des aéroports ; référentiel communautaire courant, pas une liste officielle historique |

La DGAC diffuse les données sous Licence Ouverte 2.0. OurAirports les place dans le domaine public. Ses données évoluent quotidiennement : la copie locale et son empreinte SHA-256 fixent la version effectivement utilisée. `data/raw/aviation/manifest.json` contient pour chaque fichier l'URL exacte, la taille et l'empreinte. Les ZIP d'origine sont conservés intacts. Le script lit leurs membres sans les modifier et garde `source_member` pour retrouver le CSV initial.

Eurostat `avia_par_fr` n'est pas ajouté à la série principale : les données DGAC couvrent déjà le champ visé et un assemblage des deux producteurs exigerait de réconcilier leurs champs et leurs unités. OpenSky n'est pas utilisé : ses détections de vols ne mesurent pas directement des passagers commerciaux ; l'historique exige en outre des droits d'accès. Les données de François Geerolf ont aidé au repérage des jeux, mais aucune valeur de ce site secondaire n'est copiée à la place de la source DGAC.

## Nettoyage reproductible

`src/aviation.py` lit les CSV en UTF-8 avec BOM, séparateur point-virgule. Les codes OACI et les périodes restent initialement des chaînes. L'année et le mois viennent de la valeur `ANMOIS` réellement contenue dans les observations, sans se fier à l'ordre des membres du ZIP. Les nombres avec virgule décimale sont convertis explicitement, avec erreur bloquante en présence d'une chaîne non interprétable. Les valeurs manquantes restent manquantes ; aucune interpolation ou imputation n'est réalisée.

Les assertions vérifient l'unicité des clés mensuelles, la validité des mois, la non-négativité des mesures et la présence des douze mois pour les agrégats domestiques utilisés. Les contrôles n'effacent aucune ligne afin d'obtenir artificiellement une concordance.

La notice PAP emploie les libellés `PAP_PAX_LOC`, `PAP_PEQ_LOC` et `PAP_FRP_LOC`, tandis que l'archive téléchargée emploie `PAP_PAX`, `PAP_PEQ` et `PAP_FRP`. Le module accepte explicitement ces alias, en conservant les noms présents dans l'archive de référence. Ce décalage documentaire est signalé pour éviter un traitement fondé sur un schéma supposé.

## Deux risques majeurs : secret statistique et doubles comptes

**PAP n'est pas un recensement exhaustif des liaisons.** La publication est soumise à un seuil mensuel de 10 000 passagers équivalents et à des critères de secret statistique sur la répartition entre opérateurs. Une liaison ou un mois absent ne signifie jamais un trafic nul. Les agrégats annuels PAP sont donc nommés `passagers_observes` et accompagnés de `mois_publies` et `serie_annuelle_complete`. Même douze mois ne rendent pas ce sous-ensemble représentatif de toutes les liaisons françaises.

La copie 2026 de PAP réunit les **deux sens** d'une liaison. L'ancien intitulé de l'URL « par sens » ne décrit plus correctement le fichier téléchargé. Une paire OACI est classée suivant les règles de la DGAC, et non suivant une origine et une destination. Le module ne crée donc pas de flux dirigés artificiels.

Le trafic principal utilise les faisceaux LSN `MET_RAD` (Paris–province) et `MET_TRA` (province–province), puis les additionne pour constituer `MET_INTERIEUR`. Le bulletin distingue les flux de trafic sans double compte des mouvements dans les aéroports. Additionner départs et arrivées d'APT pour des vols domestiques compterait deux fois un même trajet. De même, les entrées/sorties de gare ne sont pas des passagers origine–destination et ne se comparent pas directement aux flux aériens.

En 2019, PAP permet d'observer 50 liaisons domestiques, dont 9 sur douze mois, totalisant 12 269 572 passagers observés. En 2024, les nombres deviennent 28 liaisons, 2 sur douze mois et 6 411 765 passagers. La variation de ce sous-ensemble reflète aussi la publication sélective. La table `outputs/aviation/couverture_pap_metropole.csv` expose chaque année le rapport des passagers PAP observés au total LSN ; ce rapport est un diagnostic de couverture, pas un taux à appliquer pour redresser les liaisons.

## Appariement géographique

Une paire `PAP` est séparée en deux codes OACI. Chacun est joint au champ `ident` d'OurAirports par une jointure `many_to_one`, après contrôle d'unicité. Les noms ne servent jamais de clé de remplacement. Un aéroport domestique métropolitain est identifié par un code commençant par `LF` et le pays `FR` dans le référentiel. Cette règle inclut la Corse et Bâle-Mulhouse et écarte les codes ultramarins.

OurAirports est courant, alors que le trafic est historique : certains codes internationaux ont changé ou disparu. Les échecs restent visibles dans `outputs/aviation/aeroports_non_apparies.csv` et les taux d'appariement sont publiés. Un code non apparié n'est pas reclassé automatiquement comme français. Les coordonnées ne sont pas jointes aux communes et ne produisent pas d'estimation de population d'un bassin aéroportuaire.

## Variables et tables livrées

Toutes les tables propres sont fournies en CSV UTF-8 avec BOM et en Parquet, sous `data/processed/`.

| Table | Unité et clé | Mesures principales |
|---|---|---|
| `aviation_trafic_mensuel` | mois × faisceau domestique ; `ANMOIS, LSN_SEG, LSN_FSC, LSN_1, LSN_2` | passagers locaux `LSN_PAX`, dessertes `LSN_DRT` |
| `aviation_trafic_annuel` | année × faisceau ; `annee, LSN_FSC` | `passagers`, `dessertes`, `mois_observes`, `indice_2019_100` |
| `aviation_pap_mensuel_observe` | mois × paire publiée ; `ANMOIS, PAP` | passagers, distance orthodromique, dessertes, pays/coordonnées aux deux extrémités |
| `aviation_pap_annuel_observe` | année × paire publiée ; `annee, PAP` | `passagers_observes`, `mois_publies`, `serie_annuelle_complete` |
| `aviation_emissions_annuelles` | année × faisceau × unité ; `annee, faisceau, unite` | `valeur`, unité explicitement stockée |
| `aviation_aeroports_referentiel` | aéroport ; `icao` | nom, pays, latitude/longitude en degrés WGS84, IATA, type |

L'indice vaut `100 × passagers(année) / passagers(2019)` dans chaque faisceau. Les variations en pourcentage valent `100 × (valeur finale / valeur initiale − 1)`. Les mesures PAP utilisent les passagers réels, et non les passagers équivalents, qui combinent passagers et fret. `PAP_DIST` est une distance orthodromique dont l'unité n'est pas explicitée dans la notice : ses valeurs brutes sont conservées sans être utilisées dans les analyses. Les colonnes de passagers.km de LSN sont préservées dans les sources mais ne sont pas utilisées pour les conclusions : la notice exprime des milliards alors que l'échelle numérique de l'archive nécessite une vérification supplémentaire.

## Contrôles externes et écarts conservés

Le bulletin DGAC de mai 2026 fournit les chiffres 2025 en millions à deux décimales. Le ZIP LSN, publié en juillet 2026, est postérieur. Le recalcul donne 11 425 451 passagers radiaux et 8 210 634 transversaux, compatibles avec les valeurs publiées 11,43 et 8,21 millions. Leur somme, 19 636 085, diffère de 19,63 millions de **6 085 passagers**, soit **0,031 %**. Cet écart dépasse l'arrondi de 0,005 million ; il est conservé explicitement. Une révision postérieure est possible, mais n'est pas établie par une table de révisions. Le script distingue concordance à l'arrondi et seuil d'alerte de 0,1 %, qui détecterait une erreur de champ importante. La tolérance ne transforme pas l'écart observé en égalité.

Deux publications officielles des émissions 2024 diffèrent également : le CSV DGAC daté du 19 novembre 2025 donne **22,2 Mt de CO₂ net** pour `FRANCE_TOT` ; la [page ministérielle du 16 septembre 2025](https://www.ecologie.gouv.fr/politiques-publiques/emissions-gazeuses-liees-trafic-aerien) annonce 22,1 Mt pour le transport commercial de passagers. La date et le champ peuvent contribuer à l'écart, sans preuve permettant de le décomposer. Le projet utilise systématiquement les CSV DGAC, sans remplacer une cellule par le chiffre de communication. Les sommes des composantes peuvent également différer du total à cause des arrondis à 0,1 Mt.

## Résultat descriptif et portée

LSN mesure **26 753 422** passagers commerciaux intérieurs métropolitains en 2019 et **20 160 921** en 2024 : **−24,64 %**. C'est une baisse de trafic, pas une mesure de voyageurs ayant choisi le train. Le choc sanitaire, la demande de voyages professionnels, les prix, l'offre et les changements du réseau aérien sont des explications concurrentes que ces données agrégées ne permettent pas d'isoler.

Les émissions DGAC incluent les carburants d'aviation durables dans leur calcul net. Elles mesurent du CO₂, sans représenter l'ensemble des effets climatiques non-CO₂ de l'aviation. L'intensité est par **passager équivalent.km**, qui tient compte du fret ; elle ne devient pas automatiquement un facteur de CO₂e par voyageur.km comparable à l'ADEME. Le projet ne multiplie donc pas ces valeurs par des entrées/sorties en gares et ne produit pas d'« émissions évitées observées ».

## Politique publique : vérification au 26 octobre 2026

Le [décret n° 2023-385](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000047571222) prévoyait une durée d'application de trois ans à compter du 24 mai 2023. La codification dans [l'article R.6412-21 du Code des transports](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048324552), consulté dans sa version courante, conserve cette limite. Le [compte rendu de l'Assemblée nationale du 30 avril 2026](https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/session-ordinaire-de-2025-2026/deuxieme-seance-du-jeudi-30-avril-2026.pdf) évoque une intention de prolongation et des discussions avec la Commission européenne ; une intention n'est pas un texte de prorogation.

**La prolongation au-delà du 24 mai 2026 n'est pas établie par les sources primaires retrouvées.** Le projet n'affirme donc pas qu'elle a eu lieu, et ne construit aucune indicatrice de traitement postérieure à cette date. Le [CGDD](https://www.notre-environnement.gouv.fr/actualites/breves/article/emissions-de-co2-certaines-lignes-aeriennes-interieures-desormais-interdites) indique que les trois liaisons Orly–Nantes, Orly–Lyon et Orly–Bordeaux étaient déjà suspendues au moment de leur interdiction officielle en 2023. Une simple comparaison avant/après 2023 attribuerait donc à tort à la date du décret une rupture antérieure. Le volet reste descriptif.

## Reproduction

Depuis la racine du projet : `python -m src.aviation --offline` recalcule les tables, les contrôles, les deux figures PNG et `outputs/aviation/indicateurs.json` depuis les fichiers conservés. `python -m src.aviation` télécharge uniquement les fichiers absents avant de recalculer. `--refresh` renouvelle explicitement les sources et leurs empreintes ; les résultats peuvent alors évoluer si le producteur révise les données. Le rapport global doit appeler `run(root, offline=True)` pour une reproduction figée.
