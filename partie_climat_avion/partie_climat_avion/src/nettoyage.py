import geopandas as gpd
import pandas as pd

def clean_communes(communes, crs):
    """Garde les communes de métropole (Corse comprise), les colonnes utiles, en Lambert 93."""
    metropole = communes[~communes["INSEE_DEP"].str.startswith("97")]
    metropole = metropole[["INSEE_COM", "NOM", "INSEE_DEP", "INSEE_REG", "geometry"]]
    metropole = metropole.to_crs(crs)
    assert metropole["INSEE_COM"].is_unique, "code commune en double"
    assert (metropole["INSEE_COM"].str.len() == 5).all(), "code commune qui n'a pas 5 caractères"
    return metropole


def clean_gares(gares, crs):
    """Une ligne par code UIC (certaines gares en ont plusieurs),
     colonnes utiles, en Lambert 93."""
    gares = gares.copy()
    gares["uic"] = gares["codes_uic"].str.split(";")
    gares = gares.explode("uic")
    gares = gares[["uic", "nom", "codeinsee", "geometry"]].to_crs(crs)
    assert gares["uic"].is_unique, "code UIC en double"
    assert (gares["uic"].str.len() == 8).all(), "code UIC qui n'a pas 8 chiffres"
    return gares


def clean_gares_communes(gares, communes):
    """Donne à chaque gare un code commune du COG 2025 : celui de la SNCF s'il existe, sinon par 
    jointure spatiale."""
    gares = gares.sjoin(communes[["INSEE_COM", "geometry"]], how="left", predicate="within")
    gares = gares.drop(columns="index_right")
    assert gares["uic"].is_unique, "une gare rattachée à deux communes"
    # contours simplifiés : près d'une limite, le code SNCF est plus fiable que la position
    valide = gares["codeinsee"].isin(communes["INSEE_COM"])
    gares["code_commune"] = gares["codeinsee"].where(valide, gares["INSEE_COM"])
    return gares.drop(columns=["codeinsee", "INSEE_COM"])


def clean_lignes(lignes, crs):
    """Garde les tronçons du réseau ferré en service (statut « Exploitée »), en Lambert 93."""
    exploitees = lignes[lignes["statut"] == "Exploitée"]
    return exploitees[["code_ligne", "lib_ligne", "geometry"]].to_crs(crs)


def clean_population(population, annee_debut, annee_fin):
    """Population des communes en début et fin de période, une ligne par commune."""
    pop = population[(population["GEO_OBJECT"] == "COM") & (population["RP_MEASURE"] == "POP")].copy()
    pop["annee"] = pd.to_datetime(pop["TIME_PERIOD"]).dt.year
    pop = pop[pop["annee"].isin([annee_debut, annee_fin])]
    pop = pop.pivot_table(index="GEO", columns="annee", values="OBS_VALUE", observed=True).reset_index()
    pop.columns = ["code_commune", f"pop_{annee_debut}", f"pop_{annee_fin}"]
    pop["code_commune"] = pop["code_commune"].astype(str)
    assert pop["code_commune"].is_unique, "commune en double"
    return pop


def clean_code_arrondissement(code):
    """Ramène un code d'arrondissement de Paris, Lyon ou Marseille au code de la commune entière."""
    if code.startswith("751"):
        return "75056"
    if code.startswith("132"):
        return "13055"
    if code.startswith("6938"):
        return "69123"
    return code


def clean_parc_auto(parc, codes_communes, annee_debut, annee_fin):
    """Voitures des particuliers par commune du COG 2025 
    (arrondissements regroupés, codes inconnus retirés)."""
    colonnes = [f"PARC_{annee_debut}", f"PARC_{annee_fin}"]
    parc = parc.copy()
    parc["code_commune"] = parc["COMMUNE_CODE"].map(clean_code_arrondissement)
    parc = parc.groupby("code_commune")[colonnes].sum().reset_index()
    dans_cog = parc["code_commune"].isin(codes_communes)
    part_gardee = parc.loc[dans_cog, colonnes[1]].sum() / parc[colonnes[1]].sum()
    print("part des voitures gardées :", round(part_gardee * 100, 2), "%")
    return parc[dans_cog]


