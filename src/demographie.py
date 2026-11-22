"""Bases communales INSEE, géographie constante du 1er janvier 2025.

Les données proviennent exclusivement des fichiers officiels du RP2022.
Commande : python -m src.demographie [--offline] [--refresh].
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from .collecte import ROOT, fetch

RAW = ROOT / "data/raw/insee"
PROCESSED = ROOT / "data/processed"
SOURCES = {
    "historique": ("8582555", "base-cc-serie-historique-2022_csv.zip"),
    "population": ("8581696", "base-cc-evol-struct-pop-2022_csv.zip"),
    "logement": ("8581474", "base-cc-logement-2022_csv.zip"),
    "emploi": ("8581444", "base-cc-emploi-pop-active-2022_csv.zip"),
    "mobilite": ("8581424", "base-cc-caract_emp-2022_csv.zip"),
}
COG_FILES = ["v_commune_2025.csv", "v_departement_2025.csv",
             "v_region_2025.csv", "v_mvt_commune_2025.csv"]
POPULATION = {1968: "D68_POP", 1975: "D75_POP", 1982: "D82_POP",
              1990: "D90_POP", 1999: "D99_POP", 2006: "P06_POP",
              2011: "P11_POP", 2016: "P16_POP", 2022: "P22_POP"}


def collect(*, offline=False, refresh=False):
    """Archive fichiers et pages, avec vérification des empreintes du cache."""
    RAW.mkdir(parents=True, exist_ok=True)
    old_path = RAW / "manifest_insee.json"
    previous = {x["path"].replace("\\", "/").split("/")[-1]: x
                for x in json.loads(old_path.read_text(encoding="utf-8"))} if old_path.exists() else {}
    records = []
    for key, (page_id, filename) in SOURCES.items():
        page = f"https://www.insee.fr/fr/statistiques/{page_id}"
        fetch(page, RAW / f"{page_id}.html", offline=offline, refresh=refresh)
        url = f"https://www.insee.fr/fr/statistiques/fichier/{page_id}/{filename}"
        path = RAW / filename
        content = fetch(url, path, offline=offline, refresh=refresh)
        digest = hashlib.sha256(content).hexdigest()
        if filename in previous and not refresh:
            assert previous[filename]["sha256"] == digest, f"Cache modifié : {filename}"
        record = previous.get(filename, {}).copy()
        record.update(source_id=page_id, source_family=key, page_url=page,
                      url=url, path=str(path.relative_to(ROOT)),
                      size_bytes=len(content), sha256=digest,
                      geography="COG 2025", license="Licence Ouverte / Open Licence")
        records.append(record)
    page = "https://www.insee.fr/fr/information/8377162"
    fetch(page, RAW / "8377162.html", offline=offline, refresh=refresh)
    for filename in COG_FILES:
        url = f"https://www.insee.fr/fr/statistiques/fichier/8377162/{filename}"
        path = RAW / filename
        content = fetch(url, path, offline=offline, refresh=refresh)
        digest = hashlib.sha256(content).hexdigest()
        if filename in previous and not refresh:
            assert previous[filename]["sha256"] == digest, f"Cache modifié : {filename}"
        records.append(dict(source_id="8377162", source_family="cog2025",
                            page_url=page, url=url, path=str(path.relative_to(ROOT)),
                            size_bytes=len(content), sha256=digest,
                            geography="COG 2025", license="Licence Ouverte / Open Licence"))
    density_name = "fichier_diffusion_2025.xlsx"
    density_url = "https://www.insee.fr/fr/statistiques/fichier/8571524/" + density_name
    fetch("https://www.insee.fr/fr/information/8571524", RAW / "8571524.html", offline=offline, refresh=refresh)
    content = fetch(density_url, RAW / density_name, offline=offline, refresh=refresh)
    records.append(dict(source_id="8571524", source_family="grille_densite2025",
                        page_url="https://www.insee.fr/fr/information/8571524", url=density_url,
                        path=str((RAW / density_name).relative_to(ROOT)), size_bytes=len(content),
                        sha256=hashlib.sha256(content).hexdigest(), geography="COG 2025",
                        license="Licence Ouverte / Open Licence"))
    old_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def read_source(key, columns):
    """Lit uniquement les colonnes nécessaires ; les codes restent en chaîne."""
    filename = SOURCES[key][1]
    with zipfile.ZipFile(RAW / filename) as archive:
        names = [x for x in archive.namelist()
                 if x.lower().endswith(".csv") and not x.lower().startswith("meta")]
        assert len(names) == 1, names
        with archive.open(names[0]) as stream:
            frame = pd.read_csv(stream, sep=";", encoding="utf-8-sig",
                                usecols=["CODGEO"] + columns, dtype={"CODGEO": "string"},
                                na_values=["", "s", "S", "nd", "ND", "N/A", "NaN"])
        # Le dictionnaire officiel brut reste disponible à côté du fichier choisi.
        for member in archive.namelist():
            if member.lower().startswith("meta") and member.lower().endswith(".csv"):
                (RAW / Path(member).name).write_bytes(archive.read(member))
    assert not frame["CODGEO"].duplicated().any(), f"Codes dupliqués dans {key}"
    frame["CODGEO"] = frame["CODGEO"].str.strip()
    for col in columns:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


def safe_ratio(numerator, denominator):
    return numerator.div(denominator.where(denominator > 0))


def build(*, offline=False, refresh=False):
    collect(offline=offline, refresh=refresh)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    cog = pd.read_csv(RAW / "v_commune_2025.csv", dtype="string", keep_default_na=False)
    com = cog[cog.TYPECOM.eq("COM")].copy()
    assert not com.COM.duplicated().any()
    region = pd.read_csv(RAW / "v_region_2025.csv", dtype="string")
    com = com.merge(region[["REG", "LIBELLE"]].rename(columns={"LIBELLE": "nom_region"}),
                    how="left", on="REG", validate="many_to_one")
    com = com[["COM", "LIBELLE", "DEP", "REG", "nom_region"]].rename(columns={
        "COM": "CODGEO", "LIBELLE": "nom_commune", "DEP": "code_departement", "REG": "code_region"})
    historical_cols = list(POPULATION.values()) + ["SUPERF", "NAIS1621", "DECE1621", "NAIS1115", "DECE1115",
                                                  "P11_RP", "P16_RP", "P22_RP"]
    historical = read_source("historique", historical_cols)
    excluded = historical.loc[~historical.CODGEO.isin(com.CODGEO), ["CODGEO"]]
    excluded.to_csv(PROCESSED / "demographie_codes_exclus.csv", index=False)
    # COM : communes entières, arrondissements municipaux exclus pour éviter les doubles comptes.
    frame = historical.merge(com, on="CODGEO", how="inner", validate="one_to_one")
    for year, col in POPULATION.items():
        frame = frame.rename(columns={col: f"population_{year}"})
    frame = frame.rename(columns={"CODGEO": "code_commune", "SUPERF": "superficie_km2",
                                  "NAIS1621": "naissances_2016_2021", "DECE1621": "deces_2016_2021",
                                  "NAIS1115": "naissances_2011_2015", "DECE1115": "deces_2011_2015"})

    # Double lecture : des scissions/révisions peuvent être répercutées différemment.
    # Les écarts sont publiés, jamais effacés par une correction arbitraire.
    pop = read_source("population", ["P22_POP", "P16_POP", "P11_POP"])
    check = frame[["code_commune", "population_2022", "population_2016", "population_2011"]].merge(
        pop, left_on="code_commune", right_on="CODGEO", validate="one_to_one")
    differences = []
    for year in (2022, 2016, 2011):
        delta = check[f"population_{year}"] - check[f"P{str(year)[2:]}_POP"]
        for _, row in check.loc[delta.abs() > 0.5].iterrows():
            differences.append(dict(code_commune=row.code_commune, annee=year,
                                    population_historique=row[f"population_{year}"],
                                    population_autre_base=row[f"P{str(year)[2:]}_POP"]))
        mask = check.loc[delta.abs() > .5, "code_commune"]
        frame[f"alerte_population_inter_sources_{year}"] = frame.code_commune.isin(mask)
    pd.DataFrame(differences, columns=["code_commune", "annee", "population_historique", "population_autre_base"]).to_csv(
        PROCESSED / "demographie_ecarts_inter_sources.csv", index=False)

    logement_cols = [f"P{str(y)[2:]}_{s}" for y in (2011, 2016, 2022)
                     for s in ("MEN", "RP_VOIT1P", "RP_VOIT1", "RP_VOIT2P")]
    logement = read_source("logement", logement_cols).rename(columns={"CODGEO": "code_commune"})
    rename = {}
    for y in (2011, 2016, 2022):
        for raw, clean in {"MEN": "menages", "RP_VOIT1P": "menages_au_moins_une_voiture",
                           "RP_VOIT1": "menages_une_voiture", "RP_VOIT2P": "menages_deux_voitures_ou_plus"}.items():
            rename[f"P{str(y)[2:]}_{raw}"] = f"{clean}_{y}"
    logement = logement.rename(columns=rename)
    frame = frame.merge(logement, on="code_commune", how="left", validate="one_to_one", indicator="jointure_logement")
    for y in (2011, 2016, 2022):
        delta = frame[f"P{str(y)[2:]}_RP"] - frame[f"menages_{y}"]
        frame[f"alerte_menages_inter_sources_{y}"] = delta.abs().gt(.5)
        frame[f"residences_principales_historique_{y}"] = frame.pop(f"P{str(y)[2:]}_RP")

    mobility_cols = [f"P{str(y)[2:]}_ACTOCC15P{s}" for y in (2016, 2022)
                     for s in ("", "_VOITURE", "_COMMUN", "_MARCHE", "_PASTRANS")]
    mobility_cols += ["P22_ACTOCC15P_VELO", "P22_ACTOCC15P_2ROUESMOT", "P16_ACTOCC15P_2ROUES"]
    mobility = read_source("mobilite", mobility_cols).rename(columns={"CODGEO": "code_commune"})
    rename = {}
    for y in (2016, 2022):
        for raw, clean in {"": "actifs_occupes_15p", "_VOITURE": "navetteurs_voiture",
                           "_COMMUN": "navetteurs_transports_commun", "_MARCHE": "navetteurs_marche",
                           "_PASTRANS": "actifs_sans_deplacement"}.items():
            rename[f"P{str(y)[2:]}_ACTOCC15P{raw}"] = f"{clean}_{y}"
    rename.update(P22_ACTOCC15P_VELO="navetteurs_velo_2022",
                  P22_ACTOCC15P_2ROUESMOT="navetteurs_deux_roues_motorises_2022",
                  P16_ACTOCC15P_2ROUES="navetteurs_deux_roues_2016")
    mobility = mobility.rename(columns=rename)
    frame = frame.merge(mobility, on="code_commune", how="left", validate="one_to_one", indicator="jointure_mobilite")
    frame["metropole"] = ~frame.code_departement.str.startswith("97")
    density = pd.read_excel(RAW / "fichier_diffusion_2025.xlsx", sheet_name="Maille communale",
                            header=4, dtype={"CODGEO": "string"})
    density = density[density.CODGEO.str.fullmatch(r"[0-9AB]{5}", na=False)]
    density = density[["CODGEO", "DENS", "LIBDENS", "DENS7", "LIBDENS7", "DENS_AAV", "LIBDENS_AAV"]].rename(columns={
        "CODGEO": "code_commune", "DENS": "classe_densite_3", "LIBDENS": "libelle_densite_3",
        "DENS7": "classe_densite_7", "LIBDENS7": "libelle_densite_7", "DENS_AAV": "classe_densite_aav",
        "LIBDENS_AAV": "libelle_densite_aav"})
    assert not density.code_commune.duplicated().any()
    for col in ("classe_densite_3", "classe_densite_7", "classe_densite_aav"):
        density[col] = pd.to_numeric(density[col], errors="raise").astype("Int64")
    density.to_csv(PROCESSED / "demographie_densite2025.csv", index=False, encoding="utf-8-sig")
    frame = frame.merge(density, how="left", on="code_commune", validate="one_to_one")
    frame["millesime_cog"] = 2025
    frame["densite_population_2022_hab_km2"] = safe_ratio(frame.population_2022, frame.superficie_km2)
    for start, end in ((1999, 2006), (2006, 2011), (2011, 2016), (2016, 2022)):
        ratio = safe_ratio(frame[f"population_{end}"], frame[f"population_{start}"])
        frame[f"tcam_population_{start}_{end}_pct"] = 100 * (ratio.pow(1 / (end - start)) - 1)
    frame["croissance_population_2016_2022_pct"] = 100 * (safe_ratio(frame.population_2022, frame.population_2016) - 1)
    frame["alerte_comparabilite_rail_population"] = (frame.alerte_population_inter_sources_2016 |
                                                         frame.alerte_population_inter_sources_2022)
    frame["variation_population_2016_2022"] = frame.population_2022 - frame.population_2016
    frame["solde_naturel_2016_2022"] = frame.naissances_2016_2021 - frame.deces_2016_2021
    frame["solde_migratoire_apparent_2016_2022"] = frame.variation_population_2016_2022 - frame.solde_naturel_2016_2022
    for y in (2011, 2016, 2022):
        coherent = ~(frame[f"alerte_population_inter_sources_{y}"] | frame[f"alerte_menages_inter_sources_{y}"])
        frame[f"part_menages_motorises_{y}_pct"] = 100 * safe_ratio(
            frame[f"menages_au_moins_une_voiture_{y}"], frame[f"menages_{y}"]).where(coherent)
        # Au moins deux voitures : on peut calculer seulement une borne inférieure du parc.
        frame[f"voitures_par_menage_borne_inferieure_{y}"] = safe_ratio(
            frame[f"menages_une_voiture_{y}"] + 2 * frame[f"menages_deux_voitures_ou_plus_{y}"], frame[f"menages_{y}"]).where(coherent)
    for y in (2016, 2022):
        coherent = ~(frame[f"alerte_population_inter_sources_{y}"] | frame[f"alerte_menages_inter_sources_{y}"])
        frame[f"mobilite_geographie_comparable_{y}"] = coherent & frame.jointure_mobilite.eq("both")
        frame[f"part_modale_voiture_{y}_pct"] = 100 * safe_ratio(frame[f"navetteurs_voiture_{y}"], frame[f"actifs_occupes_15p_{y}"]).where(coherent)
        frame[f"part_modale_transports_commun_{y}_pct"] = 100 * safe_ratio(
            frame[f"navetteurs_transports_commun_{y}"], frame[f"actifs_occupes_15p_{y}"]).where(coherent)
    frame["variation_part_modale_voiture_2016_2022_points"] = frame.part_modale_voiture_2022_pct - frame.part_modale_voiture_2016_pct
    rate = frame.tcam_population_2016_2022_pct
    frame["trajectoire_demographique"] = np.select(
        [rate < -0.2, rate > 0.2, rate.notna()], ["declin", "croissance", "stable"], default="indetermine")
    # Seuil ±0,2 % annuel : choix descriptif annoncé, pas un seuil de significativité.
    checks = validate(frame, excluded, historical)
    frame = frame.sort_values("code_commune").reset_index(drop=True)
    frame.to_parquet(PROCESSED / "demographie_communes.parquet", index=False)
    frame.to_csv(PROCESSED / "demographie_communes.csv", index=False, encoding="utf-8-sig")
    identifiers = ["code_commune", "nom_commune", "code_departement", "code_region", "nom_region", "metropole", "millesime_cog"]
    long = frame[identifiers + [f"population_{y}" for y in POPULATION]].melt(
        id_vars=identifiers, var_name="annee", value_name="population")
    long["annee"] = long.annee.str.replace("population_", "", regex=False).astype(int)
    long.to_parquet(PROCESSED / "demographie_population_long.parquet", index=False)
    long.to_csv(PROCESSED / "demographie_population_long.csv", index=False, encoding="utf-8-sig")
    passage = cog[cog.TYPECOM.ne("COM") & cog.COMPARENT.ne("")][["COM", "COMPARENT", "TYPECOM", "LIBELLE"]].rename(columns={
        "COM": "code_commune_source", "COMPARENT": "code_commune_cog2025", "TYPECOM": "type_commune_source", "LIBELLE": "nom_commune_source"})
    passage = passage.drop_duplicates()
    # Un même code peut désigner à la fois la commune nouvelle et sa commune déléguée.
    # Le code courant COM a priorité ; ces identités n'ont pas à être remappées.
    passage = passage[~passage.code_commune_source.isin(com.CODGEO)]
    assert not passage.code_commune_source.duplicated().any()
    passage.to_csv(PROCESSED / "demographie_passage_cog2025.csv", index=False)
    quality_path = ROOT / "outputs/tables/controle_demographie.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
    return frame


def validate(frame, excluded, raw):
    assert frame.code_commune.str.fullmatch(r"[0-9AB]{5}").all()
    assert not frame.code_commune.duplicated().any()
    assert (frame.filter(regex=r"^population_\d{4}$").dropna() >= 0).all().all()
    for col in frame.filter(regex=r"^part_.*_pct$"):
        values = frame[col].dropna()
        assert values.between(-1e-7, 100 + 1e-7).all(), col
    for y in (2011, 2016, 2022):
        one_plus = frame[f"menages_au_moins_une_voiture_{y}"]
        parts = frame[f"menages_une_voiture_{y}"] + frame[f"menages_deux_voitures_ou_plus_{y}"]
        assert (one_plus - parts).abs().dropna().max() < 1e-4
        assert ((one_plus - frame[f"menages_{y}"]).dropna() < 1e-4).all()
    modal_errors = {}
    for y in (2016, 2022):
        cols = [f"navetteurs_voiture_{y}", f"navetteurs_transports_commun_{y}",
                f"navetteurs_marche_{y}", f"actifs_sans_deplacement_{y}"]
        cols += (["navetteurs_velo_2022", "navetteurs_deux_roues_motorises_2022"]
                 if y == 2022 else ["navetteurs_deux_roues_2016"])
        diff = frame[cols].sum(axis=1, min_count=len(cols)) - frame[f"actifs_occupes_15p_{y}"]
        # Tolérance numérique, aucun arrondi avant les agrégations.
        assert diff.abs().max() < 1e-4
        modal_errors[str(y)] = float(diff.abs().max())
    national = float(frame.population_2022.sum())
    metro = float(frame.loc[frame.metropole, "population_2022"].sum())
    # Référence publiée : fiche nationale INSEE RP2022, même géographie2025.
    assert abs(national - 67_760_573) < 1, national
    assert abs(metro - 65_846_255) < 1, metro
    return dict(communes=int(len(frame)), communes_metropole=int(frame.metropole.sum()),
                lignes_source=int(len(raw)), codes_arrondissements_exclus=excluded.CODGEO.tolist(),
                population_2022_france_hors_mayotte=national, population_2022_metropole=metro,
                reference_population_url="https://www.insee.fr/fr/statistiques/8581709?geo=METRO-1",
                logements_jointure_ok=int(frame.jointure_logement.eq("both").sum()),
                mobilite_jointure_ok=int(frame.jointure_mobilite.eq("both").sum()),
                ecart_somme_modes_max=modal_errors,
                alertes_inter_sources={c: int(frame[c].sum()) for c in frame if c.startswith("alerte_")},
                manquants={c: int(frame[c].isna().sum()) for c in frame if frame[c].isna().any()},
                periode_comparaison_principale="2016–2022", geography="COG 2025")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    build(offline=args.offline, refresh=args.refresh)
