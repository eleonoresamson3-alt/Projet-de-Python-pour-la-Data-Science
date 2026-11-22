"""Collecte officielle SDES/ADEME et indicateurs climat, sans donnees simulees.

Usage: python -m src.climat [--download] [--refresh]
Le traitement hors ligne est le comportement par defaut.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/climat"
PROCESSED = ROOT / "data/processed"
OUTPUT = ROOT / "outputs/climat"
SDES_BASE = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/1582861b-e042-4490-9161-6429d8229703"
SDES_MILLESIME = "2026-06"
YEARS = (2016, 2019, 2022, 2023, 2024)
MODES = (2, 3, 4, 5, 14, 15)


def fetch(url: str, name: str, *, refresh: bool = False, compress: bool = False) -> Path:
    """Archive une reponse publique, avec URL, date, statut HTTP et SHA-256."""
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / name
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if path.exists() and name in manifest and not refresh:
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if current_hash != manifest[name]["sha256_file"]:
            raise ValueError(f"Archive modifiee: {path}")
        return path
    request = urllib.request.Request(url, headers={"User-Agent": "Projet-statistique-rail-demographie/1.0", "Accept-Encoding": "identity"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                temp = path.with_suffix(path.suffix + ".part")
                digest = hashlib.sha256()
                uncompressed_bytes = 0
                with (gzip.open(temp, "wb") if compress else temp.open("wb")) as stream:
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk)
                        digest.update(chunk)
                        uncompressed_bytes += len(chunk)
                record = {"url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "http_status": response.status,
                          "last_modified": response.headers.get("Last-Modified"), "content_type": response.headers.get("Content-Type"),
                          "source_bytes": uncompressed_bytes, "sha256_source": digest.hexdigest()}
                temp.replace(path)
                record["sha256_file"] = hashlib.sha256(path.read_bytes()).hexdigest()
                manifest[name] = record
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                return path
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 3:
                raise
            print(f"Nouvelle tentative {attempt + 1}: {exc}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Collecte incomplete")


def collect(refresh: bool = False) -> None:
    """Extrait uniquement les VP; l'absence de filtre utilisateur conserve les professionnels."""
    fetch("https://www.data.gouv.fr/api/1/datasets/parc-de-vehicules-routiers/", "catalogue_sdes.json", refresh=refresh)
    fetch(SDES_BASE + "?millesime=" + SDES_MILLESIME, "sdes_metadata.json", refresh=refresh)
    params = {"millesime": SDES_MILLESIME, "GROUPE": "eq:VP"}
    fetch(SDES_BASE + "/count?" + urllib.parse.urlencode(params), "sdes_vp_count.json", refresh=refresh)
    params.update({"columns": ",".join(["COMMUNE_CODE", "COMMUNE_NOM", "CARBURANT", "CRIT_AIR", "STATUT_UTILISATEUR", "GROUPE", "CATEGORIE"] + [f"PARC_{y}" for y in YEARS]),
                   "withColumnName": "true", "withColumnDescription": "false", "withColumnUnit": "false"})
    fetch(SDES_BASE + "/csv?" + urllib.parse.urlencode(params), "sdes_vp_communes_2026-06.csv.gz", refresh=refresh, compress=True)
    fetch("https://data.statistiques.developpement-durable.gouv.fr/dido/api/files/6e8c4d0d-95df-4cc0-9559-54562d4ae48f", "sdes_methodologie.pdf", refresh=refresh)
    fetch("https://impactco2.fr/api/v1/transport?" + urllib.parse.urlencode({"km": 1, "transports": ",".join(map(str, MODES)), "displayAll": 1, "includeConstruction": 1, "occupencyRate": 1}),
          "ademe_impactco2_transport_1km.json", refresh=refresh)
    fetch("https://raw.githubusercontent.com/datagir/impactco2/3106130d308c2cf5605d409779b7b22b32221258/app/api/v1/transport/route.ts", "impactco2_route.ts", refresh=refresh)
    fetch("https://raw.githubusercontent.com/datagir/impactco2/3106130d308c2cf5605d409779b7b22b32221258/src/data/categories/deplacement.ts", "impactco2_deplacement.ts", refresh=refresh)
    fetch("https://www.sncf-voyageurs.com/medias-publics/2025-10/sncf-voyageurs-rse-transitions-comparateur-co2.pdf", "sncf_comparateur_2025-10.pdf", refresh=refresh)
    for scenario in ("central", "population_basse", "population_haute"):
        fetch(f"https://www.insee.fr/fr/statistiques/fichier/6652134/projections_scenario_{scenario}.xlsx", f"insee_omphale_{scenario}.xlsx", refresh=refresh)
    for scenario in ("Central", "Pop_basse", "Pop_haute"):
        fetch(f"https://www.insee.fr/fr/statistiques/fichier/7747107/donnees_det_{scenario}.xlsx", f"insee_omphale_detail_{scenario}.xlsx", refresh=refresh)
    fetch("https://www.insee.fr/fr/statistiques/7747107", "insee_omphale_detail_page.html", refresh=refresh)


