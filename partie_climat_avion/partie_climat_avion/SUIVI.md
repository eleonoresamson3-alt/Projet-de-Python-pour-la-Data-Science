# Suivi de ma partie : climat et avion

Environnement : SSP Cloud (VS Code), dossier `~/work/partie_climat_avion`, Python 3.13.
À chaque nouveau terminal : `cd ~/work/partie_climat_avion` puis `source .venv/bin/activate`.
Notebook : choisir le noyau `.venv` de partie_climat_avion. Les téléchargements se font
dans le terminal (cartiflette ne fonctionne pas dans un notebook), le notebook ne fait que lire.
Pas de Git pour l'instant : tout sera poussé à la fin dans le dépôt du groupe.

## Étape en cours

Phase 6 (README, rapport final, test dans un .venv neuf) : à démarrer.

## Journal des étapes validées

Phase 0 (mise en place)
- 0.1 : dossiers (src, data/raw, data/clean, notebooks, figures) et .gitignore
- 0.2 : .venv et requirements.txt avec versions figées (+ ipykernel, openpyxl ajoutés ensuite)
- 0.3 : config.yaml
- 0.4 : src/outils.py avec charger_config() et get_fichier() (téléchargement avec cache)
- 0.5 : squelette de run_all.py
- 0.6 : SUIVI.md

Phase 1 (collecte), toutes les fonctions sont dans src/collecte.py
- 1.1 : get_contours() : cartiflette, COG 2025, 34 875 communes (clé INSEE_COM), 101 départements (INSEE_DEP)
- 1.2 : get_gares() : SNCF Gares de voyageurs, 2 792 gares (codeinsee, codes_uic)
- 1.3 : get_lignes() : SNCF Réseau Lignes par statut, 1 638 tronçons dont 787 « Exploitée »
- 1.4 : get_mobpro() : INSEE navettes domicile-travail 2022, 7 388 023 lignes, 28,4 M actifs (somme IPONDI)
- 1.5 : get_facteurs_carbone() : API Base Carbone ADEME, 4 facteurs
- 1.6 : get_population() : INSEE séries historiques 2023 (COG 2025), format long
- 1.7 : get_parc_auto() : API DiDo SDES, voitures des particuliers 2017 et 2023 (35,9 M en 2023)
- 1.8 : get_projections() : INSEE Omphale 2022, scénario central, par département (en milliers)
- 1.9 : get_pap() : DGAC série PAP 2019 et 2025
- 1.10 : get_apt() : DGAC série APT 2019 et 2025
- 1.11 : get_emissions_avion() : DGAC, g CO2 / passager équivalent.km (intérieur métropole : 125,3 en 2019, 117,2 en 2024)
- 1.12 : get_aeroports() : OurAirports (clé ident = code OACI)
- 1.13 : get_gtfs() : GTFS national SNCF (offre du 21/11/2026 au 30/04/2027)
- 1.14 : get_table_villes() : donnees_manuelles/villes_gares_aeroports.csv (14 villes)
- 1.15 : run_all.py lance toute la collecte

Phase 2 (nettoyage), fonctions dans src/nettoyage.py
- 2.1 : clean_communes() : métropole Corse comprise (34 746 communes), Lambert 93, assert clé unique
- 2.2 : clean_gares() : explode des codes UIC (2 792 gares -> 2 805 lignes), Lambert 93, assert UIC unique à 8 chiffres
- 2.3 : clean_gares_communes() : 100 % des gares rattachées ; code SNCF gardé s'il existe au COG 2025
  (95,4 % identiques), sinon jointure spatiale (75 codes obsolètes : arrondissements, fusions) ;
  54 gares près d'une limite gardent leur code SNCF (contours cartiflette simplifiés)
- 2.4 : clean_lignes() : statut « Exploitée », 787 tronçons, environ 27 000 km
- 2.5 : clean_population() : filtre COM/POP, pivot_table 2017/2023, 34 858 communes, 68,1 M hab. en 2023
- 2.6 : clean_code_arrondissement() et clean_parc_auto() : arrondissements PLM regroupés, 34 854 communes
- 2.7 : clean_mobpro() : codes au COG 2025, modes en clair ; 69 % des actifs en voiture (France)
- 2.8 : clean_projections() : 96 départements, en habitants (x 1000) ; évolution calculée dans les projections
- 2.9 : clean_facteurs() : dictionnaire {mode: kgCO2e/km}
- 2.10 : clean_liaisons() : 54 liaisons intérieures, passagers 2019 et 2025, NaN gardés (secret statistique)
- 2.11 : clean_aeroports() : 62 aéroports de métropole, merge OurAirports 100 % (ZZMT = « autres » retiré)
- 2.12 : clean_emissions_avion() : 0,1172 kg CO2/passager.km (2024)
- 2.13 : clean_horaires() : trains seulement (route_type 2), UIC = 8 derniers caractères, heures en minutes
  (contrôle : Paris Gare de Lyon -> Lyon Part-Dieu en 113 min)
