# Climat et avion : le rail suit-il la France qui grandit ?

Partie « empreinte climatique, projections 2050 et train face à l'avion » du projet de groupe
*Le rail suit-il la France qui grandit ? Croissance démographique, fréquentation des gares et
émissions du transport dans les territoires* (cours Python pour la data science, ENSAE, 2A).

## Questions traitées

- **Q3, empreinte climatique** : les territoires en croissance mais mal desservis par le train
  sont-ils ceux où la voiture et les émissions des trajets domicile-travail pèsent le plus ?
- **Q6, et demain ?** : où la population augmenterait-elle d'ici 2050, et que deviendrait le
  nombre d'habitants par gare à réseau constant ?
- **Q7, le train face à l'avion** : le train remplace-t-il l'avion sur les liaisons intérieures ?

## Principaux résultats

- 69 % des actifs vont travailler principalement en voiture (2022). La part de la voiture
  augmente fortement dans les 5 premiers kilomètres autour d'une gare, puis plafonne vers 85 %.
- Les communes en croissance situées à plus de 10 km d'une gare (6 615 communes, 2,2 millions
  d'actifs) ont la plus forte part de voiture (85 %) et les plus fortes émissions par actif
  (8,7 kg de CO2 par jour travaillé, contre 5,6 kg près d'une gare). Le résultat ne dépend pas
  du seuil (5, 10 ou 15 km). La desserte compte plus que la croissance démographique.
- Les émissions les plus élevées se trouvent dans les couronnes périurbaines des grandes villes.
- D'ici 2050 (scénario central INSEE), la population augmenterait surtout dans l'Ouest et le Sud,
  où l'on compte déjà le plus d'habitants par gare ; à réseau constant, cet écart se creuserait.
- En 2025, aucune liaison aérienne intérieure publiée n'a de train direct en moins de 2h30.
  Les deux tiers des passagers volent là où le train dépasse 4h ; sur les liaisons avec un
  train direct, l'avion émet environ 40 fois plus que le même trafic en TGV.

Ces résultats sont descriptifs : ils décrivent des associations, pas des effets causaux.

## Structure du dossier

```
partie_climat_avion/
├── config.yaml              paramètres : années, URL des sources, seuils, hypothèses
├── requirements.txt         bibliothèques et versions figées
├── run_all.py               refait tout : collecte, nettoyage, variables, figures
├── rapport.ipynb            rapport : statistiques, cartes, graphiques et commentaires
├── SUIVI.md                 journal des étapes, choix et hypothèses
├── src/
│   ├── outils.py            lecture de la configuration, téléchargement avec cache
│   ├── collecte.py          fonctions get_ (une par source)
│   ├── nettoyage.py         fonctions clean_ (contrôles par assert, taux de jointure)
│   ├── variables.py         fonctions build_ (TCAM, part voiture, CO2, profils, durées de train…)
│   ├── statistiques.py      tableaux par groupe (ratios de sommes)
│   └── visualisation.py     fonctions plot_ et map_ (cartes statiques et interactives)
├── donnees_manuelles/
│   └── villes_gares_aeroports.csv   table faite à la main : aéroports et gares de chaque ville
├── data/                    téléchargé et produit par run_all.py (non versionné)
│   ├── raw/                 données brutes (cache)
│   └── clean/               tables propres et tables d'analyse (Parquet)
└── figures/                 images et cartes interactives produites par run_all.py
```

## Installation et exécution

Testé sur SSP Cloud (Python 3.13). Depuis le dossier `partie_climat_avion` :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name climat_avion --display-name "Python (climat_avion)"
python run_all.py
```

`run_all.py` télécharge les sources (quelques minutes la première fois, environ 150 Mo),
puis les met en cache dans `data/raw/`. Ouvrir ensuite `rapport.ipynb` avec le noyau
`Python (climat_avion)` et exécuter toutes les cellules (Restart puis Run All).

Si un téléchargement est interrompu, supprimer le fichier incomplet dans `data/raw/`
et relancer `run_all.py`.

## Sources

| Source | Producteur | Accès | Usage |
|---|---|---|---|
| Contours des communes et départements (COG 2025) | IGN, via cartiflette | package cartiflette | fonds de carte, jointures |
| Gares de voyageurs | SNCF (ODbL) | fichier GeoJSON | distance à la gare, cartes |
| Lignes par statut | SNCF Réseau (ODbL) | fichier GeoJSON | réseau ferré en service |
| Mobilités professionnelles 2022, fichier détail | INSEE | fichier Parquet | part de la voiture, CO2 des navettes |
| Séries historiques du recensement 2023 | INSEE | fichier Parquet | population 2017 et 2023 |
| Projections Omphale 2022, scénario central | INSEE | fichier Excel | population 2050 |
| Parc de véhicules par commune | SDES (Licence Ouverte) | API DiDo | motorisation |
| Base Carbone | ADEME (Licence Ouverte) | API data-fair | facteurs d'émission voiture et train |
| Trafic aérien, séries PAP et APT | DGAC (Licence Ouverte) | fichiers CSV | liaisons et aéroports |
| Émissions de CO2 du trafic aérien | DGAC | fichier CSV | facteur d'émission de l'avion |
| Référentiel des aéroports | OurAirports (domaine public) | fichier CSV | coordonnées des aéroports |
| Horaires TGV, Intercités, TER (GTFS) | SNCF | fichier ZIP | durée du train le plus rapide |

Les adresses exactes sont dans `config.yaml`.

## Principaux choix et limites

- Période 2017-2023 (séries historiques INSEE 2023, COG 2025) ; navettes domicile-travail 2022.
- Le fichier détail des navettes est un échantillon : la part de la voiture n'est jugée fiable
  qu'à partir de 1 000 actifs ; les cartes interactives sont agrégées par département.
- CO2 des navettes : distances à vol d'oiseau entre centres de communes, un aller-retour par jour,
  un occupant par voiture (Base Carbone). C'est une borne basse.
- Distance à la gare mesurée depuis le centre de la commune ; Corse exclue (réseau CFC absent).
- La série PAP de la DGAC est soumise au secret statistique : seules les liaisons publiées
  apparaissent, et une absence n'est pas un zéro.
- Le GTFS décrit l'offre ferroviaire actuelle, pas celle de 2019 ; seuls les trains directs
  sont pris en compte.
- Avion (CO2, DGAC) et train (CO2e, ADEME) n'ont pas exactement le même périmètre :
  les comparaisons sont des ordres de grandeur.

## Contrôles de cohérence

Taux de jointure affichés par `run_all.py` (gares rattachées à 100 %, 97,7 % des voitures et
97,6 % des actifs conservés en métropole) ; comparaison avec la table de Tamsir : parc
automobile identique dans 100 % des communes, part de la voiture de 68,99 % contre 69,23 %.
