"""Dictionnaire des colonnes réellement livrées, régénéré depuis les tables.

Les définitions et formules ci-dessous décrivent le code de préparation et les
notices archivées. Une colonne inconnue est signalée, jamais interprétée par
supposition. Commande hors ligne: python -m src.dictionnaire
"""
from __future__ import annotations

import csv
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
DOC = ROOT / "docs"
INSEE_HIST = "INSEE RP2022, série historique, COG2025 (8582555)"
INSEE_LOG = "INSEE RP2022, logement, COG2025 (8581474)"
INSEE_MOB = "INSEE RP2022, caractéristiques de l'emploi, COG2025 (8581424)"
COG = "INSEE COG au 01/01/2025 (8377162)"
DENS = "INSEE grille communale de densité 2025 (8571524), RP carroyé2021"
SNCF = "SNCF Gares & Connexions, fréquentation-gares, instantané archivé"
SDES = "SDES DiDo, parc VP, édition2026-06, stock au 1er janvier"
ADEME = "ADEME Impact CO₂ API, extraction26/10/2026, includeConstruction=1, occupencyRate=1"
DGAC = "DGAC ASP, archives LSN/PAP et notices archivées"
OMPHALE = "INSEE Omphale2022, base2018, tableaux détaillés publiés2024 (7747107)"

GRAINS = {
    "dataset_final_communes": "Une commune entière du RP2022 en COG2025; France hors Mayotte; rail/population principal en métropole.",
    "demographie_communes": "Une commune entière du RP2022 en COG2025; France hors Mayotte; arrondissements exclus.",
    "demographie_population_long": "Une commune entière COG2025 × année de recensement disponible (9 dates de1968à2022).",
    "demographie_passage_cog2025": "Un code non-COM du COG2025 disposant d'un parent; identités COM prioritaires et exclues du passage.",
    "demographie_densite2025": "Un code communal dans le classeur officiel de densité2025.",
    "demographie_ecarts_inter_sources": "Une commune × année dont la population diffère de plus de0,5entre deux bases RP2022.",
    "demographie_codes_exclus": "Un code de la source historique exclu de l'univers des communes entières (arrondissements).",
    "gares_annees": "Un code UIC SNCF × année2015–2024; comptages de gare, sans flux origine-destination.",
    "gares_referentiel": "Un code UIC publié dans la fréquentation SNCF; rattachement territorial et coordonnées contrôlés.",
    "communes_annees_rail": "Une commune COG2025 × année; gares UIC rattachées et présentes dans la source.",
    "climat_parc_communes": "Un code de forme communale SDES, avant regroupement COG; arrondissements distincts.",
    "climat_parc_codes_fictifs": "Un code SDES fictif ou invalide, exclu des jointures communales et conservé pour réconciliation.",
    "climat_parc_communes_cog2025": "Une commune de l'univers RP2022 avec stock SDES; arrondissements agrégés au parent, Mayotte hors univers.",
    "climat_facteurs_ademe": "Un mode de transport ADEME; facteurs moyens de référence à1km, construction incluse, voiture1occupant.",
    "climat_projections_departements": "Un département × scénario INSEE central/bas/haut; projections2018–2070, pas observations.",
    "aviation_aeroports_referentiel": "Un identifiant OurAirports, renommé icao pour la jointure; référentiel mondial, pas seulement France.",
    "aviation_emissions_annuelles": "Un faisceau DGAC × année × unité: émission nette totale ou intensité; unités à ne jamais additionner.",
    "aviation_trafic_mensuel": "Un mois × segment × faisceau × paire de zones LSN; faisceaux MET_RAD/MET_TRA,2015–2024.",
    "aviation_trafic_annuel": "Une année2015–2024 × faisceau LSN; MET_INTERIEUR est la somme des deux autres faisceaux.",
    "aviation_pap_mensuel_observe": "Un mois × paire d'aéroports PAP publiée; deux sens réunis, couverture soumise au seuil et secret.",
    "aviation_pap_annuel_observe": "Une année × paire PAP publiée; somme des seuls mois disponibles, pas trafic exhaustif.",
    "contexte_lgv": "Une ligne LGV lue sur une page Wikipédia; contexte documentaire uniquement, pas traitement causal.",
}


def readable(text: str) -> str:
    """Espaces de prose; ne touche jamais aux noms du champ_source."""
    text = re.sub(r"\b(année|années|base|cohorte|depuis|de|à|en|pour|RP|COG|Omphale|voiture|constante|notice|publication)([0-9]{4})", r"\1 \2", text)
    text = re.sub(r"([0-9]{4})([a-zàéè])", r"\1 \2", text)
    for old, new in {
        "15ansouplus": "15 ans ou plus", "2voituresouplus": "2 voitures ou plus", "2ouplus": "2 ou plus",
        "1km": "1 km", "1occupant": "1 occupant", "1000m": "1 000 m", "100m": "100 m", "1erjanvier": "1er janvier ",
        "31décembre": "31 décembre ", "10m": "10 m", "12attendus": "12 attendus", "12mois": "12 mois",
        "40cellules": "40 cellules", "2sexes": "2 sexes", "20âges": "20 âges", "2Aet2B": "2A et 2B",
        "1Peq": "1 Peq", "1passagerou0,1tonne": "1 passager ou 0,1 tonne", "10000Peq": "10 000 Peq",
        "3opérateurs": "3 opérateurs", "aucun>85%": "aucun > 85 %", "12attendus": "12 attendus",
        "année/paire": "année / paire", "CO₂net": "CO₂ net", "nonCO₂": "non CO₂", "cycledevie": "cycle de vie",
        "seulsmois": "seuls mois", "aprèslecaractère": "après le caractère ", "avantlecaractère": "avant le caractère ",
        "àFR": "à FR", "parLF": "par LF", "MoisPAP": "Mois PAP", "leZIP": "le ZIP", "duCSV": "du CSV",
        "2voitures": "2 voitures", "touscarburants": "tous carburants", "aucuneunité": "aucune unité",
    }.items():
        text = text.replace(old, new)
    return text


def record(label, definition, unit, source, field="", limits="", status="documenté"):
    return {"libelle": readable(label), "definition_ou_formule": readable(definition), "unite": readable(unit),
            "source": readable(source), "champ_source": field, "limites_et_champ": readable(limits),
            "statut_documentation": status}


@lru_cache(maxsize=None)
def _meta_label(field: str) -> str:
    """Libellé officiel, sans remplacer les formules du projet par un texte inventé."""
    for path in sorted((ROOT / "data/raw/insee").glob("meta_*.CSV")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream, delimiter=";"):
                if row.get("COD_VAR") == field:
                    return row.get("LIB_VAR_LONG") or row.get("LIB_VAR") or field
    return field