- 2.14 : clean_departements() et run_all.py enregistre 11 tables dans data/clean/
  (métropole : 97,7 % des voitures et 97,63 % des actifs gardés, le reste = DOM et codes inconnus)
- 2.15 : clean_controle_tamsir() : parc 2023 identique à 100 % ; part voiture 68,99 % contre 69,23 %

Phase 3 (variables), fonctions dans src/variables.py
- 3.1 : build_tcam() : TCAM 2017-2023 ; France +0,39 %/an ; commune médiane +0,04 %/an ; 6 non définis
- 3.2 : build_part_voiture() : part voiture par commune + drapeau part_fiable (>= 1 000 actifs :
  4 567 communes, 74 % des actifs) ; Paris 9 %, Lyon 29 %, Marseille 52 %
- 3.3 : build_motorisation() : voitures pour 1 000 hab. (médiane 660, Paris 189) ; 68 communes > 1 500
  (immatriculations atypiques dans de toutes petites communes) : décrire par la médiane
- 3.4 : build_distance_gare() : centre de commune -> gare la plus proche (sjoin_nearest) ;
  médiane 8,4 km, max 53 km ; Corse non calculée ; écart médian avec Tamsir : 0 km
- 3.5 : build_co2_navettes() : flux voiture x distance à vol d'oiseau x 2 trajets x 0,256 kg/km ;
  environ 166 000 t de CO2 par jour travaillé (borne basse) ; Paris 0,85 kg/actif/jour, rural de l'Ain 9 kg