def clean_mobpro(mobpro, codes_communes):
    """Navettes domicile-travail : codes au COG 2025, 
    mode de transport en clair, résidents du COG seulement."""
    modes = {1: "pas de transport", 2: "marche", 3: "vélo", 4: "deux-roues motorisé",
             5: "voiture", 6: "transports en commun"}
    navettes = pd.DataFrame({
        "commune_residence": mobpro["COMMUNE"].astype(str).map(clean_code_arrondissement),
        "commune_travail": mobpro["DCLT"].astype(str).map(clean_code_arrondissement),
        "mode": mobpro["TRANS"].astype(int).map(modes),
        "poids": mobpro["IPONDI"],
    })
    dans_cog = navettes["commune_residence"].isin(codes_communes)
    print("part des actifs gardés :", round(navettes.loc[dans_cog, "poids"].sum() / navettes["poids"].sum() * 100, 2), "%")
    assert navettes["mode"].notna().all(), "mode de transport inconnu"
    return navettes[dans_cog]


def clean_projections(projections, annee_fin, annee_projection):
    """Population projetée des départements de métropole, en habitants, pour deux années."""
    debut, fin = f"POP_{annee_fin}", f"POP_{annee_projection}"
    proj = projections[~projections["DEP"].str.startswith("97")]
    proj = proj[["DEP", "LIBDEP", debut, fin]].copy()
    proj[debut] = proj[debut] * 1000
    proj[fin] = proj[fin] * 1000
    proj.columns = ["code_departement", "nom_departement", f"pop_proj_{annee_fin}", f"pop_proj_{annee_projection}"]
    assert len(proj) == 96, "il doit rester 96 départements de métropole"
    return proj


def clean_facteurs(facteurs, identifiants):
    """Dictionnaire {mode: facteur d'émission en kgCO2e par km} à partir de la réponse de la Base Carbone."""
    valeurs = facteurs.set_index("Identifiant_de_l'élément")["Total_poste_non_décomposé"]
    resultat = {mode: float(valeurs[code]) for mode, code in identifiants.items()}
    assert len(resultat) == len(identifiants), "facteur d'émission manquant"
    return resultat


def clean_liaisons(pap, annees):
    """Liaisons aériennes intérieures à la métropole : passagers par an, une ligne par paire d'aéroports."""
    interieur = pap[pap["PAP"].str.match(r"^LF.._LF..$")].copy()
    interieur["annee"] = interieur["ANMOIS"].str[:4].astype(int)
    liaisons = interieur.pivot_table(index=["PAP", "PAP1_LABEL", "PAP2_LABEL", "PAP_DIST"],
                                     columns="annee", values="PAP_PAX", aggfunc="sum").reset_index()
    liaisons.columns = ["paire", "aeroport_1", "aeroport_2", "distance_km"] + [f"passagers_{a}" for a in annees]
    liaisons["oaci_1"] = liaisons["paire"].str[:4]
    liaisons["oaci_2"] = liaisons["paire"].str[5:]
    assert liaisons["paire"].is_unique, "paire d'aéroports en double"
    return liaisons


def clean_aeroports(apt, aeroports, annees, crs):
    """Aéroports de métropole : passagers par an (DGAC) et position (OurAirports), en Lambert 93."""
    metropole = apt[apt["APT_ZON"] == "MT"].copy()
    metropole["annee"] = metropole["ANMOIS"].str[:4].astype(int)
    metropole["passagers"] = metropole["APT_PAX_dep"] + metropole["APT_PAX_arr"]
    trafic = metropole.pivot_table(index=["APT", "APT_NOM"], columns="annee", values="passagers", aggfunc="sum").reset_index()
    trafic.columns = ["oaci", "nom"] + [f"passagers_{a}" for a in annees]
    positions = aeroports[["ident", "latitude_deg", "longitude_deg"]].rename(columns={"ident": "oaci"})
    trafic = trafic.merge(positions, on="oaci", how="left", validate="one_to_one")
    print("aéroports sans coordonnées :", trafic["latitude_deg"].isna().sum())
    trafic = trafic.dropna(subset=["latitude_deg"])
    points = gpd.points_from_xy(trafic["longitude_deg"], trafic["latitude_deg"])
    return gpd.GeoDataFrame(trafic, geometry=points, crs=4326).to_crs(crs)