def process_parc() -> dict:
    import pandas as pd

    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = RAW / "sdes_vp_communes_2026-06.csv.gz"
    frame = pd.read_csv(source, sep=";", dtype={"COMMUNE_CODE": "string"}, decimal=",")
    if "COMMUNE_CODE" not in frame:
        frame = pd.read_csv(source, sep=",", dtype={"COMMUNE_CODE": "string"})
    expected_json = json.loads((RAW / "sdes_vp_count.json").read_text(encoding="utf-8"))
    expected = expected_json.get("count", expected_json.get("total")) if isinstance(expected_json, dict) else expected_json
    if isinstance(expected, dict):
        expected = expected.get("count", expected.get("total"))
    if expected is not None and len(frame) != int(expected):
        raise ValueError(f"Extraction SDES tronquee: {len(frame)} != {expected}")
    assert frame["GROUPE"].eq("VP").all(), "Filtre VP non respecte"
    grain = ["COMMUNE_CODE", "CARBURANT", "CRIT_AIR", "STATUT_UTILISATEUR", "GROUPE", "CATEGORIE"]
    assert not frame.duplicated(grain).any(), "Doublons au grain source SDES"
    cols = [f"PARC_{y}" for y in YEARS]
    for col in cols:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
        assert frame[col].notna().all() and frame[col].ge(0).all()
    # Les codes dep000 ne sont pas des communes et restent dans une annexe distincte.
    unknown = (frame["COMMUNE_CODE"].str.endswith("000")
               | frame["COMMUNE_CODE"].str.match(r"^97[1-6]00$", na=False)
               | ~frame["COMMUNE_CODE"].str.match(r"^(?:[0-9]{5}|2[AB][0-9]{3})$", na=False))
    totals = frame.groupby("COMMUNE_CODE")[cols].sum(min_count=1).rename(columns={f"PARC_{y}": f"vp_{y}" for y in YEARS})
    private = frame.loc[frame["STATUT_UTILISATEUR"].eq("Particulier")].groupby("COMMUNE_CODE")[cols].sum(min_count=1).rename(columns={f"PARC_{y}": f"vp_particuliers_{y}" for y in YEARS})
    electric = frame.loc[frame["CARBURANT"].eq("Electrique")].groupby("COMMUNE_CODE")[cols].sum(min_count=1).rename(columns={f"PARC_{y}": f"vp_electriques_{y}" for y in YEARS})
    combined = totals.join(private, validate="one_to_one").join(electric, validate="one_to_one").reset_index().rename(columns={"COMMUNE_CODE": "code_commune"})
    combined["code_fictif_ou_invalide"] = combined["code_commune"].isin(frame.loc[unknown, "COMMUNE_CODE"])
    combined["millesime_source_sdes"] = SDES_MILLESIME
    combined["vp_croissance_2016_2022_pct"] = (combined["vp_2022"] / combined["vp_2016"].where(combined["vp_2016"].gt(0)) - 1) * 100
    fictive = combined.loc[combined["code_fictif_ou_invalide"]].copy()
    communes = combined.loc[~combined["code_fictif_ou_invalide"]].copy()
    for name, table in [("climat_parc_communes", communes), ("climat_parc_codes_fictifs", fictive)]:
        table.to_csv(PROCESSED / f"{name}.csv", index=False, encoding="utf-8")
        table.to_parquet(PROCESSED / f"{name}.parquet", index=False)
    for y in YEARS:
        assert abs(combined[f"vp_{y}"].sum() - frame[f"PARC_{y}"].sum()) < 1e-5
    national = pd.DataFrame({"annee_stock_1_janvier": YEARS,
                             "vp_tous_codes": [float(combined[f"vp_{y}"].sum()) for y in YEARS],
                             "vp_communes_identifiees": [float(communes[f"vp_{y}"].sum()) for y in YEARS],
                             "vp_codes_fictifs": [float(fictive[f"vp_{y}"].sum()) for y in YEARS]})
    national.to_csv(OUTPUT / "parc_national.csv", index=False)
    quality = {"source_rows": len(frame), "expected_rows_api_count": expected, "communes": len(communes), "codes_fictifs_ou_invalides": len(fictive),
               "carburants": sorted(frame["CARBURANT"].dropna().unique().tolist()), "source_years": list(YEARS),
               "geographie_sdes": "Notice: COG de la derniere annee disponible. Edition2026-06, annee COG exacte non explicitee; jointure par code et rejets controles.",
               "years_definitive_vp": "2011-2023; 2024 provisoire dans edition 2026-06", "no_imputation": True}
    (OUTPUT / "qualite_parc.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    return quality


def process_factors() -> dict:
    import pandas as pd

    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RAW / "ademe_impactco2_transport_1km.json").read_text(encoding="utf-8"))
    table = pd.DataFrame(payload["data"]).rename(columns={"id": "id_mode_ademe", "name": "mode", "value": "kgco2e_par_voyageur_km"})
    assert set(table["id_mode_ademe"]) == set(MODES)
    assert table["kgco2e_par_voyageur_km"].gt(0).all()
    table["gco2e_par_voyageur_km"] = table["kgco2e_par_voyageur_km"] * 1000
    table["perimetre"] = "API Impact CO2 includeConstruction=1; taux voiture=1 occupant; parametres archives"
    table["date_collecte"] = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))["ademe_impactco2_transport_1km.json"]["retrieved_at_utc"]
    table.to_csv(PROCESSED / "climat_facteurs_ademe.csv", index=False, encoding="utf-8")
    table.to_parquet(PROCESSED / "climat_facteurs_ademe.parquet", index=False)
    # Scenarios de comparaison unitaire, jamais un bilan d'emissions evitees observe.
    rates = table.set_index("id_mode_ademe")["kgco2e_par_voyageur_km"]
    scenarios = []
    for distance in (20, 100, 500):
        for occupancy in (1, 1.6, 2):
            for rail_id in (2, 3, 14, 15):
                scenarios.append({"distance_scenario_km": distance, "occupants_voiture_thermique": occupancy,
                                  "mode_train": table.set_index("id_mode_ademe").loc[rail_id, "mode"],
                                  "co2e_voiture_par_personne_kg": float(distance * rates[4] / occupancy),
                                  "co2e_train_par_personne_kg": float(distance * rates[rail_id]),
                                  "ecart_unitaire_scenario_kgco2e": float(distance * (rates[4] / occupancy - rates[rail_id])),
                                  "statut": "Scenario a distance egale; aucun report modal ni emission evitee observe"})
    pd.DataFrame(scenarios).to_csv(OUTPUT / "comparaison_unitaire_scenarios.csv", index=False, encoding="utf-8")
    return {"modes": len(table), "perimetre": table["perimetre"].iloc[0], "warning_api": payload.get("warning")}


