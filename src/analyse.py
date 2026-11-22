"""Analyse descriptive : unités, cohortes, dénominateurs et sensibilités explicites."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
import seaborn as sns

from .preparation import load_geography

FIG = ROOT / "outputs/figures"
TABLE = ROOT / "outputs/tables"


def table(df, name):
    df.to_csv(TABLE / f"{name}.csv", index=False, encoding="utf-8-sig")


def figure(fig, name, note="Sources : SNCF Gares & Connexions ; INSEE RP2022, COG2025. Calculs du projet."):
    fig.text(.02, .015, note, fontsize=8, color="#535d69", wrap=True)
    fig.tight_layout(rect=(0, .055, 1, 1))
    fig.savefig(FIG / f"{name}.png", dpi=180, facecolor="white")
    fig.savefig(FIG / f"{name}.svg", facecolor="white")
    plt.close(fig)


def gini(values):
    x = np.sort(np.asarray(values, dtype=float))
    if not len(x) or x.sum() == 0:
        return np.nan
    return float((2*np.dot(np.arange(1, len(x)+1), x)/(len(x)*x.sum()))-(len(x)+1)/len(x))


def pair_corr(frame, x, y):
    sub = frame[[x, y]].dropna()
    return {"n_communes": len(sub), "pearson": sub[x].corr(sub[y]), "spearman": sub[x].corr(sub[y], method="spearman")}


def share(numerator, denominator):
    return float(numerator / denominator * 100) if denominator > 0 else np.nan


def run():
    FIG.mkdir(parents=True, exist_ok=True)
    TABLE.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", font="DejaVu Sans", rc={"axes.spines.top": False, "axes.spines.right": False})
    com = pd.read_parquet(ROOT / "data/processed/dataset_final_communes.parquet")
    rail = pd.read_parquet(ROOT / "data/processed/gares_annees.parquet")
    metro = com[com.metropole].copy()
    candidate = metro[metro.tcam_rail_2016_2022_pct.notna() & metro.tcam_population_2016_2022_pct.notna()].copy()
    principal = candidate[~candidate.alerte_comparabilite_rail_population].copy()
    national = rail.groupby("annee", as_index=False).agg(
        comptages_voyageurs=("voyageurs", lambda x: x.sum(min_count=1)),
        nb_gares=("code_uic", "nunique"), nb_observations_valides=("voyageurs", "count"),
        nb_gares_positives=("voyageurs", lambda x: x.gt(0).sum()),
        mediane_comptages=("voyageurs", "median"))
    base = national.loc[national.annee.eq(2019), "comptages_voyageurs"].iloc[0]
    national["indice_base100_2019"] = national.comptages_voyageurs / base * 100
    table(national, "frequentation_annuelle")
    wide = rail.pivot(index="code_uic", columns="annee", values="voyageurs")
    fixed = wide.dropna().loc[lambda x: x[2019].gt(0)]
    balanced_sums = fixed.sum()
    national["indice_cohorte_complete_base100_2019"] = national.annee.map(balanced_sums / balanced_sums[2019] * 100)
    table(national, "frequentation_annuelle")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(national.annee, national.indice_base100_2019, "o-", color="#176b87", label="Toutes les observations publiées")
    ax.plot(national.annee, national.indice_cohorte_complete_base100_2019, "s--", color="#d17a22", label=f"Cohorte complète : {len(fixed):,} UIC")
    ax.axhline(100, color="grey", lw=.8)
    ax.set(title="Un choc en2020, puis une reprise à comparer à2019", xlabel="Année", ylabel="Indice des comptages en gare (2019=100)", xticks=national.annee)
    ax.legend()
    figure(fig, "01_evolution_rail", "Source : SNCF. Comptages en gare, pas des voyages uniques. Historique révisable ; périmètre non exhaustif.")
    last = rail.loc[rail.annee.eq(2024)].copy()
    amounts = last.voyageurs.dropna().astype(float)
    top_n = math.ceil(.1*len(amounts))
    decile_share = float(amounts.nlargest(top_n).sum()/amounts.sum()*100)
    lorenz = np.r_[0, np.cumsum(np.sort(amounts))/amounts.sum()]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    axes[0].hist(np.log10(amounts[amounts.gt(0)]), bins=45, color="#176b87")
    axes[0].set(title="Une fréquentation très inégale selon les gares", xlabel="log10(comptages annuels positifs), 2024", ylabel="Nombre de gares")
    axes[1].plot(np.linspace(0, 1, len(lorenz)), lorenz, color="#176b87", label=f"Gini = {gini(amounts):.3f}")
    axes[1].plot([0,1], [0,1], "--", color="grey")
    axes[1].set(title=f"Les10% de gares en tête concentrent {decile_share:.1f}% des comptages", xlabel="Part cumulée des gares", ylabel="Part cumulée des comptages")
    axes[1].xaxis.set_major_formatter(PercentFormatter(1))
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].legend()
    figure(fig, "02_concentration", "Source : SNCF, fréquentation2024. Les zéros publiés entrent dans Lorenz/Gini ; ils sont exclus du log10.")
    quantiles = amounts.quantile([0,.1,.25,.5,.75,.9,.99,1]).rename_axis("quantile").reset_index(name="comptages_voyageurs_2024")
    table(quantiles, "distribution_gares_2024")
    table(last.nlargest(20, "voyageurs")[["code_uic", "nom_gare", "code_commune", "voyageurs"]], "top20_gares_2024")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    size = np.sqrt(principal.voyageurs_cohorte_2022.astype(float))
    sizes = 5 + 90*size/size.max()
    for (label, sub), color in zip(principal.groupby("profil_rail_demographie"), sns.color_palette("colorblind", 4)):
        ax.scatter(sub.tcam_population_2016_2022_pct, sub.tcam_rail_2016_2022_pct,
                   s=sizes.loc[sub.index], color=color, alpha=.55, linewidth=0, label=label)
    ax.axhline(0, color="grey", lw=.8)
    ax.axvline(0, color="grey", lw=.8)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_yscale("symlog", linthresh=2)
    ax.set(title="Population et rail : des trajectoires communales dispersées", xlabel="Croissance annuelle moyenne population2016–2022 (%)", ylabel="Croissance annuelle moyenne comptages2016–2022 (%)")
    ax.legend(fontsize=8, title=None, loc="best")
    figure(fig, "03_rail_population", "Métropole, mêmes UIC observés aux deux dates, base2016>0 ; échelles symlog. Taille des points comprimée par racine carrée.")
    profiles = principal.groupby("profil_rail_demographie", as_index=False).agg(
        nb_communes=("code_commune", "size"), population_2022=("population_2022", "sum"),
        comptages_cohorte_2022=("voyageurs_cohorte_2022", "sum"))
    profiles["part_communes_pct"] = profiles.nb_communes / len(principal)*100
    table(profiles, "profils_rail_population")
    regional_source = metro.copy()
    regional_source.loc[regional_source.part_modale_voiture_2022_pct.isna(), ["navetteurs_voiture_2022", "actifs_occupes_15p_2022"]] = np.nan
    reg = regional_source.groupby(["code_region", "nom_region"], as_index=False).agg(
        population_2016=("population_2016", "sum"), population_2022=("population_2022", "sum"),
        solde_naturel=("solde_naturel_2016_2022", "sum"), solde_migratoire_apparent=("solde_migratoire_apparent_2016_2022", "sum"),
        voyageurs_cohorte_2016=("voyageurs_cohorte_2016", lambda x: x.sum(min_count=1)),
        voyageurs_cohorte_2022=("voyageurs_cohorte_2022", lambda x: x.sum(min_count=1)),
        navetteurs_voiture_2022=("navetteurs_voiture_2022", "sum"), actifs_occupes_15p_2022=("actifs_occupes_15p_2022", "sum"))
    reg["tcam_population_pct"] = ((reg.population_2022/reg.population_2016)**(1/6)-1)*100
    reg["tcam_rail_pct"] = ((reg.voyageurs_cohorte_2022/reg.voyageurs_cohorte_2016)**(1/6)-1)*100
    reg["part_modale_voiture_2022_pct"] = reg.navetteurs_voiture_2022/reg.actifs_occupes_15p_2022*100
    table(reg, "synthese_regions")
    # Une moyenne de pourcentages communaux n'est pas une part modale régionale.
    groups = []
    for name, sub in metro.groupby("trajectoire_demographique"):
        mob = sub[sub.part_modale_voiture_2022_pct.notna()]
        cars = sub[sub.part_menages_motorises_2022_pct.notna()]
        groups.append({"trajectoire_demographique": name, "n_communes": len(sub), "population_2022": sub.population_2022.sum(),
                       "n_communes_mobilite": len(mob), "n_communes_motorisation": len(cars),
                       "part_modale_voiture_2022_pct": share(mob.navetteurs_voiture_2022.sum(), mob.actifs_occupes_15p_2022.sum()),
                       "part_menages_motorises_2022_pct": share(cars.menages_au_moins_une_voiture_2022.sum(), cars.menages_2022.sum()),
                       "mediane_distance_centre_gare_km": sub.distance_centre_gare_km.median()})
    groups = pd.DataFrame(groups)
    table(groups, "mobilites_par_trajectoire")
    density_groups = []
    for name, sub in metro.groupby("libelle_densite_3"):
        mob = sub[sub.part_modale_voiture_2022_pct.notna()]
        density_groups.append({"classe_densite": name, "n_communes": len(sub), "n_communes_mobilite": len(mob), "population_2022": sub.population_2022.sum(),
                               "part_modale_voiture_2022_pct": 100*mob.navetteurs_voiture_2022.sum()/mob.actifs_occupes_15p_2022.sum(),
                               "distance_centre_gare_km_mediane": sub.distance_centre_gare_km.median(),
                               "population_proxy_plus10km_pct": 100*sub.loc[sub.distance_centre_gare_km.gt(10),"population_2022"].sum()/sub.loc[sub.distance_centre_gare_km.notna(),"population_2022"].sum()})
    table(pd.DataFrame(density_groups), "mobilites_par_densite")
    modal = principal.dropna(subset=["variation_part_modale_voiture_2016_2022_points"])
    modal_correlation = pair_corr(modal, "tcam_rail_2016_2022_pct", "variation_part_modale_voiture_2016_2022_points")
    table(pd.DataFrame([modal_correlation]), "correlation_rail_evolution_voiture")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(modal.tcam_rail_2016_2022_pct, modal.variation_part_modale_voiture_2016_2022_points, s=8, alpha=.35, color="#176b87")
    ax.set_xscale("symlog", linthresh=2)
    ax.axhline(0, color="grey", lw=.8)
    ax.axvline(0, color="grey", lw=.8)
    ax.set(title="Rail et voiture : une comparaison des évolutions communales", xlabel="TCAM des comptages en gare2016–2022 (%) ; échelle symlog", ylabel="Variation de la part voiture2016–2022 (points)")
    figure(fig, "11_rail_evolution_voiture", f"INSEE/SNCF ; {len(modal):,} communes avec données comparables aux deux dates. Association entre évolutions, sans identification d'un effet d'éviction.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(groups.trajectoire_demographique, groups.part_modale_voiture_2022_pct, color=["#176b87", "#d17a22", "#6f8f72", "grey"][:len(groups)])
    ax.set(title="La voiture dans les déplacements domicile–travail", xlabel="Trajectoire démographique2016–2022 (seuil ±0,2%/an)", ylabel="Part des actifs occupés utilisant principalement la voiture (%)", ylim=(0,100))
    figure(fig, "04_voiture_trajectoire", "INSEE RP2022. Ratios des effectifs agrégés ; tous les actifs occupés de15ans ou plus au dénominateur. Association descriptive.")
    variables = ["tcam_population_2016_2022_pct", "tcam_rail_2016_2022_pct", "comptages_gares_par_habitant_2022", "part_modale_voiture_2022_pct", "part_menages_motorises_2022_pct", "densite_population_2022_hab_km2"]
    names = ["Croissance population", "Croissance rail", "Comptages/habitant", "Part voiture", "Ménages motorisés", "Densité"]
    corr = principal[variables].corr(method="spearman")
    count = principal[variables].notna().astype(int).T.dot(principal[variables].notna().astype(int))
    table(corr.rename_axis("variable").reset_index(), "correlations_spearman")
    table(principal[variables].corr().rename_axis("variable").reset_index(), "correlations_pearson")
    table(count.rename_axis("variable").reset_index(), "effectifs_correlations")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, xticklabels=names, yticklabels=names, ax=ax)
    ax.set_title("Corrélations de rang entre les caractéristiques communales")
    figure(fig, "05_correlations", "Spearman ; communes métropolitaines avec cohorte ferroviaire, effectifs par paire dans la table associée. Corrélation ≠ causalité.")
    transitions = wide.loc[wide[2015].gt(0) & wide[2024].gt(0), [2015,2024]].copy()
    transitions["quintile_2015"] = pd.qcut(transitions[2015], 5, labels=[1,2,3,4,5])
    transitions["quintile_2024"] = pd.qcut(transitions[2024], 5, labels=[1,2,3,4,5])
    transition = pd.crosstab(transitions.quintile_2015, transitions.quintile_2024, normalize="index")*100
    table(transition.reset_index(), "transitions_quintiles")
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(transition, annot=True, fmt=".1f", cmap="Blues", ax=ax, cbar_kws={"label": "% du quintile de départ"})
    ax.set(title="La position des gares dans la distribution2015–2024", xlabel="Quintile2024 (5=plus fréquenté)", ylabel="Quintile2015")
    figure(fig, "06_transitions", f"SNCF ; {len(transitions):,} UIC positifs aux deux dates ; quintiles recalculés chaque année. Pourcentages par ligne.")
    accessibility = []
    coverage = metro[metro.distance_centre_gare_km.notna()]
    positive_growth = coverage.variation_population_2016_2022.clip(lower=0).sum()
    for threshold in (5,10,15):
        far = coverage[coverage.distance_centre_gare_km.gt(threshold)]
        accessibility.append({"seuil_km": threshold, "nb_communes": len(far), "population_communes_concernees_2022": far.population_2022.sum(),
                              "population_champ_2022": coverage.population_2022.sum(),
                              "part_population_proxy_pct": 100*far.population_2022.sum()/coverage.population_2022.sum(),
                              "croissance_positive_concernee": far.variation_population_2016_2022.clip(lower=0).sum(),
                              "part_croissance_positive_proxy_pct": 100*far.variation_population_2016_2022.clip(lower=0).sum()/positive_growth})
    table(pd.DataFrame(accessibility), "accessibilite_proxy")
    sensitivities = []
    masks = {"communes avec cohorte": pd.Series(True,index=principal.index), "hors Île-de-France": principal.code_region.ne("11"),
             "comptages2016 au moins10000": principal.voyageurs_cohorte_2016.ge(10000),
             "hors1% des comptages2022 les plus élevés": principal.voyageurs_cohorte_2022.le(principal.voyageurs_cohorte_2022.quantile(.99))}
    for label, mask in masks.items():
        sensitivities.append({"champ":label, **pair_corr(principal[mask], variables[0], variables[1])})
    sensitivities.append({"champ":"incluant les alertes géographiques INSEE", **pair_corr(candidate, variables[0],variables[1])})
    table(pd.DataFrame(sensitivities), "sensibilite_correlations")
    # Cartes : la saturation chromatique à ±2%/an est annoncée, pas des données tronquées.
    geo = load_geography()
    geo = geo[geo.code_commune.isin(metro.code_commune)].to_crs(2154).merge(metro, on="code_commune", how="left", validate="one_to_one")
    network = None
    try:
        import geopandas as gpd
        network = gpd.read_file(ROOT / "data/raw/sncf/reseau.geojson").to_crs(2154)
    except Exception as exc:
        raise RuntimeError("Fond de réseau attendu mais illisible") from exc
    fig, ax = plt.subplots(figsize=(9, 9))
    geo.plot(column="tcam_population_2016_2022_pct", cmap="RdBu", vmin=-2, vmax=2, ax=ax, linewidth=0, legend=True,
             legend_kwds={"label":"Croissance annuelle moyenne2016–2022 (%) ; couleurs saturées à ±2"})
    network.plot(ax=ax, color="#30383b", linewidth=.13, alpha=.35)
    ax.set(title="La croissance démographique varie fortement dans l'espace")
    ax.set_axis_off()
    figure(fig,"07_carte_demographie", "INSEE ; contours Etalab2025 simplifiés100m ; réseau SNCF en fond (ensemble des lignes, statut non filtré). Métropole.")
    fig, ax = plt.subplots(figsize=(9, 9))
    geo.plot(ax=ax, color="#e8ecef", linewidth=0)
    last_known = last[last.longitude.notna() & last.latitude.notna() & last.voyageurs.gt(0)].copy()
    import geopandas as gpd
    points = gpd.GeoDataFrame(last_known, geometry=gpd.points_from_xy(last_known.longitude, last_known.latitude), crs=4326).to_crs(2154)
    base2015 = wide[2015]
    points["croissance"] = (points.voyageurs.astype(float)/points.code_uic.map(base2015).astype(float).where(points.code_uic.map(base2015).gt(0))-1)*100
    points = points.sort_values("voyageurs",ascending=False)
    points.plot(ax=ax, column="croissance", cmap="RdBu", vmin=-50, vmax=50,
                markersize=1+120*np.sqrt(points.voyageurs.astype(float)/points.voyageurs.max()), alpha=.7, legend=True,
                legend_kwds={"label":"Évolution des comptages2015–2024 (%) ; couleurs saturées à ±50"}, missing_kwds={"color":"grey"})
    ax.set(title="Le réseau des gares présente des évolutions contrastées")
    ax.set_axis_off()
    figure(fig,"08_carte_gares", "SNCF ; points : gares positives2024, taille comprimée par racine carrée ; gris : évolution non définie. Coordonnées du référentiel actuel.")
    fig, ax = plt.subplots(figsize=(9, 9))
    geo.plot(column="distance_centre_gare_km", cmap="YlOrRd", vmin=0, vmax=30, ax=ax, linewidth=0, legend=True,
             legend_kwds={"label":"Distance à vol d'oiseau depuis le centre géométrique communal (km), saturation30"}, missing_kwds={"color":"#d5dae0"})
    ax.set(title="Un indicateur approché de l'éloignement des gares observées")
    ax.set_axis_off()
    figure(fig,"09_carte_distance", "Métropole hors Corse ; Corse grisée (réseau CFC absent de la source SNCF). Gares SNCF observées : proxy communal, pas une couverture de tous les réseaux ferrés.")
    # Carte et table des scénarios officiels Omphale, sans extrapolation communale.
    projection_path = ROOT / "data/processed/climat_projections_departements.parquet"
    if projection_path.exists():
        projection = pd.read_parquet(projection_path)
        central = projection[projection.scenario_insee.eq("central")]
        dep = load_geography("departements").rename(columns={"code":"code_departement"})
        dep = dep[~dep.code_departement.str.startswith("97")].to_crs(2154).merge(central,on="code_departement",validate="one_to_one")
        fig,ax = plt.subplots(figsize=(9,9))
        dep.plot(column="croissance_projetee_2018_2050_pct",cmap="RdBu",vmin=-20,vmax=20,ax=ax,edgecolor="white",linewidth=.3,legend=True,
                 legend_kwds={"label":"Population projetée2018–2050 (%) ; scénario central"})
        ax.set_title("Les projections INSEE dessinent des besoins territoriaux différents")
        ax.set_axis_off()
        figure(fig,"10_carte_projections", "INSEE Omphale2022, scénario central, départements ; contours2025. Projection conditionnelle, pas une prévision ni un besoin de trains chiffré.")
    # Carte interactive autonome : Plotly embarqué, fond sans tuiles externes.
    import plotly.express as px
    interactive = points.drop(columns="geometry")
    interactive["x_l93"] = points.geometry.x
    interactive["y_l93"] = points.geometry.y
    pfig = px.scatter(interactive, x="x_l93", y="y_l93", size="voyageurs", color="croissance", color_continuous_scale="RdBu",
                      range_color=(-50,50), hover_name="nom_gare", hover_data={"code_uic":True,"code_commune":True,"voyageurs":True,"x_l93":False,"y_l93":False},
                      title="Gares SNCF : comptages2024 et évolution2015–2024", size_max=25)
    import plotly.graph_objects as go
    outlines = load_geography("regions")
    outlines = outlines[~outlines.code.str.startswith(("01","02","03","04","06"))].to_crs(2154)
    xs, ys = [], []
    for geometry in outlines.geometry.simplify(500):
        polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
        for polygon in polygons:
            x, y = polygon.exterior.xy
            xs.extend(list(x)+[None]); ys.extend(list(y)+[None])
    pfig.add_trace(go.Scatter(x=xs,y=ys,mode="lines",line={"color":"#9ba9b3","width":.6},hoverinfo="skip",showlegend=False))
    pfig.data = (pfig.data[-1],) + pfig.data[:-1]
    pfig.update_xaxes(visible=False)
    pfig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    pfig.update_layout(template="plotly_white",height=800,margin={"l":10,"r":20,"b":10,"t":70},coloraxis_colorbar_title="Évolution (%)")
    pfig.write_html(ROOT / "outputs/carte_gares_interactive.html",include_plotlyjs=True)
    stats = {
        "gares_2024": len(last), "somme_comptages_2024": int(amounts.sum()), "gini_gares_2024": gini(amounts),
        "part_top10pct_gares_pct": decile_share, "top10pct_n": top_n,
        "indice_2020_base100_2019": float(national.loc[national.annee.eq(2020),"indice_base100_2019"].iloc[0]),
        "indice_2024_base100_2019": float(national.loc[national.annee.eq(2024),"indice_base100_2019"].iloc[0]),
        "communes_metropole": len(metro), "population_metropole_2022": float(metro.population_2022.sum()),
        "n_communes_principal": len(principal), "correlation_population_rail":pair_corr(principal,variables[0],variables[1]),
        "population_champ_principal_2022": float(principal.population_2022.sum()),
        "part_population_principal_pct": float(principal.population_2022.sum()/metro.population_2022.sum()*100),
        "correlation_rail_evolution_voiture": modal_correlation,
        "population_croissance_rail_baisse": int(((principal.tcam_population_2016_2022_pct>0)&(principal.tcam_rail_2016_2022_pct<0)).sum()),
        "accessibilite_proxy": accessibility,
    }
    (TABLE/"indicateurs.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2,default=float),encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False,indent=2,default=float))
    return stats


if __name__ == "__main__":
    run()