def describe(column: str, table: str) -> dict:
    """Définition explicite; règles de nommage limitées aux colonnes construites."""
    c = column
    if c == "CODGEO" and table == "demographie_codes_exclus":
        return record("Code géographique exclu de l'univers communal", "Code de la série historique absent de l'ensemble des communes entières TYPECOM=COM du COG2025; ici45arrondissements municipaux.", "code, chaîne", INSEE_HIST+"; "+COG, "CODGEO; TYPECOM", "Exclusion pour éviter d'additionner une ville entière et ses arrondissements; le code n'est pas nécessairement invalide.")
    if c in {"code_commune", "CODGEO"}:
        if table.startswith("climat_parc") and table != "climat_parc_communes_cog2025":
            return record("Code de localisation SDES", "Code SDES conservé en chaîne; peut être un arrondissement, ou un code fictif dans l'annexe dédiée.", "code, chaîne", SDES, "COMMUNE_CODE", "La forme de cinq caractères ne prouve pas qu'il s'agit d'une commune COG2025.")
        return record("Code de commune", "Code INSEE de la commune entière; zéros initiaux et lettres corses conservés.", "code, chaîne", COG, "COM / CODGEO", "Les tables principales utilisent la géographie2025; aucune jointure sur le seul nom.")
    identifiers = {
        "nom_commune": ("Nom officiel de commune", "LIBELLE"), "code_departement": ("Code de département", "DEP"),
        "code_region": ("Code de région", "REG"), "nom_region": ("Nom officiel de région", "v_region_2025.LIBELLE"),
        "code_commune_cog2025": ("Code du parent communal2025", "COMPARENT"),
        "type_commune_source": ("Type de code géographique source", "TYPECOM: ARM, COMA ou COMD"),
        "nom_commune_source": ("Nom officiel du code source", "LIBELLE"),
    }
    if c in identifiers:
        label, field = identifiers[c]
        src = OMPHALE + "; codes synthèse2022 (6652134)" if table == "climat_projections_departements" else COG
        return record(label, label + "; variable d'identification, pas une mesure quantitative.", "libellé" if c.startswith("nom_") else "code, chaîne", src, field)
    if c == "code_commune_source":
        return record("Code communal avant passage", "Code de la source avant harmonisation; dans la table de passage, code officiel non-COM disposant d'un parent.", "code, chaîne", COG if table.startswith("demographie") else "SNCF gares-de-voyageurs", "COM" if table.startswith("demographie") else "codeinsee")
    if c == "millesime_cog":
        return record("Millésime géographique", "Géographie constante fixée au1erjanvier2025 pour les observations communales INSEE.", "année de géographie", COG, "Constante2025")
    if c == "metropole":
        return record("Champ métropolitain", "Vrai si le code de département ne commence pas par97; Corse comprise.", "booléen", COG, "not code_departement.startswith('97')", "Ce drapeau ne garantit pas la validité de Lambert93 pour la Corse ou les DROM.")
    m = re.fullmatch(r"population_(\d{4})", c)
    if m or (c == "population" and table == "demographie_population_long"):
        year = m.group(1) if m else "année"
        sourcefield = ({"1968":"D68_POP", "1975":"D75_POP", "1982":"D82_POP", "1990":"D90_POP", "1999":"D99_POP", "2006":"P06_POP", "2011":"P11_POP", "2016":"P16_POP", "2022":"P22_POP"}).get(year,"Champ source correspondant à annee")
        return record(f"Population de{year}", _meta_label(sourcefield), "habitants", INSEE_HIST, sourcefield, "Population observée reconstituée dans la géographie2025; arrondissements exclus des tables principales.")
    if c == "superficie_km2":
        return record("Superficie communale", "Superficie fournie par la base historique INSEE.", "km²", INSEE_HIST, "SUPERF")
    m = re.fullmatch(r"(naissances|deces)_(\d{4})_(\d{4})", c)
    if m:
        kind,start,end=m.groups(); field=("NAIS" if kind=="naissances" else "DECE")+start[-2:]+end[-2:]
        return record(f"{kind.capitalize()} de{start}à{end}", f"{kind.capitalize()} du1erjanvier{start}au31décembre{end}, événement domicilié selon la source historique.", "personnes, événements", INSEE_HIST, field)
    m=re.fullmatch(r"(menages|menages_au_moins_une_voiture|menages_une_voiture|menages_deux_voitures_ou_plus|residences_principales_historique)_(\d{4})",c)
    if m:
        name,year=m.groups(); names={"menages":("Ménages","MEN"),"menages_au_moins_une_voiture":("Ménages disposant d'au moins une voiture","RP_VOIT1P"),"menages_une_voiture":("Ménages disposant exactement d'une voiture","RP_VOIT1"),"menages_deux_voitures_ou_plus":("Ménages disposant de deux voitures ou plus","RP_VOIT2P"),"residences_principales_historique":("Résidences principales, base historique","RP")}
        label,suffix=names[name];field=f"P{year[-2:]}_{suffix}"
        return record(f"{label},{year}",_meta_label(field),"ménages" if name!="residences_principales_historique" else "résidences principales",INSEE_LOG if name!="residences_principales_historique" else INSEE_HIST,field,"Effectifs de recensement pouvant être pondérés et non entiers; catégorie2voituresouplus non ventilée au-delà de2.")
    m=re.fullmatch(r"(actifs_occupes_15p|actifs_sans_deplacement|navetteurs_voiture|navetteurs_transports_commun|navetteurs_marche|navetteurs_velo|navetteurs_deux_roues_motorises|navetteurs_deux_roues)_(\d{4})",c)
    if m:
        name,year=m.groups();suffixes={"actifs_occupes_15p":"","actifs_sans_deplacement":"_PASTRANS","navetteurs_voiture":"_VOITURE","navetteurs_transports_commun":"_COMMUN","navetteurs_marche":"_MARCHE","navetteurs_velo":"_VELO","navetteurs_deux_roues_motorises":"_2ROUESMOT","navetteurs_deux_roues":"_2ROUES"}
        field=f"P{year[-2:]}_ACTOCC15P{suffixes[name]}"
        return record(_meta_label(field),_meta_label(field),"actifs occupés de15ansouplus",INSEE_MOB,field,"Mode principal domicile-travail; tous les actifs occupés au dénominateur des parts. Transports collectifs ≠ train; deux-roues2016 et2022 de périmètre différent.")
    m=re.fullmatch(r"tcam_(population|rail)_(\d{4})_(\d{4})_pct",c)
    if m:
        kind,start,end=m.groups();base="population" if kind=="population" else "voyageurs_cohorte"
        return record(f"Croissance annuelle moyenne {kind},{start}–{end}",f"100×[({base}_{end}/{base}_{start})^(1/({end}−{start}))−1], base strictement positive.","% par an",INSEE_HIST if kind=="population" else SNCF,"Calcul du projet", "Rail: mêmes UIC aux deux dates, valeur2016>0 et2022nonmanquante; comptages, pas offre de trains ni voyages uniques.")
    m=re.fullmatch(r"croissance_(population|rail)_(\d{4})_(\d{4})_pct",c)
    if m:
        kind,start,end=m.groups();base="population" if kind=="population" else "voyageurs_cohorte"
        return record(f"Croissance totale {kind},{start}–{end}",f"100×({base}_{end}/{base}_{start}−1), base strictement positive.","% sur la période",INSEE_HIST if kind=="population" else SNCF,"Calcul du projet","Ne pas confondre avec le TCAM; rail limité à la cohorte comparable.")
    m=re.fullmatch(r"alerte_(population|menages)_inter_sources_(\d{4})",c)
    if m:
        kind,year=m.groups()
        formula=f"abs(population_{year}−P{year[-2:]}_POP de la base évolution-structure)>0,5" if kind=="population" else f"abs(P{year[-2:]}_RP historique−menages_{year} logement)>0,5"
        return record(f"Alerte de cohérence {kind},{year}",formula,"booléen",INSEE_HIST+"; "+("INSEE évolution-structure2022 (8581696)" if kind=="population" else INSEE_LOG),"Contrôle intersources","Les valeurs source restent conservées. Les ratios concernés sont neutralisés; aucun ajustement arbitraire.")
    if c in {"jointure_logement","jointure_mobilite"}:
        return record("Statut de jointure "+c.split('_')[1],"Indicateur pandas de jointure gauche par code communal: both ou left_only.","catégorie",INSEE_LOG if c.endswith("logement") else INSEE_MOB,"merge(...,indicator=...)","both confirme une clé présente, pas l'absence de divergence méthodologique.")
    m=re.fullmatch(r"part_menages_motorises_(\d{4})_pct",c)
    if m:
        y=m.group(1);return record(f"Part de ménages motorisés,{y}",f"100×menages_au_moins_une_voiture_{y}/menages_{y}; dénominateur>0 et absence d'alertes population/ménages de{y}.","% des ménages",INSEE_LOG,"Calcul du projet","Taux de ménages équipés, pas nombre de voitures par ménage.")
    m=re.fullmatch(r"voitures_par_menage_borne_inferieure_(\d{4})",c)
    if m:
        y=m.group(1);return record(f"Borne inférieure de voitures par ménage,{y}",f"(menages_une_voiture_{y}+2×menages_deux_voitures_ou_plus_{y})/menages_{y}; dénominateur>0, sans alertes.","voitures par ménage, borne inférieure",INSEE_LOG,"Calcul du projet","La catégorie2ouplus interdit de connaître le nombre exact; ce ratio ne doit pas être présenté comme une moyenne exacte.")
    m=re.fullmatch(r"part_modale_(voiture|transports_commun)_(\d{4})_pct",c)
    if m:
        mode,y=m.groups();return record(f"Part modale {mode.replace('_',' ')},{y}",f"100×navetteurs_{mode}_{y}/actifs_occupes_15p_{y}; dénominateur>0 et absence d'alertes population/ménages.","% des actifs occupés de15ansouplus",INSEE_MOB,"Calcul du projet","Actifs sans déplacement inclus dans le dénominateur; transports collectifs ≠ train; ratio descriptif.")
    m=re.fullmatch(r"mobilite_geographie_comparable_(\d{4})",c)
    if m:
        y=m.group(1);return record(f"Comparabilité géographique mobilité,{y}",f"jointure_mobilite='both' ET non alerte_population_inter_sources_{y} ET non alerte_menages_inter_sources_{y}.","booléen",INSEE_MOB+"; contrôles INSEE","Calcul du projet","Indicateur prudent de cohérence de clés et sources; ne prouve pas toutes les dimensions de comparabilité.")
    density={"classe_densite_3":"DENS","libelle_densite_3":"LIBDENS","classe_densite_7":"DENS7","libelle_densite_7":"LIBDENS7","classe_densite_aav":"DENS_AAV","libelle_densite_aav":"LIBDENS_AAV"}
    if c in density:
        return record("Typologie officielle de densité: "+c.replace('_',' '),"Classe ou libellé du classeur officiel2025; classification fondée sur le RP carroyé2021, avec variantes3niveaux,7niveaux ou AAV.","libellé" if c.startswith("libelle") else "code de catégorie",DENS,density[c],"Distincte de population2022/superficie; ne pas attribuer arbitrairement des seuils aux codes de catégorie.")
    exact={
      "densite_population_2022_hab_km2":("Densité moyenne communale2022","population_2022/superficie_km2, superficie>0.","habitants/km²",INSEE_HIST,"P22_POP / SUPERF","N'est pas la grille officielle de densité fondée sur la répartition infracommunale."),
      "variation_population_2016_2022":("Variation de population2016–2022","population_2022−population_2016.","habitants",INSEE_HIST,"Calcul du projet","Variation nette, pas solde migratoire seul."),
      "solde_naturel_2016_2022":("Solde naturel2016–2022","naissances_2016_2021−deces_2016_2021, entre01/01/2016et31/12/2021.","personnes",INSEE_HIST,"NAIS1621−DECE1621","Correspond à l'intervalle entre populations au1erjanvier2016et2022."),
      "solde_migratoire_apparent_2016_2022":("Solde migratoire apparent2016–2022","variation_population_2016_2022−solde_naturel_2016_2022.","personnes",INSEE_HIST,"Calcul résiduel","Solde apparent, incluant ajustements et erreurs de mesure; pas comptage direct des déménagements."),
      "variation_part_modale_voiture_2016_2022_points":("Variation de la part voiture2016–2022","part_modale_voiture_2022_pct−part_modale_voiture_2016_pct.","points de pourcentage",INSEE_MOB,"Calcul du projet","Ne pas lire comme une variation relative en%; association avec rail non causale."),
      "trajectoire_demographique":("Trajectoire démographique descriptive","Déclin si TCAM population2016–2022<−0,2%; croissance si>+0,2%; stable sinon si taux connu; indetermine sinon.","catégorie",INSEE_HIST,"Classe construite","Seuil descriptif choisi, sans test de significativité."),
      "alerte_comparabilite_rail_population":("Alerte de comparabilité rail/population","alerte_population_inter_sources_2016 OU alerte_population_inter_sources_2022.","booléen","Contrôles INSEE2022","Calcul du projet","Communes exclues de l'analyse principale rail/population; conservées dans l'analyse de sensibilité."),
      "ecart_tcam_rail_population_points":("Écart de croissance rail/population","tcam_rail_2016_2022_pct−tcam_population_2016_2022_pct.","points de pourcentage par an",SNCF+"; "+INSEE_HIST,"Calcul du projet","Écart descriptif; la fréquentation ne mesure pas l'offre ferroviaire."),
      "comptages_gares_par_habitant_2022":("Comptages de gare par habitant2022","voyageurs_cohorte_2022/population_2022, population>0.","comptages par habitant",SNCF+"; "+INSEE_HIST,"Calcul du projet","Pas un nombre de voyages effectués par les seuls résidents; bassins de gares dépassent la commune."),
      "profil_rail_demographie":("Profil croisé rail/démographie","Quatre catégories selon le signe≥0ou<0des TCAM population et rail2016–2022; manquant si un taux manque.","catégorie",SNCF+"; "+INSEE_HIST,"Calcul du projet","Ne mesure ni qualité de desserte ni causalité."),
      "distance_centre_gare_km":("Distance du centre géométrique à une gare","Distance euclidienne minimale en Lambert93, divisée par1000, entre centroïde communal et gare avec comptage positif2024et coordonnées.","km à vol d'oiseau","Contours COG2025 généralisés100m; SNCF2024","cKDTree sur coordonnées EPSG:2154","France continentale uniquement; ni distance routière, ni temps d'accès, ni localisation de tous les habitants."),
      "gare_proche_uic":("Gare retenue comme la plus proche","Code UIC de la gare minimisant distance_centre_gare_km.","code UIC, chaîne",SNCF+"; calcul spatial","argmin de la distance","Gare de l'univers observé SNCF avec comptage positif2024; réseau non exhaustif."),
      "longitude_centre":("Longitude du centroïde","Centroïde du polygone calculé en Lambert93, puis reconverti enWGS84.","degrés de longitude","Contours COG2025 généralisés100m","geometry.centroid puis to_crs(4326)","Centre géométrique, pas chef-lieu ni centre pondéré par la population."),
      "latitude_centre":("Latitude du centroïde","Centroïde du polygone calculé en Lambert93, puis reconverti enWGS84.","degrés de latitude","Contours COG2025 généralisés100m","geometry.centroid puis to_crs(4326)","Centre géométrique, pas localisation des habitants."),
      "champ_distance_france_continentale":("Champ du proxy d'accessibilité","Commune métropolitaine hors départements2Aet2B.","booléen",COG,"metropole et département hors{2A,2B}","DROM et Corse hors calcul; aucune distance zéro imputée."),
      "nb_gares_cohorte_2016_2022":("Nombre de gares de la cohorte commune","Nombre d'UIC de la commune avec voyageurs2016>0et voyageurs2022nonmanquant.","gares UIC",SNCF,"nunique(code_uic)","Même cohorte pour les deux années; ce n'est pas l'inventaire exhaustif de l'offre."),
      "voyageurs":("Comptages annuels voyageurs en gare","Valeur SNCF Total Voyageurs de l'année, mise au format long.","comptages annuels",SNCF,"total_voyageurs_YYYY ou totalvoyageurs2017","Comptages en gare, pas voyages uniques; source estimée/révisable; les zéros publiés sont conservés."),
      "code_uic":("Code UIC de gare","Identifiant SNCF à8chiffres conservé en chaîne.","code, chaîne",SNCF,"code_uic_complet; codes_uic du référentiel","Une gare peut avoir plusieurs UIC; le grain analytique reste l'UIC publié."),
      "nom_gare":("Nom de gare","Libellé SNCF, conservé sans rapprochement approximatif pour les jointures.","libellé",SNCF,"nom_gare","Le nom ne constitue pas une clé fiable."),
      "source_coordonnees":("Source des coordonnées de gare","Gares&Connexions en priorité; SNCF Réseau en repli si dispersion des projections≤1000m.","catégorie","SNCF gares-de-voyageurs; liste-des-gares","Règle du projet","Coordonnées manquantes conservées si le repli est ambigu."),
      "nb_projections_reseau":("Nombre de projections SNCF Réseau","Nombre de lignes du référentiel réseau pour le même UIC.","projections par UIC","SNCF Réseau liste-des-gares","groupby(code_uic).size","Ce n'est ni le nombre de trains ni le nombre de quais."),
      "dispersion_projections_reseau_m":("Dispersion des projections réseau","sqrt[(max(x_l93)−min(x_l93))²+(max(y_l93)−min(y_l93))²] par UIC.","mètres","SNCF Réseau liste-des-gares","x_l93,y_l93","Diagonale de boîte englobante; repli coordonnées refusé au-delà de1000m."),
      "methode_jointure_commune":("Méthode de rattachement gare/commune","Code INSEE/parent COG2025 en priorité; sinon point unique à l'intérieur d'un polygone simplifié100m.","catégorie","SNCF; COG2025; contours administratifs","Jointure contrôlée du projet","Aucune affectation automatique au polygone le plus proche; limites simplifiées peuvent laisser des cas non résolus."),
      "vp_2022_pour_1000_habitants":("Stock VP pour1000habitants2022","1000×vp_2022/population_2022, population>0.","VP pour1000habitants",SDES+"; "+INSEE_HIST,"Calcul du projet","Stock d'adresses d'immatriculation, tous utilisateurs; pas taux de ménages motorisés ni émissions."),
      "vp_particuliers_2022_par_menage":("VP de particuliers par ménage2022","vp_particuliers_2022/menages_2022, ménages>0.","VP de particuliers par ménage",SDES+"; "+INSEE_LOG,"Calcul du projet","Périmètres certificat d'immatriculation/recensement distincts; pas taux de ménages motorisés."),
      "population_historique":("Population de la base historique","Valeur RP de la base série historique à la date indiquée par annee.","habitants",INSEE_HIST,"Champ POP de l'année","Valeur conservée, non corrigée arbitrairement."),
      "population_autre_base":("Population de la base évolution-structure","Valeur RP2022 de la base évolution-structure à la date indiquée par annee.","habitants","INSEE RP2022 évolution-structure (8581696)","P11_POP,P16_POPouP22_POP","Une différence peut refléter scission ou reprise géographique; table d'alerte, pas correctif."),
    }
    if c in exact:
        return record(*exact[c])
    m=re.fullmatch(r"centre_a_plus_de_(\d+)km",c)
    if m:
        threshold=m.group(1);return record(f"Centroïde à plus de{threshold}km d'une gare",f"distance_centre_gare_km>{threshold}; manquant si distance manquante.","booléen","Calcul spatial du projet","distance_centre_gare_km","Proxy communal appliqué à la population de la commune; pas part d'habitants géolocalisés au-delà du seuil.")
    m=re.fullmatch(r"voyageurs_cohorte_(\d{4})",c)
    if m:
        y=m.group(1);return record(f"Comptages de la cohorte de gares,{y}",f"Somme de voyageurs{y}des UIC de la commune avec voyageurs2016>0et voyageurs2022nonmanquant.","comptages annuels en gare",SNCF,"total_voyageurs_"+y,"Cohorte fixe2016–2022; absence de cohorte reste manquante, pas imputée à zéro.")
    m=re.fullmatch(r"(voyageurs_gares|nb_gares_observees|nb_gares_valeurs_valides)(?:_(\d{4}))?",c)
    if m:
        what,y=m.groups();details={"voyageurs_gares":("Comptages de toutes les gares rattachées","Somme des voyageurs nonmanquants par commune×année, avec min_count=1.","comptages annuels"),"nb_gares_observees":("Nombre d'UIC publiés rattachés","Nombre d'UIC distincts par commune×année.","gares UIC"),"nb_gares_valeurs_valides":("Nombre d'UIC avec comptage renseigné","Nombre de valeurs voyageurs nonmanquantes par commune×année; les zéros comptent comme renseignés.","gares UIC")};label,definition,unit=details[what]
        return record(label+(f",{y}"if y else""),definition+(" Dans la table finale, absence de gares observées2024→nb_gares_observees_2024=0."if c=="nb_gares_observees_2024"else""),unit,SNCF,"Agrégation par code_commune,annee","Périmètre de la source SNCF, non inventaire exhaustif de desserte.")
    if c in {"longitude","latitude"}:
        return record("Coordonnée de gare: "+c,"Coordonnée WGS84 de Gares&Connexions, ou médiane des projections SNCF Réseau si repli admissible.","degrés WGS84","SNCF gares-de-voyageurs; liste-des-gares","position_geographique.lon/lat; x_wgs84/y_wgs84","Source et dispersion du repli renseignées séparément.")
    sncf_fields={"code_postal":"Code postal","direction_regionale_gares":"Direction régionale gares","segmentation_drg":"Segmentation DRG","segmentation_marketing":"Segmentation marketing","non_voyageurs":"Pourcentage de non-voyageurs"}
    if c in sncf_fields:
        return record(sncf_fields[c],"Attribut SNCF repris sans modification; pas une mesure annuelle reconstruite.","% selon libellé source"if c=="non_voyageurs"else"code/libellé",SNCF,c,"Attribut descriptif répété sur les années dans gares_annees; définition détaillée non fournie dans les métadonnées; non utilisé pour reconstruire les comptages.")
    m=re.fullmatch(r"vp(?:_(particuliers|electriques))?_(\d{4})",c)
    if m:
        subset,y=m.groups();condition={None:"tous carburants, Crit'Air et statuts utilisateur","particuliers":"STATUT_UTILISATEUR='Particulier'","electriques":"CARBURANT='Electrique', hors hybrides"}[subset]
        return record(f"Stock VP{(' '+subset)if subset else''},{y}",f"Somme PARC_{y}pour GROUPE='VP', {condition}, par code; codes regroupés au parent dans la table harmonisée.","véhicules au1erjanvier",SDES,f"PARC_{y}; GROUPE; STATUT_UTILISATEUR; CARBURANT","2024révisable,2023etavant annoncés définitifs; géographie source exacte non précisée; une ventilation absente reste manquante.")
    if c=="vp_croissance_2016_2022_pct":
        return record("Croissance du stock VP2016–2022","100×(vp_2022/vp_2016−1), base2016>0; recalcul après agrégation COG.","% sur la période",SDES,"Calcul du projet","Stock de véhicules, pas trafic automobile ni émissions.")
    climate_exact={
      "code_fictif_ou_invalide":("Localisation impropre à une jointure communale","Vrai si code finit par000, est un97x00deDROM, ou n'a pas la forme d'un code communal.","booléen",SDES,"COMMUNE_CODE","Ces codes sont séparés, pas répartis arbitrairement entre communes."),
      "millesime_source_sdes":("Édition SDES","Constante2026-06; millésime de diffusion, distinct de la date du stock et du COG.","millésime de diffusion",SDES,"millesime","Ne prouve pas la géographieCOG2026."),
      "cog_cible":("Géographie visée par le regroupement","Constante2025; parents et codes vérifiés au COG officiel.","année de géographie",COG,"Constante2025","Ne rétablit pas une ventilation infracommunale indisponible dans la source SDES."),
      "cog_exact_source_sdes_non_precise":("Réserve sur la géographie SDES","Vrai: la notice mentionne la dernière géographie disponible sans numéro explicite.","booléen",SDES,"Information méthodologique","Présence de ce drapeau même si tous les codes sont résolus."),
      "parc_millesime_geographique_non_precise":("Réserve géographique du parc intégré","Vrai: le millésime géographique exact de la diffusion SDES n'est pas explicité.","booléen",SDES,"Information méthodologique","Même réserve que cog_exact_source_sdes_non_precise dans la table SDES."),
      "id_mode_ademe":("Identifiant de mode ADEME","Identifiant retourné par l'API pour le mode demandé.","code entier",ADEME,"id","Ne pas agréger des modes par addition des identifiants."),
      "mode":("Mode de transport ADEME","Libellé de mode fourni par l'API.","libellé",ADEME,"name","Modes de référence, pas offre locale."),
      "kgco2e_par_voyageur_km":("Facteur d'émission ADEME","Valeur API pourkm=1, construction incluse, voiture1occupant.","kgCO₂e/voyageur.km",ADEME,"value","Facteur moyen de référence collecté2026; pas série historique ni émission communale mesurée."),
      "gco2e_par_voyageur_km":("Facteur d'émission ADEME en grammes","1000×kgco2e_par_voyageur_km.","gCO₂e/voyageur.km",ADEME,"Calcul de conversion","Construction incluse; pas confusion avec CO₂net DGAC."),
      "perimetre":("Convention du facteur ADEME","Rappel textuel des paramètres de la requête: includeConstruction=1,voiture1occupant.","texte",ADEME,"Paramètres archivés","Ne pas supposer l'inclusion exhaustive des infrastructures."),
      "date_collecte":("Date de collecte du facteur","HorodatageUTC de la récupération enregistré dans le manifeste.","date-heure ISO8601 UTC",ADEME,"manifest.retrieved_at_utc","Date de récupération, pas nécessairement année d'estimation du facteur."),
      "nom_departement":("Nom de département projeté","Nom de département du classeur Omphale détaillé, apparié au code du classeur de synthèse2022.","libellé",OMPHALE,"ZONE / LIBDEP","Pas une unité communale."),
      "scenario_insee":("Scénario Omphale","central,population_basseoupopulation_haute, selon le fichier officiel téléchargé.","catégorie",OMPHALE,"Nom du scénario INSEE","Trois scénarios, sans probabilités ni intervalle de confiance."),
      "croissance_projetee_2018_2050_pct":("Croissance démographique projetée2018–2050","100×(population_projetee_2050/population_projetee_2018−1).","% projeté",OMPHALE,"Calcul du projet","Conditionnelle au scénario; pas observation ni prévision de fréquentation ferroviaire."),
      "statut_donnee":("Statut de projection","Rappel: projection officielle Omphale2022,base2018,publication2024; pas prévision.","texte",OMPHALE,"Information méthodologique","Ne pas concaténer aux populations observées sans distinguer les statuts."),
      "precision_source":("Précision des projections","Cellules sexe-âge arrondies à10; documentation recommande l'ordre de grandeur du millier.","texte",OMPHALE,"Documentation du classeur","Les sommes des cellules arrondies ne sont pas des effectifs exacts."),
    }
    if c in climate_exact:return record(*climate_exact[c])
    if c in {"nb_codes_source_agreges","nb_arrondissements_source","nb_communes_deleguees_source","nb_communes_associees_source"}:
        typ={"nb_codes_source_agreges":"tous codes source","nb_arrondissements_source":"TYPECOM=ARM","nb_communes_deleguees_source":"TYPECOM=COMD","nb_communes_associees_source":"TYPECOM=COMA"}[c]
        return record("Nombre de codes SDES regroupés: "+typ,"Nombre de codes source distincts conservés et rattachés à la commune cible, "+typ+".","codes source",SDES+"; "+COG,"Comptage après passage officiel","Le résidu du code parent et les arrondissements sont additionnés; ces codes ne sont pas des véhicules.")
    m=re.fullmatch(r"population_projetee_(\d{4})",c)
    if m:
        y=m.group(1);return record(f"Population projetée pour{y}",f"Somme POP_{y}des40cellules disjointes2sexes×20âges par département et scénario.","personnes projetées",OMPHALE,"Population.POP_"+y,"Cellules arrondies à10, interprétation au millier; scénario officiel, aucune observation simulée dans le projet.")
    if c=="annee":
        return record("Année de référence","Année de la mesure; pour les stocks:1erjanvier; pour les comptages:année civile; pour les émissions:année DGAC.","année civile",DGAC if table.startswith("aviation") else INSEE_HIST if table.startswith("demographie") else SNCF,"ANMOIS[:4]"if table.startswith("aviation")else"Année du champ source")
    if table.startswith("aviation"):
        return describe_aviation(c,table)
    if table=="contexte_lgv":
        definitions={"ligne":("Nom de ligne LGV","Nom documentaire de la ligne sur la page source.","libellé"),"champ_html":("Champ HTML lu","Libellé du champ d'infobox utilisé pour l'extraction.","texte"),"mise_en_service_brute":("Mise en service brute","Texte complet extrait de l'infobox; peut mentionner plusieurs phases.","texte"),"date_exacte_iso_si_disponible":("Date exacte si identifiable","DateISO extraite uniquement si le texte fournit une date complète non ambiguë; sinon vide.","date ISO8601"),"annee_min":("Première année citée","Minimum des années extraites du champ de mise en service.","année"),"annee_max":("Dernière année citée","Maximum des années extraites du champ de mise en service.","année"),"url_source":("URL documentaire","Adresse de la page Wikipédia archivée.","URL"),"fichier_html":("Archive de page","Chemin local de la copie HTML brute.","chemin relatif"),"sha256_html":("Empreinte de page","SHA-256 de l'archiveHTML.","empreinte hexadécimale"),"robots_autorise":("Contrôle robots","Indicateur d'accès autorisé par robots.txt lors du scraping.","booléen"),"role":("Rôle dans le projet","Contexte documentaire uniquement; pas instrument causal ni variable de traitement.","texte")}
        if c in definitions:
            label,definition,unit=definitions[c];return record(label,definition,unit,"Wikipédia, pages et robots.txt archivés","Champ HTML; src/contexte_lgv.py","Source secondaire de contexte, non mesure de fréquentation.")
    return record("Variable à documenter: "+c,"Aucune définition sûre enregistrée; consulter le champ source et le code de préparation avant tout usage analytique.","non établie","À vérifier",c,"Aucune formule ni unité n'est déduite automatiquement du seul nom.","à vérifier")


