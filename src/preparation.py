"""Tables finales : clés explicites, géographie COG2025 et cohortes comparables."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]


def save(df, name):
    target = ROOT / "data/processed" / name
    df.to_parquet(target.with_suffix(".parquet"), index=False)
    df.to_csv(target.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def load_ods(name):
    rows = []
    for p in sorted((ROOT / "data/raw/sncf" / name).glob("page_?????.json")):
        rows.extend(json.loads(p.read_text(encoding="utf-8"))["results"])
    meta = json.loads((ROOT / "data/raw/sncf" / name / "metadata.json").read_text(encoding="utf-8"))
    assert len(rows) == meta["metas"]["default"]["records_count"], name
    return pd.DataFrame(rows)


def load_geography(level="communes"):
    with gzip.open(ROOT / f"data/raw/geographie/{level}-100m.geojson.gz", "rt", encoding="utf-8") as stream:
        obj = json.load(stream)
    geo = gpd.GeoDataFrame.from_features(obj["features"], crs=4326)
    geo = geo.rename(columns={"code": "code_commune"} if level == "communes" else {})
    if level == "communes":
        assert geo["code_commune"].is_unique
    return geo


def build():
    out = ROOT / "outputs/tables"
    out.mkdir(parents=True, exist_ok=True)
    demo = pd.read_parquet(ROOT / "data/processed/demographie_communes.parquet")
    geo = load_geography()
    # Les distances sont définies uniquement en métropole, où EPSG:2154 convient.
    valid_codes = set(demo.code_commune)
    metro = geo.loc[geo.code_commune.isin(valid_codes) & ~geo["code_commune"].str.startswith(("97", "98"))].copy().to_crs(2154)
    freq = load_ods("frequentation-gares").rename(columns={"code_uic_complet": "code_uic"})
    assert freq.code_uic.is_unique
    assert freq.code_uic.str.fullmatch(r"\d{8}").all()
    gc = load_ods("gares-de-voyageurs")
    gc["code_uic"] = gc.codes_uic.fillna("").str.findall(r"\d{8}")
    gc = gc.explode("code_uic").dropna(subset=["code_uic"])
    gc["longitude"] = gc.position_geographique.map(lambda p: p.get("lon") if isinstance(p, dict) else None)
    gc["latitude"] = gc.position_geographique.map(lambda p: p.get("lat") if isinstance(p, dict) else None)
    conflicts = gc[gc.code_uic.duplicated(keep=False)]
    conflicts.to_csv(out / "uic_doublons_referentiel.csv", index=False, encoding="utf-8-sig")
    # Une ambiguïté du référentiel n'est jamais résolue en choisissant une ligne au hasard.
    gc = gc.loc[~gc.code_uic.isin(conflicts.code_uic)].copy()
    gc = gc.rename(columns={"codeinsee": "code_commune_source"})
    gc = gc[["code_uic", "code_commune_source", "longitude", "latitude"]]
    stations = freq.merge(gc, on="code_uic", how="left", validate="one_to_one")
    stations["source_coordonnees"] = np.where(stations.longitude.notna(), "SNCF Gares & Connexions", None)
    # SNCF Réseau peut contenir plusieurs projections sur des lignes pour le même UIC.
    network = load_ods("liste-des-gares")
    network = network.groupby("code_uic", as_index=False).agg(
        longitude_reseau=("x_wgs84", "median"), latitude_reseau=("y_wgs84", "median"),
        nb_projections_reseau=("code_uic", "size"),
        xmin=("x_l93", "min"), xmax=("x_l93", "max"), ymin=("y_l93", "min"), ymax=("y_l93", "max"))
    network["dispersion_projections_reseau_m"] = np.hypot(network.xmax-network.xmin, network.ymax-network.ymin)
    network = network.drop(columns=["xmin", "xmax", "ymin", "ymax"])
    stations = stations.merge(network, on="code_uic", how="left", validate="one_to_one")
    fallback = stations.longitude.isna() & stations.longitude_reseau.notna()
    fallback &= stations.dispersion_projections_reseau_m.le(1000)
    stations.loc[fallback, "longitude"] = stations.loc[fallback, "longitude_reseau"]
    stations.loc[fallback, "latitude"] = stations.loc[fallback, "latitude_reseau"]
    stations.loc[fallback, "source_coordonnees"] = "SNCF Réseau, médiane des projections UIC"
    stations = stations.drop(columns=["longitude_reseau", "latitude_reseau"])
    passage = pd.read_csv(ROOT / "data/processed/demographie_passage_cog2025.csv", dtype=str)
    # Accepte les noms explicites du module INSEE, sans jointure sur les libellés.
    source_col = next(x for x in ["code_commune_source", "code_source", "COM", "code_commune"] if x in passage)
    target_col = next(x for x in ["code_commune_cog2025", "code_commune_cible", "code_cible", "COMPARENT", "code_parent"] if x in passage and x != source_col)
    mapping = passage.set_index(source_col)[target_col].to_dict()
    stations["code_commune"] = stations.code_commune_source.map(mapping).fillna(stations.code_commune_source)
    stations.loc[~stations.code_commune.isin(valid_codes), "code_commune"] = pd.NA
    stations["methode_jointure_commune"] = np.where(stations.code_commune.notna(), "code INSEE / parent COG2025", None)
    needs = stations.code_commune.isna() & stations.longitude.notna() & stations.latitude.notna()
    if needs.any():
        pts = gpd.GeoDataFrame(stations.loc[needs, ["code_uic"]],
                               geometry=gpd.points_from_xy(stations.loc[needs, "longitude"], stations.loc[needs, "latitude"]),
                               crs=4326).to_crs(2154)
        candidates = gpd.sjoin(pts, metro[["code_commune", "geometry"]], how="left", predicate="within")
        unique = candidates.loc[~candidates.index.duplicated(keep=False)].dropna(subset=["code_commune"])
        stations.loc[unique.index, "code_commune"] = unique.code_commune
        stations.loc[unique.index, "methode_jointure_commune"] = "point dans polygone COG2025 simplifié 100 m"
    # Pas d'affectation automatique au polygone le plus proche : frontières ambiguës conservées.
    missing = stations[stations.code_commune.isna() | stations.longitude.isna() | stations.latitude.isna()].copy()
    missing.to_csv(out / "gares_jointure_incomplete.csv", index=False, encoding="utf-8-sig")
    stations[stations.dispersion_projections_reseau_m.gt(1000)].to_csv(out / "gares_projections_dispersees.csv", index=False, encoding="utf-8-sig")
    cols = []
    for name in freq:
        if re.fullmatch(r"total_?voyageurs_?20\d{2}", name):
            cols.append(name)
    long = stations.melt(id_vars=[x for x in stations if x not in cols and "voyageurs_non_voyageurs" not in x],
                         value_vars=cols, var_name="variable_source", value_name="voyageurs")
    long["annee"] = long.variable_source.str.extract(r"(20\d{2})$")[0].astype(int)
    long = long.drop(columns="variable_source")
    long["voyageurs"] = pd.to_numeric(long.voyageurs, errors="raise").astype("Int64")
    assert not long.duplicated(["code_uic", "annee"]).any()
    assert long.voyageurs.dropna().ge(0).all()
    long = long.merge(demo[["code_commune", "nom_commune", "code_departement", "code_region", "nom_region"]],
                      on="code_commune", how="left", validate="many_to_one")
    save(long, "gares_annees")
    stations = stations.drop(columns=[x for x in stations if x.startswith("total")])
    save(stations, "gares_referentiel")

    usable = long.dropna(subset=["code_commune"])
    commune_year = usable.groupby(["code_commune", "annee"], as_index=False).agg(
        voyageurs_gares=("voyageurs", lambda x: x.sum(min_count=1)),
        nb_gares_observees=("code_uic", "nunique"), nb_gares_valeurs_valides=("voyageurs", "count"))
    save(commune_year, "communes_annees_rail")
    wide = usable.pivot(index="code_uic", columns="annee", values="voyageurs")
    good = wide.index[wide[2016].gt(0) & wide[2022].notna()]
    balanced = usable.loc[usable.code_uic.isin(good) & usable.annee.isin([2016, 2022])]
    pair = balanced.groupby(["code_commune", "annee"]).voyageurs.sum(min_count=1).unstack()
    pair.columns = [f"voyageurs_cohorte_{x}" for x in pair.columns]
    pair["nb_gares_cohorte_2016_2022"] = balanced.groupby("code_commune").code_uic.nunique()
    communes = demo.merge(pair.reset_index(), on="code_commune", how="left", validate="one_to_one")
    observed = commune_year[commune_year.annee.eq(2024)].drop(columns="annee")
    observed = observed.rename(columns={x: x+"_2024" for x in observed if x != "code_commune"})
    communes = communes.merge(observed, on="code_commune", how="left", validate="one_to_one")
    communes["nb_gares_observees_2024"] = communes.nb_gares_observees_2024.fillna(0).astype(int)
    communes["croissance_rail_2016_2022_pct"] = (communes.voyageurs_cohorte_2022 / communes.voyageurs_cohorte_2016 - 1)*100
    communes["tcam_rail_2016_2022_pct"] = ((communes.voyageurs_cohorte_2022 / communes.voyageurs_cohorte_2016)**(1/6)-1)*100
    communes["ecart_tcam_rail_population_points"] = communes.tcam_rail_2016_2022_pct - communes.tcam_population_2016_2022_pct
    communes["comptages_gares_par_habitant_2022"] = communes.voyageurs_cohorte_2022 / communes.population_2022.where(communes.population_2022.gt(0))
    communes["profil_rail_demographie"] = pd.Series(pd.NA, index=communes.index, dtype="string")
    complete = communes.tcam_rail_2016_2022_pct.notna() & communes.tcam_population_2016_2022_pct.notna()
    for pop_up, rail_up, label in [(True, True, "population ≥0 / rail ≥0"), (True, False, "population ≥0 / rail <0"),
                                    (False, True, "population <0 / rail ≥0"), (False, False, "population <0 / rail <0")]:
        mask = complete & communes.tcam_population_2016_2022_pct.ge(0).eq(pop_up) & communes.tcam_rail_2016_2022_pct.ge(0).eq(rail_up)
        communes.loc[mask, "profil_rail_demographie"] = label
    # Approche d'accessibilité : centre de la commune, distance à vol d'oiseau,
    # gare avec comptage positif en2024. Ne mesure ni accès routier ni desserte.
    continental_codes = set(demo.loc[demo.metropole & ~demo.code_departement.isin(["2A", "2B"]), "code_commune"])
    centres = metro.loc[metro.code_commune.isin(continental_codes), ["code_commune", "geometry"]].copy()
    centres.geometry = centres.geometry.centroid
    active = long[long.annee.eq(2024) & long.voyageurs.gt(0) & long.longitude.notna() & long.latitude.notna()]
    pts = gpd.GeoSeries(gpd.points_from_xy(active.longitude, active.latitude), crs=4326).to_crs(2154)
    tree = cKDTree(np.c_[pts.x, pts.y])
    dist, idx = tree.query(np.c_[centres.geometry.x, centres.geometry.y], k=1)
    centres["distance_centre_gare_km"] = dist / 1000
    centres["gare_proche_uic"] = active.code_uic.to_numpy()[idx]
    centres["longitude_centre"] = centres.to_crs(4326).geometry.x
    centres["latitude_centre"] = centres.to_crs(4326).geometry.y
    communes = communes.merge(centres.drop(columns="geometry"), on="code_commune", how="left", validate="one_to_one")
    communes["champ_distance_france_continentale"] = communes.code_commune.isin(continental_codes)
    for cutoff in (5, 10, 15):
        communes[f"centre_a_plus_de_{cutoff}km"] = communes.distance_centre_gare_km.gt(cutoff).where(communes.distance_centre_gare_km.notna())
    for filename in ["climat_parc_communes_cog2025.parquet"]:
        path = ROOT / "data/processed" / filename
        if path.exists():
            extra = pd.read_parquet(path)
            overlap = [x for x in extra if x in communes and x != "code_commune"]
            communes = communes.merge(extra.drop(columns=overlap), on="code_commune", how="left", validate="one_to_one")
    if "vp_2022" in communes:
        communes["vp_2022_pour_1000_habitants"] = communes.vp_2022 / communes.population_2022.where(communes.population_2022.gt(0))*1000
        communes["vp_particuliers_2022_par_menage"] = communes.vp_particuliers_2022 / communes.menages_2022.where(communes.menages_2022.gt(0))
        # Périmètre SDES décrit comme dernière géographie disponible, sans millésime explicite.
        communes["parc_millesime_geographique_non_precise"] = True
    save(communes, "dataset_final_communes")
    join = {
        "gares_frequentation": int(stations.shape[0]), "annees": sorted(map(int, long.annee.unique())),
        "gare_avec_commune": int(stations.code_commune.notna().sum()),
        "gare_avec_coordonnees": int(stations.longitude.notna().sum()),
        "taux_jointure_commune_pct": float(stations.code_commune.notna().mean()*100),
        "methodes_jointure": stations.methode_jointure_commune.fillna("non résolu").value_counts().to_dict(),
        "voyageurs_2024_couverts_commune_pct": float(usable.loc[usable.annee.eq(2024), "voyageurs"].sum()/long.loc[long.annee.eq(2024), "voyageurs"].sum()*100),
        "communes_insee": int(len(demo)), "communes_analyse_cohorte": int(complete.sum()),
        "gares_cohorte": int(len(good)), "gares_2024_positives_coordonnees": int(len(active)),
        "valeurs_manquantes_frequentation": int(long.voyageurs.isna().sum()),
        "valeurs_nulles_frequentation": int(long.voyageurs.eq(0).sum()),
        "doublons_uic_referentiel": int(len(conflicts)),
    }
    (out / "qualite_jointures.json").write_text(json.dumps(join, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(join, ensure_ascii=False, indent=2))
    return communes, long


if __name__ == "__main__":
    build()
