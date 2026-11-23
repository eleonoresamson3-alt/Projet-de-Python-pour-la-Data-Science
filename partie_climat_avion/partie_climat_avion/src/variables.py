import numpy as np
import pandas as pd

def build_tcam(population, annee_debut, annee_fin):
    """Taux de croissance annuel moyen de la population de chaque commune, en %."""
    debut, fin = population[f"pop_{annee_debut}"], population[f"pop_{annee_fin}"]
    n = annee_fin - annee_debut
    population = population.copy()
    population["tcam_pop"] = ((fin / debut.replace(0, np.nan)) ** (1 / n) - 1) * 100
    return population


def build_part_voiture(navettes, actifs_min):
    """Par commune de résidence : nombre d'actifs, d'actifs allant travailler en voiture, et part de la voiture."""
    navettes = navettes.assign(poids_voiture=navettes["poids"].where(navettes["mode"] == "voiture", 0))
    communes = navettes.groupby("commune_residence")[["poids", "poids_voiture"]].sum().reset_index()
    communes.columns = ["code_commune", "actifs", "actifs_voiture"]
    communes["part_voiture"] = communes["actifs_voiture"] / communes["actifs"] * 100
    communes["part_fiable"] = communes["actifs"] >= actifs_min
    return communes


def build_motorisation(parc, population, annee_fin):
    """Nombre de voitures des particuliers pour 1 000 habitants, par commune, en fin de période."""
    table = parc.merge(population, on="code_commune", how="inner", validate="one_to_one")
    habitants = table[f"pop_{annee_fin}"].replace(0, np.nan)
    table["voitures_1000_hab"] = table[f"PARC_{annee_fin}"] / habitants * 1000
    return table[["code_commune", f"PARC_{annee_fin}", f"pop_{annee_fin}", "voitures_1000_hab"]]


def build_distance_gare(communes, gares):
    """Distance (en km, à vol d'oiseau) du centre de chaque commune à la gare de voyageurs la plus proche."""
    centres = communes[["INSEE_COM", "INSEE_DEP", "geometry"]].copy()
    centres["geometry"] = centres.centroid
    proches = centres.sjoin_nearest(gares[["uic", "nom", "geometry"]], how="left", distance_col="distance_m")
    proches = proches.drop_duplicates(subset="INSEE_COM")
    proches["distance_gare_km"] = proches["distance_m"] / 1000
    # pas de trains SNCF en Corse (réseau CFC absent des données) : distance non calculée
    proches.loc[proches["INSEE_DEP"].isin(["2A", "2B"]), "distance_gare_km"] = np.nan
    return proches[["INSEE_COM", "nom", "distance_gare_km"]].rename(columns={"INSEE_COM": "code_commune", "nom": "gare_proche"})


def build_co2_navettes(navettes, communes, facteur_voiture, trajets_par_jour):
    """CO2 des navettes en voiture (kg par jour travaillé), par commune de résidence, distances à vol d'oiseau."""
    voiture = navettes[navettes["mode"] == "voiture"]
    flux = voiture.groupby(["commune_residence", "commune_travail"])["poids"].sum().reset_index()
    centres = communes[["INSEE_COM"]].copy()
    centres["x"] = communes.centroid.x
    centres["y"] = communes.centroid.y
    flux = flux.merge(centres.rename(columns={"INSEE_COM": "commune_residence"}), on="commune_residence")
    flux = flux.merge(centres.rename(columns={"INSEE_COM": "commune_travail"}), on="commune_travail", suffixes=("_res", "_trav"))
    flux["distance_km"] = np.sqrt((flux["x_res"] - flux["x_trav"]) ** 2 + (flux["y_res"] - flux["y_trav"]) ** 2) / 1000
    flux["co2_kg"] = flux["poids"] * flux["distance_km"] * trajets_par_jour * facteur_voiture
    return flux.groupby("commune_residence")[["co2_kg"]].sum().reset_index().rename(columns={"commune_residence": "code_commune"})

def build_table_communes(communes, population, part_voiture, motorisation, distance, co2):
    """Assemble toutes les variables communales dans une seule table, avec la géométrie des communes."""
    table = communes.rename(columns={"INSEE_COM": "code_commune"})
    table = table.merge(population, on="code_commune", how="left", validate="one_to_one")
    table = table.merge(part_voiture, on="code_commune", how="left", validate="one_to_one")
    table = table.merge(motorisation[["code_commune", "voitures_1000_hab"]], on="code_commune", how="left", validate="one_to_one")
    table = table.merge(distance, on="code_commune", how="left", validate="one_to_one")
    table = table.merge(co2, on="code_commune", how="left", validate="one_to_one")
    table["co2_kg_par_actif"] = table["co2_kg"] / table["actifs"]
    assert len(table) == len(communes), "la jointure a changé le nombre de communes"
    return table