def harmonize_parc_cog2025() -> dict:
    """Regroupe les codes officiels relies au COG2025; isole tout code non resolu.

    La geographie exacte SDES n'etant pas explicitee, cette operation ne garantit
    pas une reconstitution de toutes les limites de2025. Elle n'invente aucun
    coefficient de ventilation pour une eventuelle fusion posterieure.
    """
    import pandas as pd

    source = pd.read_parquet(PROCESSED / "climat_parc_communes.parquet")
    reference = pd.read_csv(PROCESSED / "demographie_communes.csv", usecols=["code_commune", "nom_commune", "population_2022"], dtype={"code_commune": "string"})
    valid = set(reference["code_commune"])
    official = pd.read_csv(ROOT / "data/raw/insee/v_commune_2025.csv", dtype="string")
    official_codes = set(official.loc[official["TYPECOM"].eq("COM"), "COM"])
    crosswalk = pd.read_csv(PROCESSED / "demographie_passage_cog2025.csv", dtype="string")
    assert not crosswalk["code_commune_source"].duplicated().any()
    crosswalk = crosswalk.set_index("code_commune_source")
    mapping = crosswalk["code_commune_cog2025"].to_dict()
    types = crosswalk["type_commune_source"].to_dict()
    audit = pd.DataFrame({"code_commune_source": source["code_commune"]})
    audit["code_commune_cog2025_officiel"] = audit["code_commune_source"].map(lambda x: x if x in official_codes else mapping.get(x))
    audit["code_commune_cible_cog2025"] = audit["code_commune_cog2025_officiel"]
    # Une cible doit elle-meme appartenir a l'univers effectivement analyse.
    invalid_target = ~audit["code_commune_cible_cog2025"].isin(valid)
    audit.loc[invalid_target, "code_commune_cible_cog2025"] = pd.NA
    audit["type_code_source"] = audit["code_commune_source"].map(types).fillna("COM_ou_non_resolu")
    audit["statut_passage"] = "identique"
    audit.loc[audit["code_commune_cible_cog2025"].notna() & audit["code_commune_cible_cog2025"].ne(audit["code_commune_source"]), "statut_passage"] = "rattachement_officiel"
    audit.loc[audit["code_commune_cible_cog2025"].isna(), "statut_passage"] = "non_resolu_exclu_jointure"
    outside = audit["code_commune_cog2025_officiel"].isin(official_codes) & audit["code_commune_cible_cog2025"].isna()
    audit.loc[outside, "statut_passage"] = "code_officiel_hors_univers_recensement"
    quantities = [f"{prefix}_{year}" for prefix in ("vp", "vp_particuliers", "vp_electriques") for year in YEARS]
    audit = audit.merge(source.rename(columns={"code_commune": "code_commune_source"})[["code_commune_source"] + quantities], on="code_commune_source", validate="one_to_one")
    audit.to_csv(OUTPUT / "audit_passage_sdes_cog2025.csv", index=False, encoding="utf-8")
    unresolved = audit.loc[audit["code_commune_cible_cog2025"].isna()].copy()
    unresolved.to_csv(OUTPUT / "parc_codes_non_resolus_cog2025.csv", index=False, encoding="utf-8")
    matched = audit.loc[audit["code_commune_cible_cog2025"].notna()].copy()
    grouped = matched.groupby("code_commune_cible_cog2025")[quantities].sum(min_count=1)
    counts = matched.groupby("code_commune_cible_cog2025").agg(nb_codes_source_agreges=("code_commune_source", "size"))
    for typ, col in (("ARM", "nb_arrondissements_source"), ("COMD", "nb_communes_deleguees_source"), ("COMA", "nb_communes_associees_source")):
        counts[col] = matched.loc[matched["type_code_source"].eq(typ)].groupby("code_commune_cible_cog2025").size().reindex(counts.index, fill_value=0)
    grouped = grouped.join(counts, validate="one_to_one").reset_index().rename(columns={"code_commune_cible_cog2025": "code_commune"})
    grouped["millesime_source_sdes"] = SDES_MILLESIME
    grouped["cog_cible"] = 2025
    grouped["cog_exact_source_sdes_non_precise"] = True
    grouped["vp_croissance_2016_2022_pct"] = (grouped["vp_2022"] / grouped["vp_2016"].where(grouped["vp_2016"].gt(0)) - 1) * 100
    assert not grouped["code_commune"].duplicated().any()
    for col in quantities:
        assert abs(grouped[col].sum() + unresolved[col].sum() - source[col].sum()) < 1e-5, col
    # Le parent contient des vehicules distincts des arrondissements. Les sommer
    # preserve le total source au lieu de prendre le faible residu parent seul.
    city_audit = audit.loc[audit["code_commune_cible_cog2025"].isin(["75056", "69123", "13055"])].copy()
    city_audit.to_csv(OUTPUT / "audit_parc_paris_lyon_marseille.csv", index=False, encoding="utf-8")
    for city in ("75056", "69123", "13055"):
        for year in YEARS:
            actual = grouped.loc[grouped["code_commune"].eq(city), f"vp_{year}"].iloc[0]
            expected = city_audit.loc[city_audit["code_commune_cible_cog2025"].eq(city), f"vp_{year}"].sum()
            assert actual == expected
    grouped.to_csv(PROCESSED / "climat_parc_communes_cog2025.csv", index=False, encoding="utf-8")
    grouped.to_parquet(PROCESSED / "climat_parc_communes_cog2025.parquet", index=False)
    no_stock = reference.loc[~reference["code_commune"].isin(grouped["code_commune"])].copy()
    no_stock["statut"] = "Absence de ligne SDES; aucune imputation"
    no_stock.to_csv(OUTPUT / "audit_communes_rp_sans_parc_sdes.csv", index=False, encoding="utf-8")
    quality = {"codes_source_hors_fictifs": len(source), "codes_cibles_cog2025": len(grouped),
               "codes_univers_recensement": len(reference), "communes_rp_sans_ligne_sdes": len(no_stock),
               "population_2022_communes_sans_sdes": float(no_stock["population_2022"].sum()),
               "codes_rattaches": int(audit["statut_passage"].eq("rattachement_officiel").sum()),
               "codes_non_resolus_geographiquement": int(audit["statut_passage"].eq("non_resolu_exclu_jointure").sum()),
               "codes_officiels_hors_univers_recensement": int(audit["statut_passage"].eq("code_officiel_hors_univers_recensement").sum()),
               "vp_2022_exclus_jointure": float(unresolved["vp_2022"].sum()), "vp_2022_resolus": float(grouped["vp_2022"].sum()),
               "somme_conservee_chaque_annee_chaque_sous_parc": True,
               "limite": "Rattachements officiels COG2025 verifies; millesime geographique SDES exact non precise; aucune ventilation des codes non resolus."}
    (OUTPUT / "qualite_passage_cog2025.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    return quality


def process_projections() -> dict:
    """Agrege les projections INSEE detaillees, sans les traiter comme observations."""
    import pandas as pd
    import re
    import unicodedata

    def key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower())

    # Table de codes departement issue du classeur officiel agrege 2022.
    codes = pd.read_excel(RAW / "insee_omphale_central.xlsx", sheet_name="Population_DEP", header=5, dtype={"DEP": "string"})
    assert codes["DEP"].nunique() == 101
    code_map = {key(r.LIBDEP): r.DEP for r in codes.itertuples()}
    # Deux graphies officielles differentes dans les deux publications.
    if "lareunion" in code_map:
        code_map["reunion"] = code_map["lareunion"]
    if "territoiredebelfort" in code_map:
        code_map["territoirebelfort"] = code_map["territoiredebelfort"]
    results = []
    for suffix, scenario in (("Central", "central"), ("Pop_basse", "population_basse"), ("Pop_haute", "population_haute")):
        source = pd.read_excel(RAW / f"insee_omphale_detail_{suffix}.xlsx", sheet_name="Population", header=5)
        assert len(source) == 4040 and not source.duplicated(["ZONE", "SEXE", "TRAGE"]).any()
        assert source.groupby("ZONE").size().eq(40).all()
        years = [f"POP_{y}" for y in range(2018, 2071)]
        total = source.groupby("ZONE")[years].sum(min_count=40).reset_index()
        total["code_departement"] = total["ZONE"].map(lambda x: code_map.get(key(x)))
        if total["code_departement"].isna().any():
            raise ValueError(f"Departements Omphale sans code: {total.loc[total['code_departement'].isna(), 'ZONE'].tolist()}")
        total = total.rename(columns={"ZONE": "nom_departement", **{f"POP_{y}": f"population_projetee_{y}" for y in range(2018, 2071)}})
        total["scenario_insee"] = scenario
        total["croissance_projetee_2018_2050_pct"] = (total["population_projetee_2050"] / total["population_projetee_2018"] - 1) * 100
        total["statut_donnee"] = "Projection officielle INSEE Omphale2022; base2018; publication2024; pas une prevision"
        total["precision_source"] = "Cellules sexe-age arrondies a10; interpretation recommandee au millier"
        results.append(total)
    combined = pd.concat(results, ignore_index=True)
    assert len(combined) == 303 and not combined.duplicated(["code_departement", "scenario_insee"]).any()
    combined.to_csv(PROCESSED / "climat_projections_departements.csv", index=False, encoding="utf-8")
    combined.to_parquet(PROCESSED / "climat_projections_departements.parquet", index=False)
    central = combined.loc[combined["scenario_insee"].eq("central"), ["code_departement", "nom_departement", "population_projetee_2018", "population_projetee_2050", "croissance_projetee_2018_2050_pct"]]
    central.to_csv(OUTPUT / "projections_2050_central.csv", index=False, encoding="utf-8")
    return {"departements": 101, "scenarios": 3, "periode": "2018-2070", "projection_non_observation": True}


