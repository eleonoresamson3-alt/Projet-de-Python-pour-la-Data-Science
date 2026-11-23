"""Refait toute ma partie depuis zéro : collecte, nettoyage, variables, figures."""
import os

from src import collecte, nettoyage, variables, visualisation
from src.outils import charger_config

config = charger_config()
urls = config["urls"]
print("période étudiée :", config["annee_debut"], "-", config["annee_fin"])

# 1. collecte (un fichier déjà présent dans data/raw/ n'est pas retéléchargé)
communes = collecte.get_contours("COMMUNE", config["annee_cog"])
departements = collecte.get_contours("DEPARTEMENT", config["annee_cog"])
gares = collecte.get_gares(urls["gares"])
lignes = collecte.get_lignes(urls["lignes"])
mobpro = collecte.get_mobpro(urls["mobpro"])
population = collecte.get_population(urls["population"])
projections = collecte.get_projections(urls["projections"])
parc = collecte.get_parc_auto(urls["parc_auto"], config["annee_debut"], config["annee_fin"])
facteurs = collecte.get_facteurs_carbone(urls["base_carbone"], list(config["facteurs_base_carbone"].values()))
pap = collecte.get_pap(urls["dgac_pap"], config["annees_avion"])
apt = collecte.get_apt(urls["dgac_apt"], config["annees_avion"])
emissions_avion = collecte.get_emissions_avion(urls["dgac_emissions"])
aeroports = collecte.get_aeroports(urls["ourairports"])
arrets, horaires, trajets, routes = collecte.get_gtfs(urls["gtfs_sncf"])
villes = collecte.get_table_villes(config["table_villes"])
print("collecte terminée")

# 2. nettoyage
communes = nettoyage.clean_communes(communes, config["crs"])
codes = communes["INSEE_COM"]
propres = {
    "communes": communes,
    "departements": nettoyage.clean_departements(departements, config["crs"]),
    "gares": nettoyage.clean_gares_communes(nettoyage.clean_gares(gares, config["crs"]), communes),
    "lignes": nettoyage.clean_lignes(lignes, config["crs"]),
    "population": nettoyage.clean_population(population, config["annee_debut"], config["annee_fin"]),
    "parc_auto": nettoyage.clean_parc_auto(parc, codes, config["annee_debut"], config["annee_fin"]),
    "navettes": nettoyage.clean_mobpro(mobpro, codes),
    "projections": nettoyage.clean_projections(projections, config["annee_fin"], config["annee_projection"]),
    "liaisons": nettoyage.clean_liaisons(pap, config["annees_avion"]),
    "aeroports": nettoyage.clean_aeroports(apt, aeroports, config["annees_avion"], config["crs"]),
    "horaires_trains": nettoyage.clean_horaires(horaires, trajets, routes),
}
for nom, table in propres.items():
    table.to_parquet(f"{config['dossiers']['propre']}/{nom}.parquet")
print("tables propres enregistrées dans", config["dossiers"]["propre"])
if os.path.exists(config["table_tamsir"]):
    nettoyage.clean_controle_tamsir(propres["parc_auto"], propres["navettes"], config["table_tamsir"])

# 3. variables : partie climat (une ligne par commune)
facteurs = nettoyage.clean_facteurs(facteurs, config["facteurs_base_carbone"])
pop = variables.build_tcam(propres["population"], config["annee_debut"], config["annee_fin"])
table = variables.build_table_communes(
    communes,
    pop,
    variables.build_part_voiture(propres["navettes"], config["actifs_min_fiable"]),
    variables.build_motorisation(propres["parc_auto"], pop, config["annee_fin"]),
    variables.build_distance_gare(communes, propres["gares"]),
    variables.build_co2_navettes(propres["navettes"], communes, facteurs["voiture"], config["trajets_par_jour"]),
)
table = variables.build_profils(table, config["seuil_tcam_croissance"], config["seuil_distance_gare_km"])
table.to_parquet(f"{config['dossiers']['propre']}/table_communes.parquet")
print("table communale enregistrée :", table.shape)

# 3. variables : Q6 (une ligne par département)
departements_q6 = variables.build_departements(propres["projections"], propres["gares"], config["annee_fin"], config["annee_projection"])
departements_q6.to_parquet(f"{config['dossiers']['propre']}/table_departements.parquet")
print("table départementale enregistrée :", departements_q6.shape)

# 3. variables : avion (une ligne par liaison aérienne)
facteur_avion = nettoyage.clean_emissions_avion(emissions_avion, config["annee_emissions_avion"])
durees = variables.build_duree_train(propres["horaires_trains"], villes)
table_liaisons = variables.build_liaisons_avion(
    propres["liaisons"],
    villes,
    durees,
    config["seuils_duree_train_min"],
    facteur_avion,
    facteurs["tgv"],
    config["annees_avion"][1],
)
table_liaisons.to_parquet(f"{config['dossiers']['propre']}/table_liaisons.parquet")
print("table des liaisons enregistrée :", table_liaisons.shape)

# 5. cartes et graphiques, enregistrés dans le dossier figures
fig = config["dossiers"]["figures"]
annee_avion = config["annees_avion"][1]
contours_dep = propres["departements"]
fiables = table[table["part_fiable"] == True]
correlations = fiables[["tcam_pop", "distance_gare_km", "part_voiture", "voitures_1000_hab",
                        "co2_kg_par_actif"]].corr(method="spearman")

visualisation.plot_voiture_distance(table, f"{fig}/nuage_voiture_distance.png")
visualisation.plot_taille_communes(table, config["annee_fin"], f"{fig}/q3_taille_communes.png")
visualisation.plot_correlations(correlations, f"{fig}/heatmap_correlations.png")
visualisation.map_co2(table, propres["lignes"], propres["gares"], f"{fig}/carte4_co2_navettes.png")
visualisation.map_co2_interactive(table, contours_dep, propres["lignes"], config["annee_fin"], f"{fig}/carte4_interactive.html")
visualisation.map_profils(table, propres["lignes"], f"{fig}/carte_profils.png")
visualisation.map_projections(contours_dep, departements_q6, propres["lignes"], propres["gares"],
                              f"{fig}/carte7_projections_2050.png")
visualisation.map_projections_interactive(contours_dep, departements_q6, propres["lignes"], f"{fig}/carte7_interactive.html")
visualisation.plot_projections_barres(departements_q6, f"{fig}/q6_habitants_par_gare.png")
visualisation.plot_liaisons(table_liaisons, annee_avion, f"{fig}/nuage_liaisons_aeriennes.png")
visualisation.plot_co2_avion_train(table_liaisons, annee_avion, f"{fig}/q7_co2_avion_train.png")
visualisation.map_liaisons(table_liaisons, propres["aeroports"], villes, contours_dep, propres["lignes"], annee_avion,
                           f"{fig}/carte8_liaisons_aeriennes.png")
visualisation.map_liaisons_interactive(table_liaisons, propres["aeroports"], villes, propres["lignes"], annee_avion,
                                       f"{fig}/carte8_interactive.html")
visualisation.map_aeroports_gares(propres["aeroports"], propres["gares"], contours_dep, annee_avion,
                                  f"{fig}/carte9_aeroports_gares.png")
print("figures enregistrées dans", fig)

trafic_interieur = nettoyage.clean_trafic_interieur(collecte.get_lsn(urls["dgac_lsn"]))
visualisation.plot_trafic_interieur(trafic_interieur, f"{fig}/q7_trafic_interieur.png")