def describe_aviation(c: str, table: str) -> dict:
    airport=re.fullmatch(r"(icao|name|iso_country|latitude_deg|longitude_deg|iata_code|type)(?:_([12]))?",c)
    if airport:
        var,side=airport.groups();spec={"icao":("Identifiant de l'aéroport","Identifiant OurAirports ident renomméicao; coïncide avec le code OACI pour les aéroports DGAC appariés.","code, chaîne","ident"),"name":("Nom d'aéroport","Libellé OurAirports.","texte","name"),"iso_country":("Pays d'aéroport","Code paysISO du référentiel OurAirports.","codeISO","iso_country"),"latitude_deg":("Latitude d'aéroport","LatitudeWGS84 du référentiel.","degrés de latitude","latitude_deg"),"longitude_deg":("Longitude d'aéroport","LongitudeWGS84 du référentiel.","degrés de longitude","longitude_deg"),"iata_code":("CodeIATA","CodeIATA s'il est renseigné dans OurAirports.","code, chaîne","iata_code"),"type":("Type d'aéroport","Classification OurAirports, conservée brute.","catégorie","type")}
        label,definition,unit,field=spec[var];return record(label+(" extrémité"+side if side else""),definition,unit,"OurAirports, instantané archivé",field,"Référentiel mondial évolutif; ident n'est pas universellement un code OACI; jointure sur code, jamais sur nom.")
    definitions={
      "ANMOIS":("Période mensuelleDGAC","Mois au formatAAAAMM.","code de mois, chaîne","ANMOIS"),
      "mois":("Numéro du mois","Deux derniers caractèresANMOIS convertis en entier1à12.","mois","ANMOIS[4:6]"),
      "LSN_SEG":("SegmentDGAC","NAT=trafic intérieur,INTL=international; variable brute source.","code de catégorie","LSN_SEG"),
      "LSN_FSC":("FaisceauDGAC","MET_RAD=Paris–province;MET_TRA=province–province;MET_INTERIEUR=total des deux, construit seulement dans la table annuelle.","code de catégorie","LSN_FSC"),
      "LSN_1":("Premier point zonalLSN","Désignation du premier point agrégé de la liaison: métropole,outre-mer,Paris ou province selon faisceau.","zone/libellé","LSN_1"),
      "LSN_2":("Second point zonalLSN","Désignation du second point agrégé:province/outre-mer ou pays selon faisceau.","zone/libellé","LSN_2"),
      "LSN_2_CONT":("Continent de destination/origine","Continent source pour le trafic international exclusivement; généralement vide dans le sous-champ métropolitain intérieur.","code/libellé","LSN_2_CONT"),
      "LSN_PEQ":("Passagers équivalentsLSN","1Peq=1passagerou0,1tonne de fret/poste; variable brute conservée.","passagers équivalents","LSN_PEQ"),
      "LSN_PEQKT":("Passagers équivalents.kmLSN","Passagers équivalents-kilomètres transportés selon noticeLSN; variable brute conservée.","milliards dePeq.km","LSN_PEQKT"),
      "LSN_PAX":("Passagers locauxLSN","Passagers locaux de la liaison; variable numérique retenue pour les totaux.","passagers","LSN_PAX"),
      "LSN_PKT":("Passagers.kmLSN","Passagers-kilomètres transportés; variable brute conservée.","milliards de passagers.km","LSN_PKT"),
      "LSN_FRP":("Fret et poste locauxLSN","Fret et poste locaux sur la liaison; variable brute conservée.","tonnes","LSN_FRP"),
      "LSN_TKT":("Fret et poste.kmLSN","Fret et poste-kilomètres transportés; variable brute conservée.","tonnes.km selon libellé; échelle non explicitée dans notice","LSN_TKT"),
      "LSN_DRT":("Dessertes commercialesLSN","Nombre de dessertes commerciales avec ou sans escale intermédiaire.","dessertes","LSN_DRT"),
      "source_member":("Fichier membre de l'archive","Nom duCSV annuel dans leZIP source.","nom de fichier","MembreZIP"),
      "passagers":("Passagers aériens annuelsLSN","SommeLSN_PAX par année/faisceau;MET_INTERIEUR=MET_RAD+MET_TRA.","passagers par an","sum(LSN_PAX)"),
      "dessertes":("Dessertes aériennes annuellesLSN","SommeLSN_DRT par année/faisceau;MET_INTERIEUR=MET_RAD+MET_TRA.","dessertes par an","sum(LSN_DRT)"),
      "mois_observes":("Mois couvertsLSN","Nombre de mois distincts par année/faisceau;12attendus et contrôlés.","mois","nunique(mois)"),
      "passagers_2019":("Référence aérienne2019","PassagersLSN2019du même faisceau, répétés sur les années pour construire l'indice.","passagers en2019","passagers(2019)"),
      "indice_2019_100":("Indice aérien base100en2019","100×passagers/passagers_2019.","indice,2019=100","Calcul du projet"),
      "PAP":("Paire d'aéroportsDGAC","Paire de codesOACI de formeAAAA_BBBB; ordre de classementDGAC, deux sens réunis.","code de paire","PAP"),
      "PAP1_LABEL":("Nom premier aéroportDGAC","Appellation de l'aéroport des quatre premiers caractères dePAP.","libellé","PAP1_LABEL"),
      "PAP2_LABEL":("Nom second aéroportDGAC","Appellation de l'aéroport des quatre derniers caractères dePAP.","libellé","PAP2_LABEL"),
      "PAP_DIST":("Distance entre aéroports","Distance orthodromique selon la noticePAP.","distance: unité non explicitée dans la notice archivée","PAP_DIST"),
      "PAP_PEQ":("Passagers équivalents locauxPAP","1Peq=1passagerou0,1tonne de fret/poste; départs et arrivées réunis.","passagers équivalents","PAP_PEQ (ancien nom); PAP_PEQ_LOC dans notice"),
      "PAP_PAX":("Passagers locauxPAP","Passagers locaux sur la paire, départs et arrivées réunis.","passagers","PAP_PAX (ancien nom); PAP_PAX_LOC dans notice"),
      "PAP_FRP":("Fret/poste locauxPAP","Fret et poste locaux, départs et arrivées réunis; variable brute conservée.","tonnes","PAP_FRP (ancien nom); PAP_FRP_LOC dans notice"),
      "PAP_DRT":("Dessertes commercialesPAP","Dessertes avec ou sans escale intermédiaire, départs et arrivées réunis.","dessertes","PAP_DRT"),
      "PAP_MVT":("Mouvements commerciaux directsPAP","Mouvements sans escale intermédiaire, départs et arrivées réunis; variable brute conservée.","mouvements","PAP_MVT"),
      "PAP_PEQ_FS":("Passagers équivalents à bordPAP","Passagers équivalents à bord sur liaisons directes, départs et arrivées réunis; variable brute conservée.","passagers équivalents","PAP_PEQ_FS"),
      "PAP_PAX_FS":("Passagers à bord en directPAP","Passagers à bord sur liaisons directes, départs et arrivées réunis; variable brute conservée.","passagers","PAP_PAX_FS"),
      "PAP_FRP_FS":("Fret/poste à bord en directPAP","Fret/poste à bord sur liaisons directes, départs et arrivées réunis; variable brute conservée.","tonnes","PAP_FRP_FS"),
      "aeroport_1":("Premier code aéroportDGAC","Première composante dePAP avantlecaractère_.","codeOACI","PAP.split('_')[0]"),
      "aeroport_2":("Second code aéroportDGAC","Seconde composante dePAP aprèslecaractère_.","codeOACI","PAP.split('_')[1]"),
      "interieur_metropole":("Paire intérieure métropolitaine","Deux codesPAP commençant parLF et deux paysOurAirports égauxàFR.","booléen","aeroport_1, aeroport_2,iso_country_1,iso_country_2"),
      "passagers_observes":("PassagersPAP des seuls mois publiés","SommePAP_PAX par année/paire, sur les mois présents uniquement.","passagers observés","sum(PAP_PAX)"),
      "mois_publies":("Nombre de moisPAP publiés","Nombre de mois distincts présents dans l'archive pour l'année/paire.","mois","nunique(mois)"),
      "serie_annuelle_complete":("Douze moisPAP publiés","mois_publies==12.","booléen","Calcul du projet"),
      "faisceau":("Périmètre des émissionsDGAC","MET_INTERIEUR,MET-OM_et_OM-OM,INTL_MC,INTL_LC ouFRANCE_TOT selon la sourceEMI.","code de catégorie","AN dans fichiersEMI"),
      "valeur":("Mesure d'émission netteDGAC","Valeur sourceEMI_TOT ouEMI_UNI, conservée sans mélange des unités.","Variable: lire obligatoirementunite","Cellule duCSVEMI"),
      "unite":("Unité de mesure des émissionsDGAC","Mt_CO2_net=millions de tonnes deCO₂net;g_CO2_net_par_Peq_km=grammes deCO₂net par passager équivalent.km.","code d'unité","FichierEMI_TOT ouEMI_UNI"),
    }
    if c in definitions:
        label,definition,unit,field=definitions[c]
        if "PAP" in c or table.startswith("aviation_pap"):
            limits="PAP: seuil≥10000Peq/mois et secret statistique (≥3opérateurs, aucun>85%); absence≠zéro. Deux sens réunis, pas série directionnelle exhaustive."
        elif table=="aviation_emissions_annuelles":
            limits="CO₂net, SAF inclus, effets nonCO₂ exclus; pas CO₂e en cycledevie, pas inventaire territorial communal."
        else:limits="LSN regroupe les petites liaisons sous le seuil; trafic intérieur métropolitain, Corse comprise. Ne pas sommerMET_INTERIEURavec ses composants."
        return record(label,definition,unit,"DGAC EMI et notice archivée"if table=="aviation_emissions_annuelles"else DGAC,field,limits)
    return record("Champ aérien à documenter: "+c,"Variable brute conservée; définition non établie dans ce dictionnaire.","non établie",DGAC,c,"Consulter la notice avant usage; aucune unité inventée.","à vérifier")


