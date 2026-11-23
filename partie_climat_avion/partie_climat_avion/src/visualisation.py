import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from shapely.geometry import LineString
from matplotlib.patches import Patch

BLEU = "#2a78d6"
GRIS = "#52514e"


def plot_voiture_distance(communes, chemin):
    """Nuage : part de la voiture dans les navettes selon la distance de la commune à la gare la plus proche."""
    fiables = communes[communes["part_fiable"] == True].copy()
    # médiane par tranche de 2 km, pour lire la tendance dans le nuage
    fiables["tranche"] = pd.cut(fiables["distance_gare_km"], bins=range(0, 42, 2))
    medianes = fiables.groupby("tranche", observed=True).agg(distance=("distance_gare_km", "median"),
                                                             part=("part_voiture", "median"))
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=fiables, x="distance_gare_km", y="part_voiture", s=12, alpha=0.3,
                    color=BLEU, edgecolor=None, ax=ax, label="une commune")
    ax.plot(medianes["distance"], medianes["part"], color="black", linewidth=2, label="médiane par tranche de 2 km")
    ax.set_title("Dès 5 km d'une gare, plus de 8 actifs sur 10 vont travailler en voiture", loc="left", fontweight="bold")
    ax.set_xlabel("Distance du centre de la commune à la gare la plus proche (km)")
    ax.set_ylabel("Part des actifs allant travailler en voiture (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower right")
    sns.despine(ax=ax)
    fig.text(0.01, 0.01, "Sources : INSEE (navettes 2022), SNCF (gares). Communes d'au moins 1 000 actifs.",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


def plot_correlations(correlations, chemin):
    """Heatmap de la matrice des corrélations, palette divergente centrée sur 0."""
    noms = {"tcam_pop": "Croissance de la\npopulation (TCAM)", "distance_gare_km": "Distance à\nla gare",
            "part_voiture": "Part de la voiture\n(navettes)", "voitures_1000_hab": "Voitures pour\n1 000 habitants",
            "co2_kg_par_actif": "CO2 des navettes\npar actif"}
    matrice = correlations.rename(index=noms, columns=noms)
    # on masque la diagonale et le triangle du haut, qui répètent l'information
    masque = np.triu(np.ones(matrice.shape, dtype=bool))
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(matrice, mask=masque, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, center=0,
                square=True, linewidths=2, linecolor="white", cbar_kws={"label": "Corrélation de Spearman"}, ax=ax)
    ax.set_title("La croissance démographique n'est liée ni à la desserte ni à la voiture",
                 loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, "Communes d'au moins 1 000 actifs. Sources : INSEE, SNCF, SDES, ADEME.", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


def map_co2(communes, lignes, gares, chemin):
    """Carte 4 : CO2 des navettes en voiture par actif, avec le réseau ferré et les gares."""
    carte = communes.copy()
    carte["classe_co2"] = pd.cut(carte["co2_kg_par_actif"], bins=[-1, 4, 6, 8, 10, 1000],
                                 labels=["moins de 4", "4 à 6", "6 à 8", "8 à 10", "plus de 10"])
    fig, ax = plt.subplots(figsize=(9, 9))
    carte.plot(ax=ax, color="#e9e8e4", linewidth=0)
    carte.dropna(subset=["classe_co2"]).plot(ax=ax, column="classe_co2", cmap="YlOrRd", linewidth=0, legend=True,
                                             legend_kwds={"title": "kg de CO2 par actif\net par jour travaillé",
                                                          "loc": "lower left", "frameon": False})
    lignes.plot(ax=ax, color="#2b2b2b", linewidth=0.4)
    gares.plot(ax=ax, color="#2b2b2b", markersize=0.3)
    ax.set_title("Les navettes en voiture émettent le plus dans les couronnes périurbaines",
                 loc="left", fontweight="bold")
    ax.set_axis_off()
    fig.text(0.01, 0.01, "Distances à vol d'oiseau, 2 trajets par jour, facteur ADEME. Valeurs imprécises dans les "
             "petites communes.\nSources : INSEE (navettes 2022), ADEME (Base Carbone), SNCF (gares, lignes en service).",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


def map_projections(departements, table_departements, lignes, gares, chemin):
    """Carte 7 : évolution projetée de la population 2023-2050 par département, avec le réseau ferré et les gares."""
    carte = departements.merge(table_departements, left_on="INSEE_DEP", right_on="code_departement")
    fig, ax = plt.subplots(figsize=(9, 9))
    carte.plot(ax=ax, column="evolution_pop_pct", cmap="RdBu", vmin=-20, vmax=20, edgecolor="white", linewidth=0.5,
               legend=True, legend_kwds={"label": "Évolution de la population 2023-2050 (%)", "shrink": 0.6})
    lignes.plot(ax=ax, color="#2b2b2b", linewidth=0.4)
    gares.plot(ax=ax, color="#2b2b2b", markersize=0.3)
    ax.set_title("D'ici 2050, la population grandirait surtout à l'Ouest et au Sud,\n"
                 "là où l'on compte déjà le moins de gares par habitant", loc="left", fontweight="bold")
    ax.set_axis_off()
    fig.text(0.01, 0.01, "Scénario central, réseau ferré actuel. Sources : INSEE (projections Omphale 2022), "
             "SNCF (gares, lignes en service).", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


# fond de carte gris clair (Esri), utilisable sans clé d'accès ; folium ajoute lui-même les crédits
FOND_CARTE = "Esri.WorldGrayCanvas"

# couleurs des classes de durée du train (palette vérifiée pour les daltoniens), gris = pas de train direct
COULEURS_TRAIN = {"moins de 2h30": "#1baf7a", "de 2h30 à 4h": "#eb6834",
                  "plus de 4h": "#2a78d6", "pas de train direct": "#a8a7a1"}


def plot_liaisons(liaisons, annee, chemin):
    """Nuage distance × passagers des liaisons aériennes intérieures (échelle log), couleur = durée du train."""
    publiees = liaisons.dropna(subset=[f"passagers_{annee}"]).copy()
    publiees["nom"] = publiees["aeroport_1"].str.title() + " – " + publiees["aeroport_2"].str.title()
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=publiees, x="distance_km", y=f"passagers_{annee}", hue="classe_train",
                    hue_order=list(COULEURS_TRAIN), palette=COULEURS_TRAIN, s=70, edgecolor="white", ax=ax)
    ax.set_yscale("log")
    for _, ligne in publiees.nlargest(3, f"passagers_{annee}").iterrows():
        ax.annotate(ligne["nom"], (ligne["distance_km"], ligne[f"passagers_{annee}"]),
                    xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.set_title(f"En {annee}, les grosses liaisons aériennes sont celles où le train dépasse 4h",
                 loc="left", fontweight="bold")
    ax.set_xlabel("Distance entre les deux aéroports (km)")
    ax.set_ylabel(f"Passagers en {annee} (échelle logarithmique)")
    ax.legend(title="Train direct le plus rapide", frameon=False, loc="lower right")
    sns.despine(ax=ax)
    fig.text(0.01, 0.01, "Liaisons intérieures publiées (secret statistique). Sources : DGAC (série PAP), SNCF (GTFS).",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


def map_liaisons(liaisons, aeroports, villes, departements, lignes, annee, chemin):
    """Carte 8 : arcs des liaisons aériennes (épaisseur = passagers, couleur = durée du train) sur le réseau ferré."""
    # liaisons absentes cette année (fermées ou sous secret statistique) : pas d'arc
    publiees = liaisons.dropna(subset=[f"passagers_{annee}"])
    position = aeroports.set_index("oaci").geometry
    # un arc = une ligne droite entre les deux aéroports, en Lambert 93 comme les autres couches
    arcs = gpd.GeoDataFrame(
        publiees,
        geometry=[LineString([position[a], position[b]]) for a, b in zip(publiees["oaci_1"], publiees["oaci_2"])],
        crs=aeroports.crs,
    ).sort_values(f"passagers_{annee}")  # les gros arcs sont dessinés en dernier, par-dessus les petits
    fig, ax = plt.subplots(figsize=(9, 9))
    # ordre des couches : fond, réseau ferré, arcs, puis aéroports et noms
    departements.plot(ax=ax, color="#f2f1ed", edgecolor="#dcdad3", linewidth=0.4)
    lignes.plot(ax=ax, color="#c9c7bf", linewidth=0.5)
    # épaisseur proportionnelle aux passagers, au moins 1 point pour que les petites liaisons restent visibles
    arcs.plot(ax=ax, color=arcs["classe_train"].astype(str).map(COULEURS_TRAIN),
              linewidth=1 + arcs[f"passagers_{annee}"] / 200000, alpha=0.9)
    # une étiquette par ville, placée sur son premier aéroport
    sites = villes[villes["type"] == "aeroport"].drop_duplicates(subset="ville")
    sites = sites[sites["code"].isin(set(arcs["oaci_1"]) | set(arcs["oaci_2"]))]
    for _, site in sites.iterrows():
        point = position[site["code"]]
        ax.plot(point.x, point.y, "o", color="#2b2b2b", markersize=4)
        ax.annotate(site["ville"], (point.x, point.y), xytext=(5, 4), textcoords="offset points", fontsize=8,
                    bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.8})
    # légende faite à la main (geopandas ne la crée pas pour des couleurs données directement),
    # seulement avec les classes présentes sur la carte
    presentes = [c for c in COULEURS_TRAIN if c in set(arcs["classe_train"].astype(str))]
    legende = [Line2D([0], [0], color=COULEURS_TRAIN[c], linewidth=4, label=c) for c in presentes]
    ax.legend(handles=legende, title="Train direct le plus rapide\n(épaisseur = passagers)", frameon=False, loc="lower left")
    ax.set_title(f"En {annee}, aucune liaison aérienne intérieure publiée n'a de train direct en moins de 2h30",
                 loc="left", fontweight="bold", fontsize=11)
    ax.set_axis_off()
    fig.text(0.01, 0.01, "Liaisons intérieures publiées (secret statistique), lignes droites entre aéroports. "
             "Sources : DGAC (PAP, APT), OurAirports, SNCF (GTFS, lignes).", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(chemin, dpi=150)
    return fig


def map_fond_france():
    """Fond de carte folium centré sur la France, avec un zoom plus doux et limité à l'échelle utile."""
    return folium.Map(
        location=[46.6, 2.5], zoom_start=6, tiles=FOND_CARTE,
        min_zoom=5, max_zoom=10,                                # pas de zoom inutile au-delà
        max_bounds=True, min_lat=40, max_lat=52, min_lon=-7, max_lon=11,  # la carte ne part pas hors de France
        prefer_canvas=True,                                     # dessin plus rapide des nombreuses lignes
        zoom_snap=0.5, zoom_delta=0.5, wheel_px_per_zoom_level=120,  # molette : demi-niveau de zoom, plus progressif
    )


def map_liaisons_interactive(liaisons, aeroports, villes, lignes, annee, chemin):
    """Carte 8 interactive (folium) : liaisons aériennes sur fond clair, infobulle et surbrillance au survol."""
    # liaisons publiées seulement ; les plus grosses ajoutées en dernier pour être au-dessus
    publiees = liaisons.dropna(subset=[f"passagers_{annee}"]).sort_values(f"passagers_{annee}").copy()
    position = aeroports.set_index("oaci").geometry
    arcs = gpd.GeoDataFrame(
        publiees,
        geometry=[LineString([position[a], position[b]]) for a, b in zip(publiees["oaci_1"], publiees["oaci_2"])],
        crs=aeroports.crs,
    ).to_crs(4326)  # folium travaille en latitude / longitude
    # textes de l'infobulle, préparés à l'avance
    arcs["liaison"] = arcs["aeroport_1"].str.title() + " – " + arcs["aeroport_2"].str.title()
    arcs["passagers"] = arcs[f"passagers_{annee}"].map(lambda n: f"{n:,.0f}".replace(",", " "))
    arcs["train"] = arcs["duree_min"].map(lambda d: "pas de train direct" if pd.isna(d) else f"{int(d // 60)} h {int(d % 60):02d}")
    arcs["couleur"] = arcs["classe_train"].astype(str).map(COULEURS_TRAIN)
    arcs["epaisseur"] = 2 + arcs[f"passagers_{annee}"] / 150000

    carte = map_fond_france()
    # tracés simplifiés à 500 m près : invisible à cette échelle, mais la carte bouge plus vite
    reseau = lignes[["geometry"]].simplify(500).to_crs(4326)
    folium.GeoJson(reseau, name="Réseau ferré en service",
                   style_function=lambda _: {"color": "#b5b4ae", "weight": 1}).add_to(carte)
    # chaque liaison garde sa couleur et son épaisseur ; au survol, elle passe en noir et s'épaissit
    folium.GeoJson(
        arcs[["liaison", "passagers", "train", "couleur", "epaisseur", "geometry"]],
        name=f"Liaisons aériennes {annee}",
        style_function=lambda arc: {"color": arc["properties"]["couleur"], "weight": arc["properties"]["epaisseur"],
                                    "opacity": 0.85},
        highlight_function=lambda arc: {"color": "#111111", "weight": arc["properties"]["epaisseur"] + 3, "opacity": 1},
        tooltip=folium.GeoJsonTooltip(fields=["liaison", "passagers", "train"],
                                      aliases=["Liaison", f"Passagers en {annee}", "Train direct le plus rapide"]),
    ).add_to(carte)
    # un point par ville desservie, avec son nom au survol
    sites = villes[(villes["type"] == "aeroport") & villes["code"].isin(set(arcs["oaci_1"]) | set(arcs["oaci_2"]))]
    for _, site in sites.drop_duplicates(subset="ville").iterrows():
        point = aeroports.loc[aeroports["oaci"] == site["code"]].iloc[0]
        folium.CircleMarker([point["latitude_deg"], point["longitude_deg"]], radius=4, color="#2b2b2b",
                            fill=True, fill_opacity=1, tooltip=site["ville"]).add_to(carte)
    # encadré avec le titre et la légende, en haut à gauche de la carte
    lignes_legende = "".join(
        f"<div><span style='display:inline-block;width:22px;height:5px;background:{couleur};"
        f"margin-right:6px;vertical-align:middle'></span>{classe}</div>"
        for classe, couleur in COULEURS_TRAIN.items() if classe in set(arcs["classe_train"].astype(str)))
    encadre = (f"<div style='position:fixed;top:12px;left:60px;z-index:9999;background:white;padding:8px 12px;"
               f"border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.3);font:13px sans-serif;max-width:330px'>"
               f"<b>Liaisons aériennes intérieures en {annee}</b><br>"
               f"<span style='color:#555'>Épaisseur = passagers. Survolez une liaison pour le détail.</span>"
               f"<div style='margin-top:6px'><b>Train direct le plus rapide</b>{lignes_legende}</div></div>")
    carte.get_root().html.add_child(folium.Element(encadre))
    folium.LayerControl(collapsed=False).add_to(carte)  # menu des couches, ouvert par défaut
    carte.save(chemin)
    return carte


def map_projections_interactive(departements, table_departements, lignes, chemin):
    """Carte 7 interactive (folium) : évolution projetée 2023-2050 et habitants par gare, au survol de chaque département."""
    carte_dep = departements.merge(table_departements, left_on="INSEE_DEP", right_on="code_departement")
    # habitants par gare, arrondis à la centaine pour l'infobulle (vide en Corse : pas de gare SNCF)
    carte_dep["hab_par_gare_2023"] = (carte_dep["pop_proj_2023"] / carte_dep["nb_gares"]).round(-2)
    carte_dep["hab_par_gare_2050"] = (carte_dep["pop_proj_2050"] / carte_dep["nb_gares"]).round(-2)
    carte_dep["evolution_pop_pct"] = carte_dep["evolution_pop_pct"].round(1)
    # palette divergente par paliers de 5 points, symétrique autour de 0 : rouge = baisse, bleu = hausse
    couleurs = folium.StepColormap(["#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#d1e5f0", "#92c5de", "#4393c3", "#2166ac"],
                                   index=[-20, -15, -10, -5, 0, 5, 10, 15, 20], vmin=-20, vmax=20,
                                   caption="Évolution de la population 2023-2050 (%), scénario central")
    carte = map_fond_france()
    # chaque département prend la couleur de son évolution ; au survol, contour épaissi et infobulle
    folium.GeoJson(
        carte_dep[["LIBELLE_DEPARTEMENT", "evolution_pop_pct", "nb_gares", "hab_par_gare_2023", "hab_par_gare_2050",
                   "geometry"]].to_crs(4326),
        name="Évolution de la population 2023-2050",
        style_function=lambda departement: {"fillColor": couleurs(departement["properties"]["evolution_pop_pct"]),
                                            "color": "white", "weight": 0.6, "fillOpacity": 0.85},
        highlight_function=lambda _: {"color": "#111111", "weight": 2},
        tooltip=folium.GeoJsonTooltip(
            fields=["LIBELLE_DEPARTEMENT", "evolution_pop_pct", "nb_gares", "hab_par_gare_2023", "hab_par_gare_2050"],
            aliases=["Département", "Évolution 2023-2050 (%)", "Gares", "Habitants par gare 2023",
                     "Habitants par gare 2050 (réseau actuel)"]),
    ).add_to(carte)
    # tracés simplifiés à 500 m près : invisible à cette échelle, mais la carte bouge plus vite
    reseau = lignes[["geometry"]].simplify(500).to_crs(4326)
    folium.GeoJson(reseau, name="Réseau ferré en service",
                   style_function=lambda _: {"color": "#3a3a3a", "weight": 1}).add_to(carte)
    couleurs.add_to(carte)  # légende des couleurs, en haut à droite
    folium.LayerControl(collapsed=False).add_to(carte)
    carte.save(chemin)
    return carte


def map_co2_interactive(communes, departements, lignes, annee_fin, chemin):
    """Carte 4 interactive (folium) : CO2 des navettes en voiture par actif, agrégé par département."""
    # agrégat par département (ratios de sommes) : plus léger et plus fiable que la commune
    communes = communes.assign(loin_gare=communes[f"pop_{annee_fin}"].where(communes["distance_gare_km"] > 10, 0))
    agregat = communes.groupby("INSEE_DEP").agg(actifs=("actifs", "sum"), actifs_voiture=("actifs_voiture", "sum"),
                                                co2_kg=("co2_kg", "sum"), habitants=(f"pop_{annee_fin}", "sum"),
                                                habitants_loin=("loin_gare", "sum"))
    agregat["co2_kg_par_actif"] = (agregat["co2_kg"] / agregat["actifs"]).round(1)
    agregat["part_voiture"] = (agregat["actifs_voiture"] / agregat["actifs"] * 100).round(0)
    agregat["part_loin_gare"] = (agregat["habitants_loin"] / agregat["habitants"] * 100).round(0)
    carte_dep = departements.merge(agregat, left_on="INSEE_DEP", right_index=True)
    # palette séquentielle : du jaune (peu d'émissions) au rouge foncé (beaucoup)
    couleurs = folium.StepColormap(["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"], index=[0, 5, 6, 7, 8, 11],
                                   vmin=0, vmax=11, caption="CO2 des navettes en voiture (kg par actif et par jour travaillé)")
    carte = map_fond_france()
    folium.GeoJson(
        carte_dep[["LIBELLE_DEPARTEMENT", "co2_kg_par_actif", "part_voiture", "part_loin_gare", "geometry"]].to_crs(4326),
        name="CO2 des navettes par actif",
        style_function=lambda dep: {"fillColor": couleurs(dep["properties"]["co2_kg_par_actif"]),
                                    "color": "white", "weight": 0.6, "fillOpacity": 0.85},
        highlight_function=lambda _: {"color": "#111111", "weight": 2},
        tooltip=folium.GeoJsonTooltip(
            fields=["LIBELLE_DEPARTEMENT", "co2_kg_par_actif", "part_voiture", "part_loin_gare"],
            aliases=["Département", "CO2 (kg par actif et par jour)", "Part de la voiture (%)",
                     "Habitants à plus de 10 km d'une gare (%)"]),
    ).add_to(carte)
    reseau = lignes[["geometry"]].simplify(500).to_crs(4326)
    folium.GeoJson(reseau, name="Réseau ferré en service",
                   style_function=lambda _: {"color": "#3a3a3a", "weight": 1}).add_to(carte)
    couleurs.add_to(carte)
    folium.LayerControl(collapsed=False).add_to(carte)
    carte.save(chemin)
    return carte


# couleurs des 4 profils : bleu = gare proche, rouge = gare loin ; foncé = croissance, clair = déclin
COULEURS_PROFILS = {"en croissance / gare à 10 km ou moins": "#2166ac",
                    "en croissance / gare à plus de 10 km": "#b2182b",
                    "stable ou en déclin / gare à 10 km ou moins": "#92c5de",
                    "stable ou en déclin / gare à plus de 10 km": "#f4a582"}


def map_profils(communes, lignes, chemin):
    """Carte des 4 profils de communes (croissance × desserte), avec le réseau ferré."""
    cible = communes[communes["profil"] == "en croissance / gare à plus de 10 km"]
    nb_communes = f"{len(cible):,}".replace(",", " ")
    actifs = round(cible["actifs"].sum() / 1e6, 1)
    fig, ax = plt.subplots(figsize=(9, 9))
    communes.plot(ax=ax, color="#e9e8e4", linewidth=0)  # communes sans profil (Corse) en gris
    communes.dropna(subset=["profil"]).plot(ax=ax, color=communes["profil"].dropna().map(COULEURS_PROFILS), linewidth=0)
    lignes.plot(ax=ax, color="#2b2b2b", linewidth=0.4)
    legende = [Patch(color=couleur, label=profil) for profil, couleur in COULEURS_PROFILS.items()]
    ax.legend(handles=legende, title="Profil de la commune", frameon=False, loc="lower left", fontsize=8)
    ax.set_title(f"{nb_communes} communes en croissance sont à plus de 10 km d'une gare :\n"
                 f"{str(actifs).replace('.', ',')} millions d'actifs y vivent", loc="left", fontweight="bold")
    ax.set_axis_off()
    fig.text(0.01, 0.01, "Croissance = TCAM 2017-2023 > 0. Distance du centre de la commune à la gare la plus proche, "
             "à vol d'oiseau. Corse non classée.\nSources : INSEE (séries historiques), SNCF (gares, lignes en service).",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(chemin, dpi=150)
    return fig


def plot_projections_barres(table_departements, chemin):
    """Q6 : 10 plus fortes hausses et 10 plus fortes baisses de population d'ici 2050, et habitants par gare."""
    deps = table_departements.dropna(subset=["nb_gares"]).copy()  # Corse exclue : pas de gare SNCF
    deps["hab_par_gare_2023"] = deps["pop_proj_2023"] / deps["nb_gares"]
    deps["hab_par_gare_2050"] = deps["pop_proj_2050"] / deps["nb_gares"]
    deps["nom"] = deps["nom_departement"] + " (" + deps["code_departement"] + ")"
    extremes = pd.concat([deps.nlargest(10, "evolution_pop_pct"), deps.nsmallest(10, "evolution_pop_pct")])
    extremes = extremes.sort_values("evolution_pop_pct")  # les hausses en haut du graphique
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 7), sharey=True)
    # à gauche : évolution projetée, bleu = hausse, rouge = baisse
    couleurs = ["#2166ac" if e > 0 else "#b2182b" for e in extremes["evolution_pop_pct"]]
    gauche.barh(extremes["nom"], extremes["evolution_pop_pct"], color=couleurs)
    gauche.axvline(0, color="black", linewidth=0.8)
    gauche.set_xlabel("Évolution de la population 2023-2050 (%)")
    # à droite : habitants par gare aujourd'hui (gris) et en 2050 à réseau constant (foncé)
    positions = range(len(extremes))
    droite.barh([y + 0.2 for y in positions], extremes["hab_par_gare_2023"], height=0.4, color="#bdbcb6", label="2023")
    droite.barh([y - 0.2 for y in positions], extremes["hab_par_gare_2050"], height=0.4, color="#3a3a3a",
                label="2050 (réseau actuel)")
    droite.set_xlabel("Habitants par gare")
    droite.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}".replace(",", " "))  # 10 000 plutôt que 10000
    droite.legend(frameon=False, loc="lower right")
    for ax in (gauche, droite):
        sns.despine(ax=ax)
    fig.suptitle("À réseau constant, chaque gare desservirait plus d'habitants dans l'Ouest et le Sud,\n"
                 "et moins dans le Nord-Est et le Centre", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, "Dix plus fortes hausses et dix plus fortes baisses (scénario central). Sources : INSEE "
             "(projections Omphale 2022), SNCF (gares de voyageurs).", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(chemin, dpi=150)
    return fig


def plot_co2_avion_train(liaisons, annee, chemin):
    """Q7 : CO2 émis par l'avion et par le même trafic en train, pour les liaisons qui ont un train direct."""
    avec_train = liaisons.dropna(subset=[f"passagers_{annee}", "co2_train_t"]).copy()
    rapport = avec_train["co2_avion_t"].sum() / avec_train["co2_train_t"].sum()
    # nom de la liaison suivi de la durée du train le plus rapide, par exemple « Paris-Orly – Nice (5 h 34) »
    duree = avec_train["duree_min"].map(lambda d: f"{int(d // 60)} h {int(d % 60):02d}")
    avec_train["nom"] = (avec_train["aeroport_1"].str.title() + " – " + avec_train["aeroport_2"].str.title()
                         + " (" + duree + ")")
    avec_train = avec_train.nlargest(10, "co2_avion_t").sort_values("co2_avion_t")
    positions = range(len(avec_train))
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh([y + 0.2 for y in positions], avec_train["co2_avion_t"] / 1000, height=0.4, color="#3a3a3a", label="Avion")
    ax.barh([y - 0.2 for y in positions], avec_train["co2_train_t"] / 1000, height=0.4, color="#1baf7a",
            label="Mêmes passagers en TGV")
    ax.set_yticks(list(positions), avec_train["nom"])
    ax.set_xlabel(f"Émissions en {annee} (milliers de tonnes)")
    ax.legend(frameon=False, loc="lower right")
    sns.despine(ax=ax)
    fig.suptitle(f"Sur les liaisons qui ont un train direct, le train émettrait\n"
                 f"environ {rapport:.0f} fois moins de CO2 que l'avion ({annee})", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, "Passagers × distance × facteur : avion = DGAC (CO2, vols intérieurs), train = Base Carbone "
             "(TGV, CO2e), même distance que le vol.\nDix liaisons qui émettent le plus. Entre parenthèses : train direct "
             "le plus rapide.", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    fig.savefig(chemin, dpi=150)
    return fig


def plot_taille_communes(communes, annee_fin, chemin):
    """Boîtes à moustaches : part de la voiture et CO2 par actif selon la taille de la commune."""
    classes = ["moins de 500", "500 à 2 000", "2 000 à 10 000", "10 000 à 50 000", "50 000 à 200 000", "plus de 200 000"]
    tailles = communes.copy()
    tailles["taille"] = pd.cut(tailles[f"pop_{annee_fin}"], bins=[0, 500, 2000, 10000, 50000, 200000, 10**8],
                               labels=classes)
    palette = sns.color_palette("Blues", n_colors=len(classes))  # plus foncé = commune plus grande
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(12, 5.5))
    # showfliers=False : on ne trace pas les valeurs extrêmes, nombreuses dans les toutes petites communes
    sns.boxplot(data=tailles, x="taille", y="part_voiture", hue="taille", palette=palette, legend=False,
                showfliers=False, dodge=False, ax=gauche)
    sns.boxplot(data=tailles, x="taille", y="co2_kg_par_actif", hue="taille", palette=palette, legend=False,
                showfliers=False, dodge=False, ax=droite)
    gauche.set_ylabel("Actifs allant travailler en voiture (%)")
    droite.set_ylabel("CO2 des navettes (kg par actif et par jour travaillé)")
    for ax in (gauche, droite):
        ax.set_xlabel("Taille de la commune (habitants)")
        ax.tick_params(axis="x", rotation=25)
        sns.despine(ax=ax)
    medianes = tailles.groupby("taille", observed=True)["part_voiture"].median()
    fig.suptitle(f"Plus la commune est grande, moins la voiture domine : médiane de {medianes.iloc[0]:.0f} % de voiture "
                 f"sous 500 habitants, {medianes.iloc[-1]:.0f} % au-dessus de 200 000", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, "Chaque boîte regroupe les communes d'une classe de taille ; trait central : médiane ; "
             "valeurs extrêmes non tracées. Sources : INSEE (navettes 2022, population 2023), ADEME.",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(chemin, dpi=150)
    return fig


def map_aeroports_gares(aeroports, gares, departements, annee, chemin):
    """Carte 9 : aéroports (taille = passagers) et gares de voyageurs, côte à côte, à la même échelle."""
    actifs = aeroports.dropna(subset=[f"passagers_{annee}"]).sort_values(f"passagers_{annee}", ascending=False)
    nb_gares = len(gares.drop_duplicates(subset=["nom", "code_commune"]))  # une gare peut avoir plusieurs codes UIC
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(12, 6.5))
    for ax in (gauche, droite):
        departements.plot(ax=ax, color="#f2f1ed", edgecolor="#dcdad3", linewidth=0.4)
        ax.set_axis_off()
    # bulles triées de la plus grande à la plus petite pour que les petites restent visibles
    actifs.plot(ax=gauche, color="#2a78d6", alpha=0.6, edgecolor="white",
                markersize=actifs[f"passagers_{annee}"] / 60000)
    gauche.set_title(f"{len(actifs)} aéroports (taille = passagers {annee})", fontsize=10)
    gares.drop_duplicates(subset=["nom", "code_commune"]).plot(ax=droite, color="#eb6834", markersize=1.5)
    droite.set_title(f"{nb_gares:,} gares de voyageurs".replace(",", " "), fontsize=10)
    fig.suptitle("L'avion se concentre sur quelques pôles, le rail irrigue tout le territoire",
                 x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, "Aéroports de métropole avec trafic commercial ; gares sans indication de fréquentation. "
             "Sources : DGAC (série APT), OurAirports, SNCF (gares de voyageurs).", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(chemin, dpi=150)
    return fig

def plot_trafic_interieur(trafic, chemin):
    """Évolution des passagers aériens intérieurs à la métropole depuis 1990, par type de liaison."""
    couleurs = {"Paris – province": "#2a78d6", "province – province": "#eb6834"}
    fig, ax = plt.subplots(figsize=(9, 5))
    for faisceau, couleur in couleurs.items():
        serie = trafic[trafic["faisceau"] == faisceau]
        ax.plot(serie["annee"], serie["LSN_PAX"] / 1e6, color=couleur, linewidth=2, marker="o", markersize=3.5,
                label=faisceau)
    # deux repères : le Covid et le décret de mai 2023 sur les liaisons de moins de 2h30 en train
    for annee, texte in [(2020, "Covid"), (2023, "décret\n2023-385")]:
        ax.axvline(annee, color="#9a9a9a", linestyle="--", linewidth=1)
        ax.text(annee + 0.2, 21.5, texte, fontsize=8, color="#6b6a66", va="top")
    ax.set_ylim(0, 22)
    ax.set_xlabel("Année")
    ax.set_ylabel("Passagers par an (millions)")
    ax.legend(frameon=False, loc="center left")
    sns.despine(ax=ax)
    fig.suptitle("Les vols entre Paris et la province reculent depuis 2000 ; les vols entre villes de province\n"
                 "ont progressé jusqu'en 2019 avant de chuter avec le Covid", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.01, "Vols commerciaux intérieurs à la métropole (Corse comprise), tous mois publiés. "
             "Source : DGAC, série LSN.", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.03, 1, 0.92))
    fig.savefig(chemin, dpi=150)
    return fig