def make_figures() -> None:
    """Figures autonomes: comparaisons de facteurs et scenarios officiels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
    factors = pd.read_csv(PROCESSED / "climat_facteurs_ademe.csv").sort_values("gco2e_par_voyageur_km")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    colors = ["#287c8e" if "Voiture" not in x else "#c66b40" for x in factors["mode"]]
    bars = ax.barh(factors["mode"], factors["gco2e_par_voyageur_km"], color=colors)
    ax.bar_label(bars, fmt="%.1f", padding=5)
    ax.set_xlim(0, factors["gco2e_par_voyageur_km"].max() * 1.2)
    ax.set_xlabel("g CO₂e par voyageur.km")
    ax.set_title("Les facteurs ADEME distinguent fortement les modes", loc="left", fontweight="bold", pad=15)
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    fig.text(.02, .02, "Source : ADEME Impact CO₂, extraction du 26/10/2026. Construction incluse ; voiture : 1 occupant.\nFacteurs moyens de référence, sans reconstitution historique ni émissions évitées observées.", fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(OUTPUT / f"facteurs_ademe.{ext}", bbox_inches="tight")
    plt.close(fig)

    stock = pd.read_csv(OUTPUT / "parc_national.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(stock["annee_stock_1_janvier"], stock["vp_tous_codes"] / 1e6, marker="o", color="#287c8e")
    ax.set(xlabel="Stock au 1er janvier", ylabel="Millions de voitures particulières", title="Le parc SDES est un stock de véhicules, pas un flux d’émissions")
    ax.grid(alpha=.2)
    fig.text(.02, .02, "Source : SDES, édition 2026-06, ensemble des codes y compris non localisés.\nPoints 2016, 2019, 2022, 2023, 2024 ; données 2024 révisables, arrondis de diffusion.", fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(OUTPUT / f"parc_national.{ext}", bbox_inches="tight")
    plt.close(fig)

    projections = pd.read_csv(PROCESSED / "climat_projections_departements.csv", dtype={"code_departement": str})
    metropolitan = projections.loc[~projections["code_departement"].str.startswith("97")]
    central = metropolitan.loc[metropolitan["scenario_insee"].eq("central")].sort_values("croissance_projetee_2018_2050_pct")
    selected_codes = pd.concat([central.head(6), central.tail(6)])["code_departement"]
    selected = metropolitan.loc[metropolitan["code_departement"].isin(selected_codes)]
    pivot = selected.pivot(index=["code_departement", "nom_departement"], columns="scenario_insee", values="croissance_projetee_2018_2050_pct").sort_values("central")
    fig, ax = plt.subplots(figsize=(9, 6))
    positions = np.arange(len(pivot))
    ax.hlines(positions, pivot["population_basse"], pivot["population_haute"], color="#aab7bf", linewidth=3, label="Scénarios bas à haut")
    ax.scatter(pivot["central"], positions, color="#287c8e", zorder=3, label="Scénario central")
    ax.set_yticks(positions, pivot.index.get_level_values("nom_departement"))
    ax.axvline(0, color="grey", linewidth=.8)
    ax.set_xlabel("Évolution projetée de population entre 2018 et 2050 (%)")
    ax.set_title("Les trajectoires Omphale à 2050 varient selon les départements", loc="left", fontweight="bold")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=.2)
    fig.text(.02, .02, "Source : INSEE Omphale 2022, tableaux détaillés publiés en 2024.\nSix plus fortes hausses et six plus fortes baisses centrales de métropole. Scénarios, pas intervalles de confiance.\nBase démographique 2018 ; aucune prévision de trafic ferroviaire n’est déduite de ces projections.", fontsize=8)
    fig.tight_layout(rect=(0, .11, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(OUTPUT / f"projections_2050.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.download:
        collect(refresh=args.refresh)
    results = {"parc": process_parc(), "facteurs": process_factors(), "projections": process_projections()}
    if (PROCESSED / "demographie_communes.csv").exists() and (PROCESSED / "demographie_passage_cog2025.csv").exists():
        results["passage_cog2025"] = harmonize_parc_cog2025()
    else:
        results["passage_cog2025"] = "Non execute: lancer src.demographie au prealable puis relancer src.climat."
    print(json.dumps(results, ensure_ascii=False, indent=2))
    make_figures()


if __name__ == "__main__":
    main()