def generate() -> dict:
    """Produit CSV exhaustif et Markdown lisible, à partir des schémas présents."""
    import pandas as pd

    DOC.mkdir(parents=True,exist_ok=True)
    names=["dataset_final_communes","gares_annees"]+sorted({p.stem for p in DATA.glob("*.csv")}-{ "dataset_final_communes","gares_annees"})
    rows=[];summaries=[]
    for name in names:
        parquet=DATA/f"{name}.parquet";csv_path=DATA/f"{name}.csv"
        if parquet.exists():frame=pd.read_parquet(parquet)
        elif csv_path.exists():frame=pd.read_csv(csv_path,dtype="string",keep_default_na=False)
        else:continue
        summaries.append({"table":name,"lignes":len(frame),"colonnes":len(frame.columns),"grain":readable(GRAINS.get(name,"Grain à vérifier dans le module producteur."))})
        for c in frame:
            meta=describe(c,name)
            missing=int(frame[c].isna().sum())
            if not parquet.exists():missing+=int(frame[c].eq("").sum())
            rows.append({"table":name,"variable":c,"type_stocke":str(frame[c].dtype),"nb_lignes_table":len(frame),"nb_manquants":missing,"part_manquante_pct":100*missing/len(frame) if len(frame) else 0,**meta})
    dictionary=pd.DataFrame(rows)
    assert not dictionary.duplicated(["table","variable"]).any()
    dictionary.to_csv(DOC/"dictionnaire_donnees.csv",index=False,encoding="utf-8-sig")
    def safe(value):return str(value).replace("|"," / ").replace("\n"," ")
    sections=["# Dictionnaire des données livrées","", "Généré hors ligne par `python -m src.dictionnaire` à partir des colonnes réellement présentes dans `data/processed/`. Le CSV associé fournit une ligne par table et variable, le type stocké, les valeurs manquantes, l'unité, la source, le champ brut et la formule ou définition.","", "Les codes sont des identifiants, jamais des quantités. Les valeurs manquantes restent distinctes des zéros. Les comptages de gares ne sont pas des voyages uniques ; les modes collectifs INSEE ne désignent pas exclusivement le train. Les projections Omphale et scénarios ne sont pas des observations. Les variables brutes conservées sans usage analytique sont signalées ; les réserves d'unité restent explicites.","", "## Tables disponibles","", "| Table | Lignes | Colonnes | Unité statistique et champ |","|---|---:|---:|---|"]
    for item in summaries:sections.append(f"| `{item['table']}` | {item['lignes']:,} | {item['colonnes']} | {safe(item['grain'])} |")
    for item in summaries:
        sections += ["",f"## {item['table']}","",item['grain'],"", "| Variable · type · manquants | Définition / formule | Unité | Source et champ source | Limites |","|---|---|---|---|---|"]
        for r in rows:
            if r["table"]!=item["table"]:continue
            variable=f"`{r['variable']}` · {r['type_stocke']} · {r['nb_manquants']}/{r['nb_lignes_table']}"
            source=r["source"]+("; champ: "+r["champ_source"]if r["champ_source"]else"")
            sections.append("| "+" | ".join(safe(x)for x in [variable,r["definition_ou_formule"],r["unite"],source,r["limites_et_champ"]])+" |")
    sections += ["", "## Sources et règles de lecture", "", "Les sources détaillées, URL, empreintes et périmètres sont documentés dans `notes_demographie.md`, `notes_climat.md`, `notes_aviation.md`, `notes_contexte_lgv.md` et le document de méthodologie. Les identifiants de pages INSEE entre parenthèses permettent de retrouver la publication exacte. Les notices DGAC archivées définissent les champs PAP/LSN/EMI.","", "Les effectifs INSEE de logement et mobilité peuvent être pondérés et non entiers. Les parts sont des ratios d'effectifs ; agréger des parts communales par simple moyenne ne donne pas une part régionale. Les indicateurs de croissance exigent une base strictement positive. Les divergences intersources restent visibles et neutralisent les ratios concernés selon le code de préparation.","", "Une colonne signalée «à vérifier» ne doit pas être utilisée sans compléter sa définition. Le dictionnaire n'invente aucune unité lorsque la notice ne la précise pas ; c'est notamment le cas de l'unité de distance PAP et de l'échelle TKT, inutilisées dans l'analyse principale.",""]
    (DOC/"DICTIONNAIRE_DONNEES.md").write_text("\n".join(sections),encoding="utf-8")
    pending=dictionary.loc[dictionary.statut_documentation.eq("à vérifier"),["table","variable"]].to_dict("records")
    result={"tables":len(summaries),"colonnes_documentees":len(dictionary),"variables_a_verifier":pending,"tableaux":summaries}
    (DOC/"dictionnaire_controle.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


if __name__=="__main__":
    print(json.dumps(generate(),ensure_ascii=False,indent=2))