def build_profils(table, seuil_tcam, seuil_km):
    """Typologie en 4 profils : commune en croissance ou non, desservie par une gare proche ou non."""
    table = table.copy()
    croissance = np.where(table["tcam_pop"] > seuil_tcam, "en croissance", "stable ou en déclin")
    desserte = np.where(table["distance_gare_km"] <= seuil_km, f"gare à {seuil_km} km ou moins", f"gare à plus de {seuil_km} km")
    table["profil"] = pd.Series(croissance, index=table.index) + " / " + pd.Series(desserte, index=table.index)
    connu = table["tcam_pop"].notna() & table["distance_gare_km"].notna()
    table["profil"] = table["profil"].where(connu)
    return table


def build_duree_train(horaires, villes):
    """Durée (minutes) du train direct le plus rapide entre chaque paire de villes de la table faite à la main."""
    gares = villes.loc[villes["type"] == "gare", ["ville", "code"]].rename(columns={"code": "uic"})
    passages = horaires.merge(gares, on="uic")
    trajets = passages.merge(passages, on="trip_id", suffixes=("_dep", "_arr"))
    trajets = trajets[(trajets["stop_sequence_dep"] < trajets["stop_sequence_arr"]) & (trajets["ville_dep"] != trajets["ville_arr"])]
    trajets["duree_min"] = trajets["arrivee_min_arr"] - trajets["depart_min_dep"]
    # même paire dans les deux sens : on range les deux villes par ordre alphabétique
    trajets["ville_1"] = trajets[["ville_dep", "ville_arr"]].min(axis=1)
    trajets["ville_2"] = trajets[["ville_dep", "ville_arr"]].max(axis=1)
    return trajets.groupby(["ville_1", "ville_2"])["duree_min"].min().reset_index()


def build_liaisons_avion(liaisons, villes, durees, seuils, facteur_avion, facteur_train, annee):
    """Ajoute à chaque liaison aérienne les villes, la durée du train, sa classe et le CO2 avion / train."""
    aeroport_ville = villes.loc[villes["type"] == "aeroport"].set_index("code")["ville"]
    table = liaisons.copy()
    table["ville_a"] = table["oaci_1"].map(aeroport_ville)
    table["ville_b"] = table["oaci_2"].map(aeroport_ville)
    table = table.dropna(subset=["ville_a", "ville_b"])
    table["ville_1"] = table[["ville_a", "ville_b"]].min(axis=1)
    table["ville_2"] = table[["ville_a", "ville_b"]].max(axis=1)
    table = table.merge(durees, on=["ville_1", "ville_2"], how="left")
    classes = pd.cut(table["duree_min"], bins=[0, seuils[0], seuils[1], np.inf],
                     labels=["moins de 2h30", "de 2h30 à 4h", "plus de 4h"])
    table["classe_train"] = classes.cat.add_categories("pas de train direct").fillna("pas de train direct")
    passagers_km = table[f"passagers_{annee}"] * table["distance_km"]
    table["co2_avion_t"] = passagers_km * facteur_avion / 1000
    # pas de CO2 « train » sans train direct : il n'y a pas d'alternative à comparer
    table["co2_train_t"] = (passagers_km * facteur_train / 1000).where(table["duree_min"].notna())
    return table.drop(columns=["ville_a", "ville_b"])


def build_departements(projections, gares, annee_fin, annee_projection):
    """Par département : évolution projetée de la population et nombre de gares pour 100 000 habitants."""
    debut, fin = f"pop_proj_{annee_fin}", f"pop_proj_{annee_projection}"
    gares_uniques = gares.drop_duplicates(subset=["nom", "code_commune"])
    nb_gares = gares_uniques["code_commune"].str[:2].value_counts().rename("nb_gares")
    table = projections.merge(nb_gares, left_on="code_departement", right_index=True, how="left")
    table["evolution_pop_pct"] = (table[fin] / table[debut] - 1) * 100
    table[f"gares_100k_hab_{annee_fin}"] = table["nb_gares"] / table[debut] * 100000
    table[f"gares_100k_hab_{annee_projection}"] = table["nb_gares"] / table[fin] * 100000
    return table

