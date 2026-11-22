# Scraping documentaire des mises en service de LGV

Cette table contextualise les évolutions ferroviaires. Elle ne fournit pas un instrument causal et n'est pas jointe aux communes. La présence d'une gare dans une commune ne suffit pas à établir son exposition à une nouvelle LGV : certains trains parcourent des lignes classiques, et des territoires éloignés des infrastructures nouvelles bénéficient aussi des gains de temps.

## Échantillon et résultat effectivement extrait

Trois articles ont été choisis dans l'Ouest français, région concernée par les ouvertures de 2017. C'est un échantillon documentaire raisonné, pas une liste exhaustive des LGV ni des nouvelles dessertes.

| Article Wikipédia | Texte de la cellule « Mise en service » | Normalisation |
|---|---|---|
| [LGV Sud Europe Atlantique](https://fr.wikipedia.org/wiki/LGV_Sud_Europe_Atlantique) | 2 juillet 2017 | 2017-07-02 |
| [LGV Bretagne-Pays de la Loire](https://fr.wikipedia.org/wiki/LGV_Bretagne-Pays_de_la_Loire) | 2 juillet 2017 | 2017-07-02 |
| [LGV Atlantique](https://fr.wikipedia.org/wiki/LGV_Atlantique) | 1989 – 1990 | années minimum 1989 et maximum 1990 ; date exacte absente |

L'intervalle de la LGV Atlantique est conservé. Le projet n'invente ni jour ni mois et ne l'écrase pas en une date unique. Les mises en service SEA/BPL de juillet 2017 sont également corroborées par la [présentation des projets ferroviaires du ministère](https://www.ecologie.gouv.fr/politiques-publiques/projets-lignes-grande-vitesse). La table reste celle du scraping : les valeurs ne sont pas remplacées manuellement par une autre publication.

## Collecte respectueuse et archivage

Le script `src/contexte_lgv.py` commence par lire et archiver [robots.txt de Wikipédia francophone](https://fr.wikipedia.org/robots.txt). Il utilise `urllib.robotparser.RobotFileParser` pour vérifier chaque URL avec l'agent HTTP du projet. Toutes les pages effectivement collectées étaient autorisées. En cas d'interdiction, la procédure s'arrête explicitement, sans contourner le refus. Une pause d'au moins deux secondes sépare les requêtes de pages ; un délai plus long défini dans robots.txt serait respecté.

Les trois réponses HTML sont sauvegardées telles quelles sous `data/raw/contexte/`, avec une provenance HTTP créée par le collecteur commun. `manifest.json` conserve l'URL, la taille, la date du fichier local en UTC et son SHA-256, ainsi que l'empreinte de robots.txt. La collecte se réfère au **26 octobre 2026**. Un téléchargement n'est pas confondu avec la date d'une révision encyclopédique.

Le mode hors ligne ne sollicite pas le site et vérifie les empreintes des copies locales. Une reproduction figée utilise ces copies, car les articles et leurs modèles peuvent évoluer. `--refresh` renouvelle explicitement les fichiers. La licence éditoriale de Wikipédia est CC BY-SA ; les URL et les articles d'origine sont attribués et conservés dans chaque ligne de la table.

## Extraction et contrôles

Le module standard Python `HTMLParser` extrait le texte des cellules des tableaux. Le script sélectionne la ligne dont la première cellule est exactement « Mise en service ». Il exige une seule ligne correspondante par article. Si la structure change ou que le champ devient ambigu, il échoue au lieu d'extraire une autre date présente dans le récit.

Une expression régulière repère les années de la cellule. Une date complète en français n'est normalisée en ISO que si toute la cellule respecte le motif jour–mois–année, puis sa validité calendaire est vérifiée. Le champ brut demeure disponible. Aucune statistique de fréquentation n'est extraite de ces pages.

`data/processed/contexte_lgv.csv` comporte une ligne par LGV et les colonnes : `ligne`, `champ_html`, `mise_en_service_brute`, `date_exacte_iso_si_disponible`, `annee_min`, `annee_max`, `url_source`, `fichier_html`, `sha256_html`, `robots_autorise` et `role`. `data/raw/contexte/controle.json` récapitule les trois pages, les deux dates exactes et le délai minimal. Cette troisième méthode d'acquisition, le scraping HTML, complète les téléchargements de fichiers INSEE et l'accès API SNCF/SDES ; elle ne sert pas uniquement à découvrir des liens de téléchargement.

## Reproduction

Depuis la racine : `python -m src.contexte_lgv --offline` reconstruit la table sans réseau. Sans `--offline`, les fichiers absents sont collectés après vérification de robots.txt. Le calcul complet peut appeler `contexte_lgv.run(offline=True)`. Le module ne dépend que de la bibliothèque standard et du collecteur commun du projet.