- 3.6 : build_table_communes() : une table de 34 746 communes, toutes variables
- 3.7 : build_profils() : 4 profils (TCAM > 0 ; gare à 10 km ou moins) ;
  en croissance et loin d'une gare : 8 % des habitants, 85 % de voiture, 8,7 kg CO2/actif/jour
  (contre 67,6 % et 5,6 kg en croissance et proche d'une gare) ; la desserte joue plus que la croissance
- 3.8 : run_all.py enregistre data/clean/table_communes.parquet
- 3.9 : build_duree_train() : train direct le plus rapide entre villes (GTFS) ; 49 paires reliées
  (Paris-Lille 1h00, Paris-Lyon 1h53, Paris-Bordeaux 2h02, Paris-Marseille 3h02, Paris-Nice 5h34)
- 3.10 : build_liaisons_avion() : 45 liaisons sur 54 dans la table des villes ; classes de durée ;
  CO2 avion et équivalent TGV ; aucune liaison publiée de moins de 2h30 en 2025
- 3.11 : build_departements() : évolution projetée 2023-2050 et gares pour 100 000 hab. ;
  forte croissance à l'Ouest et au Sud (Loire-Atlantique +18 %, Hérault +17 %, 1,7 gare/100 000 hab.)
- 3.12 : run_all.py enregistre table_departements.parquet et table_liaisons.parquet

Phase 4 (statistiques descriptives), notebook rapport.ipynb (à la racine) + src/statistiques.py
- 4.1 : rapport.ipynb à la racine (noyau .venv), lit les 3 tables de data/clean
- 4.2 : description de la base : 34 746 communes, 66,2 M hab., 27,7 M actifs, 4 567 communes fiables
- 4.3 : distributions (médianes) : TCAM 0,0 %/an, voiture 83 % (fiables), 8,4 km d'une gare, 6,9 kg CO2/actif/jour
- 4.4 : build_resume_groupes() : tableau par profil (ratios de sommes)
- 4.5 : sensibilité 5 / 10 / 15 km : +20 points de voiture et +50 à 60 % de CO2 loin d'une gare, quel que soit le seuil
- 4.6 : corrélations de Spearman (communes fiables) : distance-voiture 0,39 ; distance-CO2 0,30 ; TCAM ~ 0
- 4.7 : Q6 : 6 départements à plus de 10 % de croissance d'ici 2050, 3,6 gares/100 000 hab. (5,2 en déclin) ;
  Spearman évolution / gares par hab. = -0,40 (Corse exclue)
- 4.8 : Q7 : aucune liaison publiée < 2h30 en 2025 ; 67,6 % des passagers où le train dépasse 4h, 25,1 % sans train direct ;
  Roissy-Marseille -66 %, Orly-Toulouse -54 % depuis 2019, Paris-Nice stable ; avion ~40 fois le TGV en CO2
  Piège : Series.corr(method="spearman") demande scipy, utiliser DataFrame.corr


Phase 5 (cartes et graphiques), fonctions dans src/visualisation.py, figures dans figures/
- 5.1 nuage part voiture × distance (médiane par tranche de 2 km) : forte hausse jusqu'à 5 km puis plateau
- 5.2 heatmap des corrélations (Spearman, triangle bas, palette divergente centrée sur 0)
- 5.3 carte 4 statique (CO2 par actif, commune) : couronnes périurbaines les plus émettrices
- 5.4 carte 7 statique (évolution 2023-2050 par département)
- 5.5 nuage distance × passagers (log), couleur = durée du train ; palette vérifiée daltonisme
- 5.6 carte 8 statique (arcs, noms des villes, légende des classes présentes)
- 5.7 carte 8 interactive (folium : surbrillance, infobulles, encadré légende)
- 5.8 carte 7 interactive (habitants par gare 2023 / 2050 au survol)
- 5.9 carte 4 interactive, agrégée par département (19 Mo par commune -> 1,2 Mo ; plus fiable)
- 5.10 carte des 4 profils : 6 615 communes en croissance à plus de 10 km d'une gare, 2,2 M d'actifs
- 5.11 barres Q6 : 10 plus fortes hausses / baisses, habitants par gare (Hérault ~58 000 -> ~68 000)
- 5.12 barres CO2 avion / TGV : rapport 40 sur 13 liaisons avec train direct
- 5.13 boîtes à moustaches par taille de commune : voiture 88 % (< 500 hab.) -> 41 % (> 200 000)
- 5.14 carte 9 : 54 aéroports contre 2 792 gares
- 5.15 run_all.py régénère les 14 figures
  Fond folium : Esri.WorldGrayCanvas (CARTO demande une clé) ; map_fond_france() règle le zoom.
  Notebook : une seule cellule de chargement en haut (tous les imports), puis Restart + Run All.

## Choix et décisions

- Ma propre collecte et mes propres jointures. La table de Tamsir (dataset_final_communes.csv)
  sert uniquement de contrôle de cohérence en phase 2.
- Période 2017-2023 (séries historiques INSEE 2023, même COG 2025 que Tamsir).
  Tamsir utilise 2016-2022 : écart d'un an à signaler dans le rapport.
- Navettes domicile-travail : millésime 2022 (photo de la situation, pas d'évolution).
- Facteurs d'émission : Base Carbone de l'ADEME (Tamsir utilise Impact CO2, même producteur).
- Avion : 2019 (avant Covid) et 2025 (dernière année complète DGAC).
- Pas de total d'« émissions évitées » calculé à partir de la fréquentation des gares.
  À la place : CO2 des navettes en voiture (flux INSEE), puis un scénario hypothétique
  de report vers le train, avec ses hypothèses écrites dans config.yaml.

## Points du nettoyage (phase 2, traités)

- Codes INSEE et UIC en texte (zéros initiaux), projection Lambert 93 (EPSG:2154) pour les distances.
- Contours : retirer les DOM (pas de réseau SNCF).
- Gares : 11 gares ont plusieurs codes UIC séparés par « ; ».
- Lignes : garder statut « Exploitée ».
- Navettes : DCLT utilise les arrondissements de Paris, Lyon, Marseille (à ramener à la commune) ;
  66 codes commune hors COG 2025 ; sommer IPONDI, ne jamais compter les lignes.
- Population : filtrer GEO_OBJECT == "COM" et RP_MEASURE == "POP", pivot 2017 / 2023.
- Parc auto : plusieurs lignes par commune (carburant, Crit'Air) à sommer ; code 00000 = inconnu ;
  COG du SDES non précisé.
- Projections : populations en milliers.
- DGAC PAP : liaisons intérieures = deux codes « LF » ; une absence n'est pas un zéro (secret statistique).
- GTFS : garder route_type == "2" (train) ; heures pouvant dépasser 24:00 ; trains directs seulement.

## Hypothèses chiffrées (avec source)

- Voiture : 0,256 kgCO2e/km par véhicule (Base Carbone 43791, motorisation moyenne 2023).
  Hypothèse : un seul occupant pour les navettes domicile-travail.
- TER : 0,0277 kgCO2e/passager.km (Base Carbone 43255, 2022).
- Intercités : 0,0075 kgCO2e/passager.km (Base Carbone 43272, 2022).
- TGV : 0,00293 kgCO2e/passager.km (Base Carbone 43256, 2022).
- Avion intérieur métropole : 117,2 g CO2/passager équivalent.km en 2024 (DGAC).
  Attention : CO2 seul (DGAC) contre CO2e (ADEME), périmètres différents.

## Limites à écrire dans le rapport

- Lignes SNCF Réseau mises à jour en 2022.
- DGAC PAP soumise au secret statistique : 31 liaisons intérieures publiées en 2025 ; top 20 « des liaisons publiées ».
- GTFS = offre actuelle, pas celle de 2019 ; Corse (CFC) absente des données SNCF.
- Fichier détail des navettes = échantillon : part modale imprécise dans les petites communes
  (écart médian avec Tamsir : 5,4 points sous 200 actifs, 0,5 point au-dessus de 5 000).
  Présenter la part voiture et le CO2 par actif à une échelle plus large ou signaler les petites communes.
- Actifs travaillant à l'étranger (code 99999, environ 495 000) : gardés pour la part modale,
  exclus du calcul de CO2 (distance inconnue).
- Le cache de get_fichier vérifie l'existence d'un fichier, pas qu'il est complet :
  supprimer à la main un fichier tronqué (cas vécu avec RP2022_mobpro.parquet).

## Points A_VERIFIER

- Décret n° 2023-385 : prolongé ou modifié après mai 2026 ? (Légifrance)