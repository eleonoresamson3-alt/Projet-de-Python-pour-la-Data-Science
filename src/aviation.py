"""Collecte et analyse descriptive du volet aérien (données DGAC, sans simulation).

Exécution : python -m src.aviation --offline
Renouvellement explicite : python -m src.aviation --refresh
Les résultats principaux s'arrêtent en 2024 ; 2025 sert de contrôle externe.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request
import zipfile

TRAFFIC_API = "https://www.data.gouv.fr/api/1/datasets/64808a5811da153f1439914c/"
CO2_API = "https://www.data.gouv.fr/api/1/datasets/691dcc1b4a50a5b0a65889c8/"
AIRPORT_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
BULLETIN_URL = "https://www.ecologie.gouv.fr/sites/default/files/documents/Bulletin_Statistiques_transport_aerien_2025.pdf"
CLIENT_DATE = "2026-10-26"


def collect(root: Path, refresh: bool = False) -> None:
    """Télécharge les instantanés bruts. Aucun écrasement sans refresh explicite."""
    raw = root / "data/raw/aviation"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = raw / "manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    previous_hashes = {x["file"]: x["sha256"] for x in previous.get("files", [])}
    records = []

    def download(url: str, filename: str) -> bytes:
        target = raw / filename
        if refresh or not target.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "ProjetStatRail/1.0 (research open data)"})
            with urllib.request.urlopen(req, timeout=120) as response:
                blob = response.read()
            target.write_bytes(blob)
        blob = target.read_bytes()
        relative = target.relative_to(root).as_posix()
        digest = hashlib.sha256(blob).hexdigest()
        if not refresh and relative in previous_hashes:
            assert digest == previous_hashes[relative], f"Archive brute modifiée : {relative}"
        records.append({"file": target.relative_to(root).as_posix(), "url": url,
                        "bytes": len(blob), "sha256": digest,
                        "local_file_mtime_utc": datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()})
        return blob

    for api, filename, series in [(TRAFFIC_API, "dgac_metadata.json", ["PAP", "LSN", "APT"]),
                                  (CO2_API, "co2_metadata.json", None)]:
        metadata = json.loads(download(api, filename))
        for resource in metadata["resources"]:
            if series is None or any(s in resource["title"] for s in series):
                download(resource["url"], resource["title"].replace("/", "_"))
    download(AIRPORT_URL, "ourairports.csv")
    download(BULLETIN_URL, "Bulletin_Statistiques_transport_aerien_2025.pdf")
    manifest = {"client_date": CLIENT_DATE, "manifest_built_utc": datetime.now(timezone.utc).isoformat(),
                "licence_dgac": "Licence Ouverte 2.0", "ourairports": "public domain (OurAirports data page)",
                "files": records}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_table(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    df.to_parquet(path.with_suffix(".parquet"), index=False)


def _read_archive(raw: Path, series: str):
    import pandas as pd
    # Le catalogue archivé désigne la ressource active. Les anciens ZIP peuvent
    # rester présents après un renouvellement annuel sans rendre le choix ambigu.
    metadata = json.loads((raw / "dgac_metadata.json").read_text(encoding="utf-8"))
    resources = [r for r in metadata["resources"]
                 if r["title"].startswith(f"ASP_{series}_") and r["title"].lower().endswith(".zip")]
    if len(resources) != 1:
        raise ValueError(f"Une ressource ZIP active {series} attendue dans le catalogue, trouvé : {resources}")
    candidate = raw / resources[0]["title"].replace("/", "_")
    if not candidate.exists():
        raise FileNotFoundError(f"Archive active absente : {candidate}")
    frames = []
    with zipfile.ZipFile(candidate) as archive:
        for name in archive.namelist():
            if name.lower().endswith(".csv"):
                frame = pd.read_csv(io.BytesIO(archive.read(name)), sep=";", encoding="utf-8-sig", dtype=str)
                frame["source_member"] = name
                frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df["annee"] = df["ANMOIS"].str[:4].astype(int)
    df["mois"] = df["ANMOIS"].str[4:6].astype(int)
    df = df[df["annee"].between(2015, 2025)].copy()
    assert df["mois"].between(1, 12).all()
    return df


def _numeric(df, columns):
    import pandas as pd
    for name in columns:
        # errors='raise' : une chaîne non documentée n'est jamais changée silencieusement en NA.
        df[name] = pd.to_numeric(df[name].str.replace(",", ".", regex=False), errors="raise")
        if df[name].notna().any():
            assert df[name].dropna().ge(0).all(), f"Valeur négative : {name}"
    return df


def run(root: Path | str | None = None, offline: bool = True, refresh: bool = False) -> dict:
    import pandas as pd
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw = root / "data/raw/aviation"
    output = root / "outputs/aviation"
    output.mkdir(parents=True, exist_ok=True)
    if not offline or refresh:
        collect(root, refresh=refresh)
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = root / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], f"Archive brute modifiée : {path}"

    lsn = _read_archive(raw, "LSN")
    lsn = _numeric(lsn, ["LSN_PAX", "LSN_DRT"])
    key = ["ANMOIS", "LSN_SEG", "LSN_FSC", "LSN_1", "LSN_2"]
    assert not lsn.duplicated(key).any(), "Doublons LSN : archive non compatible"
    domestic = lsn[lsn["LSN_FSC"].isin(["MET_RAD", "MET_TRA"])].copy()
    assert domestic.groupby(["annee", "LSN_FSC"])["mois"].nunique().eq(12).all()
    annual = domestic.groupby(["annee", "LSN_FSC"], as_index=False).agg(
        passagers=("LSN_PAX", "sum"), dessertes=("LSN_DRT", "sum"), mois_observes=("mois", "nunique"))
    total = annual.groupby("annee", as_index=False).agg(
        passagers=("passagers", "sum"), dessertes=("dessertes", "sum"))
    total["LSN_FSC"] = "MET_INTERIEUR"
    total["mois_observes"] = 12
    annual = pd.concat([annual, total], ignore_index=True).sort_values(["LSN_FSC", "annee"])
    annual = annual.merge(annual[annual["annee"].eq(2019)][["LSN_FSC", "passagers"]].rename(
        columns={"passagers": "passagers_2019"}), on="LSN_FSC", validate="many_to_one")
    annual["indice_2019_100"] = 100 * annual["passagers"] / annual["passagers_2019"]
    _write_table(annual[annual["annee"].le(2024)], root / "data/processed/aviation_trafic_annuel")
    _write_table(domestic[domestic["annee"].le(2024)], root / "data/processed/aviation_trafic_mensuel")

    pap = _read_archive(raw, "PAP")
    # La notice 2026 emploie *_LOC ; l'archive réelle conserve les anciens noms.
    for old, new in [("PAP_PAX_LOC", "PAP_PAX"), ("PAP_PEQ_LOC", "PAP_PEQ"), ("PAP_FRP_LOC", "PAP_FRP")]:
        if old in pap and new not in pap:
            pap = pap.rename(columns={old: new})
    pap = _numeric(pap, ["PAP_DIST", "PAP_PAX", "PAP_PEQ", "PAP_DRT"])
    assert not pap.duplicated(["ANMOIS", "PAP"]).any()
    pap[["aeroport_1", "aeroport_2"]] = pap["PAP"].str.split("_", expand=True)

    airports = pd.read_csv(raw / "ourairports.csv", dtype={"ident": str, "icao_code": str, "iata_code": str},
                           keep_default_na=False)
    # Jointure sur ident, qui coïncide avec l'OACI pour les aéroports DGAC ; jamais sur le nom.
    airports = airports[["ident", "name", "iso_country", "latitude_deg", "longitude_deg", "iata_code", "type"]]
    assert airports["ident"].is_unique
    airports = airports.rename(columns={"ident": "icao"})
    for side in [1, 2]:
        a = airports.rename(columns={c: f"{c}_{side}" for c in airports.columns})
        pap = pap.merge(a, left_on=f"aeroport_{side}", right_on=f"icao_{side}", how="left", validate="many_to_one")
    # Codes LF + pays FR = Métropole (Corse comprise). Les Outre-mer ont d'autres préfixes OACI.
    pap["interieur_metropole"] = (
        pap["aeroport_1"].str.startswith("LF") & pap["aeroport_2"].str.startswith("LF") &
        pap["iso_country_1"].eq("FR") & pap["iso_country_2"].eq("FR"))
    pap = pap[pap["annee"].le(2024)].copy()
    pap[pap["icao_1"].isna() | pap["icao_2"].isna()][
        ["ANMOIS", "PAP", "PAP1_LABEL", "PAP2_LABEL", "aeroport_1", "aeroport_2", "icao_1", "icao_2"]
    ].to_csv(output / "aeroports_non_apparies.csv", index=False, encoding="utf-8-sig")
    _write_table(pap, root / "data/processed/aviation_pap_mensuel_observe")
    pap_year = pap.groupby(["annee", "PAP", "PAP1_LABEL", "PAP2_LABEL", "interieur_metropole"], as_index=False).agg(
        passagers_observes=("PAP_PAX", "sum"), mois_publies=("mois", "nunique"))
    pap_year["serie_annuelle_complete"] = pap_year["mois_publies"].eq(12)
    _write_table(pap_year, root / "data/processed/aviation_pap_annuel_observe")
    _write_table(airports, root / "data/processed/aviation_aeroports_referentiel")

    co2_frames = []
    for kind, unit in [("TOT", "Mt_CO2_net"), ("UNI", "g_CO2_net_par_Peq_km")]:
        file = next(raw.glob(f"EMI_{kind}_*.csv"))
        df = pd.read_csv(file, sep=";", dtype=str)
        df = df.melt(id_vars="AN", var_name="annee", value_name="valeur").rename(columns={"AN": "faisceau"})
        df["annee"] = df["annee"].astype(int)
        df = _numeric(df, ["valeur"])
        df["unite"] = unit
        co2_frames.append(df)
    co2 = pd.concat(co2_frames, ignore_index=True)
    assert not co2.duplicated(["annee", "faisceau", "unite"]).any()
    _write_table(co2, root / "data/processed/aviation_emissions_annuelles")

    # Contrôle externe : le bulletin 2025 arrondit à 0,01 million de passagers.
    # Valeurs saisies comme références publiées, jamais injectées dans les observations.
    check = annual[annual["annee"].eq(2025)][["LSN_FSC", "passagers"]].copy()
    published = {"MET_RAD": 11.43, "MET_TRA": 8.21, "MET_INTERIEUR": 19.63}
    check["reference_bulletin_2025_millions"] = check["LSN_FSC"].map(published)
    check["recalcule_millions"] = check["passagers"] / 1e6
    check["ecart_millions"] = check["recalcule_millions"] - check["reference_bulletin_2025_millions"]
    check["conforme_arrondi_001_million"] = check["ecart_millions"].abs().le(0.005)
    check["ecart_relatif_pct"] = 100 * check["ecart_millions"] / check["reference_bulletin_2025_millions"]
    # Le ZIP (juillet 2026) est postérieur au bulletin (mai 2026). On garde les
    # écarts, y compris celui qui dépasse l'arrondi, et alerte au-delà de 0,1 %.
    check["compatible_tolerance_01_pct"] = check["ecart_relatif_pct"].abs().le(0.1)
    assert check["compatible_tolerance_01_pct"].all(), "Écart externe DGAC supérieur à 0,1 %"
    check.to_csv(output / "controle_bulletin_2025.csv", index=False, encoding="utf-8-sig")
    annual[annual["annee"].le(2024)].to_csv(output / "trafic_metropole_2015_2024.csv", index=False, encoding="utf-8-sig")
    observed = pap_year[pap_year["interieur_metropole"]].groupby("annee", as_index=False).agg(
        liaisons_publiees=("PAP", "nunique"), passagers_pap_observes=("passagers_observes", "sum"),
        liaisons_12_mois=("serie_annuelle_complete", "sum"))
    observed = observed.merge(annual[annual["LSN_FSC"].eq("MET_INTERIEUR")][["annee", "passagers"]],
                              on="annee", validate="one_to_one")
    observed["ratio_pap_sur_lsn_pct"] = 100 * observed["passagers_pap_observes"] / observed["passagers"]
    observed.to_csv(output / "couverture_pap_metropole.csv", index=False, encoding="utf-8-sig")
    top = pap_year[pap_year["interieur_metropole"] & pap_year["annee"].eq(2024)].sort_values(
        "passagers_observes", ascending=False)
    top.to_csv(output / "liaisons_pap_metropole_2024.csv", index=False, encoding="utf-8-sig")

    # Graphiques descriptifs : aucune régression causale avec la fréquentation des gares.
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = {"MET_RAD": "Paris–province", "MET_TRA": "Province–province", "MET_INTERIEUR": "Métropole : ensemble"}
    for category, group in annual[annual["annee"].le(2024)].groupby("LSN_FSC"):
        ax.plot(group["annee"], group["indice_2019_100"], marker="o", label=labels[category])
    ax.axhline(100, color="grey", linewidth=.7)
    ax.axvspan(2020, 2021, color="grey", alpha=.12)
    ax.set(title="Le trafic aérien intérieur reste inférieur à 2019 en 2024",
           xlabel="Année", ylabel="Indice de passagers, 2019 = 100")
    ax.legend(frameon=False)
    fig.text(.1, .005, "Source : DGAC, LSN. Flux commerciaux sans double compte ; Corse incluse.", fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1))
    fig.savefig(output / "trafic_aerien_base100.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for category, label in [("MET_INTERIEUR", "Intérieur Métropole"), ("FRANCE_TOT", "Total France")]:
        for axis, unit in zip(axes, ["Mt_CO2_net", "g_CO2_net_par_Peq_km"]):
            group = co2[co2["faisceau"].eq(category) & co2["unite"].eq(unit) & co2["annee"].ge(2015)]
            axis.plot(group["annee"], group["valeur"], marker="o", label=label)
    axes[0].set(title="Émissions nettes de CO₂", ylabel="Millions de tonnes de CO₂")
    axes[1].set(title="Intensité d'émission nette", ylabel="g CO₂ / passager équivalent.km")
    for ax in axes:
        ax.set_xlabel("Année")
        ax.legend(frameon=False, fontsize=8)
        ax.tick_params(axis="x", rotation=45)
    fig.text(.07, .005, "DGAC, CSV EMI (publication 2025). SAF inclus ; effets non-CO₂ exclus. Périmètres distincts du bilan GES territorial.", fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(output / "emissions_aeriennes.png", dpi=180)
    plt.close(fig)

    stats = {
        "client_date": CLIENT_DATE,
        "main_period": [2015, 2024],
        "lsn_domestic_monthly_rows": int(len(domestic[domestic["annee"].le(2024)])),
        "pap_observed_monthly_rows": int(len(pap)),
        "pap_airport_1_match_pct": float(100 * pap["icao_1"].notna().mean()),
        "pap_airport_2_match_pct": float(100 * pap["icao_2"].notna().mean()),
        "domestic_pax_2019": int(annual.loc[annual["annee"].eq(2019) & annual["LSN_FSC"].eq("MET_INTERIEUR"), "passagers"].iloc[0]),
        "domestic_pax_2024": int(annual.loc[annual["annee"].eq(2024) & annual["LSN_FSC"].eq("MET_INTERIEUR"), "passagers"].iloc[0]),
        "external_validation_bulletin_2025_within_01_pct": bool(check["compatible_tolerance_01_pct"].all()),
        "external_validation_exact_rounding_all": bool(check["conforme_arrondi_001_million"].all()),
        "co2_total_france_2024_mt_csv": float(co2.loc[co2["annee"].eq(2024) & co2["faisceau"].eq("FRANCE_TOT") & co2["unite"].eq("Mt_CO2_net"), "valeur"].iloc[0]),
        "legal_status_after_2026_05_24": "Prolongation non établie par les sources primaires consultées ; aucune variable de traitement postérieure construite.",
        "warnings": ["PAP : secret statistique et seuil mensuel ; une absence n'est jamais un zéro.",
                     "PAP : deux sens réunis, contrairement à l'ancien intitulé de l'URL.",
                     "Bulletin mai2026 vs ZIP juillet2026 : total intérieur2025 diffère de 6085 passagers (+0,031%), écart conservé.",
                     "Une baisse du trafic aérien et une hausse des entrées/sorties en gares ne mesurent pas un report modal.",
                     "Émissions CO2 CSV : 22,2 Mt en 2024 ; page ministère : 22,1 Mt. Écart de source conservé et signalé."]}
    stats["domestic_growth_2019_2024_pct"] = 100 * (stats["domestic_pax_2024"] / stats["domestic_pax_2019"] - 1)
    (output / "indicateurs.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Recalculer depuis les instantanés locaux uniquement")
    parser.add_argument("--refresh", action="store_true", help="Renouveler explicitement les instantanés")
    args = parser.parse_args()
    print(json.dumps(run(offline=args.offline, refresh=args.refresh), indent=2, ensure_ascii=False))
