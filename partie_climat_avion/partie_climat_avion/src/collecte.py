import json
import os
import zipfile


import geopandas as gpd
import pandas as pd
import requests
from cartiflette import carti_download

from src.outils import get_fichier


def get_contours(niveau, annee):
    """Télécharge les contours (COMMUNE ou DEPARTEMENT) de toute la France avec cartiflette."""
    chemin = f"data/raw/contours_{niveau.lower()}_{annee}.parquet"
    if os.path.exists(chemin):
        print("déjà téléchargé :", chemin)
        return gpd.read_parquet(chemin)
    contours = carti_download(
        values="France",
        borders=niveau,
        filter_by="FRANCE_ENTIERE",
        year=annee,
        crs=4326,
    )
    contours.to_parquet(chemin)
    print("téléchargé :", chemin)
    return contours


def get_gares(url):
    """Télécharge la liste des gares de voyageurs SNCF (GeoJSON)
     et la lit avec geopandas."""
    chemin = get_fichier(url, "data/raw/gares_voyageurs.geojson")
    return gpd.read_file(chemin)


def get_lignes(url):
    """Télécharge les tracés des lignes du réseau ferré national avec
     leur statut (GeoJSON)."""
    chemin = get_fichier(url, "data/raw/lignes_par_statut.geojson")
    return gpd.read_file(chemin)


def get_mobpro(url):
    """Télécharge le fichier détail INSEE des navettes domicile-travail 2022
     (colonnes utiles seulement)."""
    chemin = get_fichier(url, "data/raw/RP2022_mobpro.parquet")
    colonnes = ["COMMUNE", "DCLT", "TRANS", "IPONDI"]
    return pd.read_parquet(chemin, columns=colonnes)


def get_facteurs_carbone(url, identifiants):
    """Interroge l'API Base Carbone de l'ADEME pour 
    une liste d'identifiants de facteurs d'émission."""
    chemin = "data/raw/base_carbone.json"
    if not os.path.exists(chemin):
        params = {
            "Identifiant_de_l'élément_in": ",".join(identifiants),
            "Type_Ligne_eq": "Elément",
            "size": 100,
        }
        reponse = requests.get(url, params=params, timeout=60)
        reponse.raise_for_status()
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(reponse.text)
    with open(chemin, encoding="utf-8") as f:
        resultats = json.load(f)["results"]
    return pd.DataFrame(resultats)


def get_population(url):
    """Télécharge les séries historiques du recensement (INSEE, millésime 2023)
    , au format long."""
    chemin = get_fichier(url, "data/raw/serie_historique_2023.parquet")
    return pd.read_parquet(chemin)


def get_parc_auto(url, annee_debut, annee_fin):
    """Interroge l'API DiDo du SDES : voitures des particuliers par commune, pour deux années."""
    chemin = "data/raw/parc_vp_particuliers.csv"
    if not os.path.exists(chemin):
        params = {
            "GROUPE": "eq:VP",
            "STATUT_UTILISATEUR": "eq:Particulier",
            "columns": f"COMMUNE_CODE,PARC_{annee_debut},PARC_{annee_fin}",
        }
        reponse = requests.get(url, params=params, timeout=120)
        reponse.raise_for_status()
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(reponse.text)
    return pd.read_csv(chemin, sep=";", dtype={"COMMUNE_CODE": str})


def get_projections(url):
    """Télécharge les projections de population Omphale 2022 (INSEE, scénario central)
     par département."""
    chemin = get_fichier(url, "data/raw/omphale_scenario_central.xlsx")
    return pd.read_excel(chemin, sheet_name="Population_DEP", skiprows=5, dtype={"DEP": str})


def get_pap(url, annees):
    """Télécharge la série PAP de la DGAC (trafic par paire d'aéroports) 
    et lit les années demandées."""
    chemin = get_fichier(url, "data/raw/dgac_pap_1990_2025.zip")
    archive = zipfile.ZipFile(chemin)
    tables = []
    for annee in annees:
        with archive.open(f"ASP_PAP_{annee}.csv") as f:
            tables.append(pd.read_csv(f, sep=";", decimal=",", encoding="utf-8-sig", dtype={"ANMOIS": str}))
    return pd.concat(tables)


def get_apt(url, annees):
    """Télécharge la série APT de la DGAC (trafic par aéroport) et lit les années demandées."""
    chemin = get_fichier(url, "data/raw/dgac_apt_1990_2025.zip")
    archive = zipfile.ZipFile(chemin)
    tables = []
    for annee in annees:
        with archive.open(f"ASP_APT_{annee}.csv") as f:
            tables.append(pd.read_csv(f, sep=";", decimal=",", encoding="utf-8-sig", dtype={"ANMOIS": str}))
    return pd.concat(tables)


def get_emissions_avion(url):
    """Télécharge les émissions unitaires de CO2 du trafic aérien publiées par la DGAC 
    (g CO2 / passager.km)."""
    chemin = get_fichier(url, "data/raw/dgac_emissions_unitaires.csv")
    return pd.read_csv(chemin, sep=";", decimal=",")


def get_aeroports(url):
    """Télécharge le référentiel OurAirports (codes et coordonnées des aéroports du monde)."""
    chemin = get_fichier(url, "data/raw/ourairports_airports.csv")
    colonnes = ["ident", "type", "name", "latitude_deg", "longitude_deg", "iso_country", "municipality", "iata_code"]
    return pd.read_csv(chemin, usecols=colonnes)


def get_gtfs(url):
    """Télécharge le GTFS national SNCF (horaires TGV, Intercités, TER) 
    et lit les quatre fichiers utiles."""
    chemin = get_fichier(url, "data/raw/gtfs_sncf.zip")
    archive = zipfile.ZipFile(chemin)
    arrets = pd.read_csv(archive.open("stops.txt"), dtype=str)
    colonnes = ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"]
    horaires = pd.read_csv(archive.open("stop_times.txt"), usecols=colonnes, dtype={"trip_id": str, "stop_id": str})
    trajets = pd.read_csv(archive.open("trips.txt"), usecols=["route_id", "trip_id"], dtype=str)
    routes = pd.read_csv(archive.open("routes.txt"), usecols=["route_id", "route_type"], dtype=str)
    return arrets, horaires, trajets, routes


def get_table_villes(chemin):
    """Lit la table faite à la main qui relie chaque ville à
     ses aéroports et à ses gares principales."""
    return pd.read_csv(chemin, sep=";", dtype=str)

def get_lsn(url):
    """Télécharge la série LSN de la DGAC (trafic mensuel par faisceau) et lit toutes les années."""
    chemin = get_fichier(url, "data/raw/dgac_lsn_1990_2025.zip")
    archive = zipfile.ZipFile(chemin)
    tables = []
    for nom in archive.namelist():
        with archive.open(nom) as f:
            tables.append(pd.read_csv(f, sep=";", decimal=",", encoding="utf-8-sig", dtype={"ANMOIS": str}))
    return pd.concat(tables)