def clean_emissions_avion(emissions, annee):
    """Facteur d'émission de l'avion sur les vols intérieurs à la métropole, en kg CO2 par passager.km."""
    ligne = emissions[emissions["AN"] == "MET_INTERIEUR"]
    assert len(ligne) == 1, "ligne MET_INTERIEUR introuvable"
    return float(ligne[str(annee)].iloc[0]) / 1000


def clean_horaires(horaires, trajets, routes):
    """Horaires des trains seulement (sans les cars), avec le code UIC de la gare et les heures en minutes."""
    lignes_train = routes.loc[routes["route_type"] == "2", "route_id"]
    trajets_train = trajets.loc[trajets["route_id"].isin(lignes_train), "trip_id"]
    trains = horaires[horaires["trip_id"].isin(trajets_train)].copy()
    trains["uic"] = trains["stop_id"].str[-8:]
    depart = trains["departure_time"].str.split(":", expand=True).astype(int)
    arrivee = trains["arrival_time"].str.split(":", expand=True).astype(int)
    trains["depart_min"] = depart[0] * 60 + depart[1]
    trains["arrivee_min"] = arrivee[0] * 60 + arrivee[1]
    assert trains["uic"].str.isdigit().all(), "code UIC mal extrait"
    return trains[["trip_id", "stop_sequence", "uic", "depart_min", "arrivee_min"]]


def clean_departements(departements, crs):
    """Garde les départements de métropole (Corse comprise), en Lambert 93."""
    metropole = departements[~departements["INSEE_DEP"].str.startswith("97")]
    return metropole[["INSEE_DEP", "LIBELLE_DEPARTEMENT", "geometry"]].to_crs(crs)


def clean_controle_tamsir(parc, navettes, chemin):
    """Compare mes tables à celles de Tamsir : parc auto 2023 et part de la voiture dans les navettes."""
    tamsir = pd.read_csv(chemin, dtype={"code_commune": str}, low_memory=False)
    tamsir = tamsir[tamsir["metropole"]]
    parc = parc.merge(tamsir[["code_commune", "vp_particuliers_2023"]], on="code_commune")
    print("parc 2023 identique à Tamsir :", round((parc["PARC_2023"] == parc["vp_particuliers_2023"]).mean() * 100, 2), "% des communes")
    voiture = navettes.loc[navettes["mode"] == "voiture", "poids"].sum() / navettes["poids"].sum()
    voiture_tamsir = tamsir["navetteurs_voiture_2022"].sum() / tamsir["actifs_occupes_15p_2022"].sum()
    print("part de la voiture en métropole :", round(voiture * 100, 2), "% (moi) contre", round(voiture_tamsir * 100, 2), "% (Tamsir)")

def clean_trafic_interieur(lsn):
    """Passagers des vols intérieurs à la métropole par année : Paris-province (radiales) et province-province."""
    faisceaux = {"MET_RAD": "Paris – province", "MET_TRA": "province – province"}
    interieur = lsn[lsn["LSN_FSC"].isin(faisceaux)].copy()
    interieur["annee"] = interieur["ANMOIS"].str[:4].astype(int)
    interieur["faisceau"] = interieur["LSN_FSC"].map(faisceaux)
    trafic = interieur.groupby(["annee", "faisceau"])["LSN_PAX"].sum().reset_index()
    assert (interieur.groupby("annee")["ANMOIS"].nunique() == 12).all(), "année incomplète"
    return trafic