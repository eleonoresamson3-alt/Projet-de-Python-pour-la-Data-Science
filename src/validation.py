"""Audit hors ligne des données réelles, des empreintes et des conservations.

N'appelle aucun module de production pour fabriquer les résultats attendus.
Écrit outputs/tables/validation_globale.json même en cas d'anomalie.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def run(root: Path | str | None = None) -> dict:
    import numpy as np
    import pandas as pd

    root = Path(root) if root is not None else ROOT
    checks, warnings, skipped = [], [], []
    raw, processed = root / "data/raw", root / "data/processed"

    def check(name, condition, details=None):
        checks.append({"controle": name, "conforme": bool(condition), "details": details})

    def read(name):
        path = processed / f"{name}.parquet"
        if not path.exists():
            skipped.append({"controle": name, "raison": "Table pas encore produite"})
            return None
        return pd.read_parquet(path)

    # Plusieurs formats de provenance existent : tous sont compris explicitement.
    expected = {}
    manifests = list(raw.rglob("*manifest*.json"))
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("files"), list):
            entries = data["files"]
        elif isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = [dict(v, file=(path.parent / k).relative_to(root).as_posix())
                       for k, v in data.items() if isinstance(v, dict) and "sha256_file" in v]
        else:
            raise ValueError(f"Format de manifeste non compris : {path}")
        for entry in entries:
            name = entry.get("file", entry.get("path", "")).replace("\\", "/")
            sha = entry.get("sha256", entry.get("sha256_file"))
            if name and sha:
                expected.setdefault(name, set()).add(sha)
    for sidecar in raw.rglob("*.provenance.json"):
        entry = json.loads(sidecar.read_text(encoding="utf-8"))
        path = sidecar.with_name(sidecar.name.removesuffix(".provenance.json"))
        if "sha256" in entry:
            expected.setdefault(path.relative_to(root).as_posix(), set()).add(entry["sha256"])
    bad_hashes, missing_raw, conflicting_hashes = [], [], []
    for name, hashes in sorted(expected.items()):
        path = root / name
        if len(hashes) != 1:
            conflicting_hashes.append(name)
        if not path.exists():
            missing_raw.append(name)
        elif _digest(path) not in hashes:
            bad_hashes.append(name)
    check("empreintes_sources", not (bad_hashes or missing_raw or conflicting_hashes),
          {"fichiers_controles": len(expected), "manifestes": len(manifests), "empreintes_differentes": bad_hashes,
           "fichiers_absents": missing_raw, "empreintes_contradictoires": conflicting_hashes})

    tables = {}
    grains = {
        "demographie_communes": ["code_commune"], "demographie_population_long": ["code_commune", "annee"],
        "gares_referentiel": ["code_uic"], "gares_annees": ["code_uic", "annee"],
        "communes_annees_rail": ["code_commune", "annee"], "dataset_final_communes": ["code_commune"],
        "climat_parc_communes": ["code_commune"], "climat_parc_communes_cog2025": ["code_commune"],
        "climat_projections_departements": ["code_departement", "scenario_insee"],
        "aviation_trafic_annuel": ["annee", "LSN_FSC"],
        "aviation_trafic_mensuel": ["ANMOIS", "LSN_SEG", "LSN_FSC", "LSN_1", "LSN_2"],
        "aviation_pap_mensuel_observe": ["ANMOIS", "PAP"],
        "aviation_pap_annuel_observe": ["annee", "PAP"],
        "aviation_emissions_annuelles": ["annee", "faisceau", "unite"],
        "aviation_aeroports_referentiel": ["icao"]}
    for name, keys in grains.items():
        table = read(name)
        if table is None:
            continue
        tables[name] = table
        check(f"grain_{name}", not table.duplicated(keys).any() and table[keys].notna().all().all(),
              {"lignes": len(table), "cles": keys})
        for key, pattern in [("code_commune", r"[0-9AB]{5}"), ("code_uic", r"\d{8}")]:
            if key in table:
                values = table[key].dropna()
                strings = values.map(lambda x: isinstance(x, str)).all()
                check(f"format_{name}_{key}", strings and values.astype(str).str.fullmatch(pattern).all(),
                      {"valeurs_non_nulles": len(values)})
        numeric = table.select_dtypes(include="number")
        check(f"absence_infini_{name}", not np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).any())

    demo, final = tables.get("demographie_communes"), tables.get("dataset_final_communes")
    long, commune_year = tables.get("gares_annees"), tables.get("communes_annees_rail")
    if demo is not None and final is not None:
        check("conservation_communes_apres_jointures", set(demo.code_commune) == set(final.code_commune)
              and len(demo) == len(final), {"insee": len(demo), "final": len(final)})
        population_columns = [c for c in demo if re.fullmatch(r"population_\d{4}", c)]
        a = demo.set_index("code_commune").sort_index()[population_columns]
        b = final.set_index("code_commune").reindex(a.index)[population_columns]
        check("conservation_populations_apres_jointures", np.allclose(a, b, equal_nan=True, rtol=0, atol=0))
        check("population_nonnegative", a.ge(0).where(a.notna(), True).all().all())
        for cutoff in (5, 10, 15):
            flag = f"centre_a_plus_de_{cutoff}km"
            if flag in final and "distance_centre_gare_km" in final:
                known = final.distance_centre_gare_km.notna()
                check(f"couverture_distance_{cutoff}km", final.loc[known, flag].eq(
                    final.loc[known, "distance_centre_gare_km"].gt(cutoff)).all()
                    and final.loc[~known, flag].isna().all())
        if "distance_centre_gare_km" in final:
            check("distances_nonnegatives", final.distance_centre_gare_km.dropna().ge(0).all())
            if "champ_distance_france_continentale" in final:
                declared = final.champ_distance_france_continentale
                expected_scope = ~final.code_departement.str.startswith(("2A", "2B", "97", "98"))
                check("champ_distance_france_continentale_explicitement_defini",
                      declared.notna().all() and declared.eq(expected_scope).all())
                in_scope = declared.eq(True)
                distance = final.distance_centre_gare_km
                check("distance_finie_nonnegative_dans_champ_continental",
                      distance.loc[in_scope].notna().all()
                      and np.isfinite(distance.loc[in_scope].to_numpy(dtype=float)).all()
                      and distance.loc[in_scope].ge(0).all(),
                      {"communes_dans_champ": int(in_scope.sum())})
                check("distance_non_mesuree_hors_champ_continental", distance.loc[~in_scope].isna().all(),
                      {"communes_hors_champ": int((~in_scope).sum()),
                       "motif": "Corse : réseau CFC absent de la source SNCF ; Outre-mer hors champ."})

    if long is not None:
        check("frequentation_nonnegative", long.voyageurs.dropna().ge(0).all())
        folder = raw / "sncf/frequentation-gares"
        raw_rows = []
        for page in sorted(folder.glob("page_?????.json")):
            raw_rows.extend(json.loads(page.read_text(encoding="utf-8"))["results"])
        source = pd.DataFrame(raw_rows)
        if len(source):
            check("conservation_gares_source", set(source.code_uic_complet) == set(long.code_uic))
            differences = []
            for year in sorted(long.annee.unique()):
                columns = [c for c in source if re.fullmatch(fr"total_?voyageurs_?{year}", c)]
                if len(columns) != 1:
                    differences.append({"annee": int(year), "erreur": "Colonne source ambiguë"})
                    continue
                src = source.set_index("code_uic_complet")[columns[0]].sort_index()
                dst = long.loc[long.annee.eq(year)].set_index("code_uic").voyageurs.reindex(src.index)
                if not np.allclose(src, dst, equal_nan=True, rtol=0, atol=0):
                    differences.append({"annee": int(year), "erreur": "Valeurs source modifiées"})
            check("frequentation_identique_a_la_source_par_gare_annee", not differences, differences)
        if commune_year is not None:
            src = long.dropna(subset=["code_commune"]).groupby("annee").voyageurs.sum(min_count=1)
            dst = commune_year.groupby("annee").voyageurs_gares.sum(min_count=1).reindex(src.index)
            check("conservation_comptages_agregation_communale", np.allclose(src, dst, equal_nan=True, rtol=0, atol=0))
            total = long.groupby("annee").voyageurs.sum(min_count=1)
            unmatched = long[long.code_commune.isna()].groupby("annee").voyageurs.sum(min_count=1).reindex(total.index, fill_value=0)
            check("totaux_rattaches_plus_non_rattaches", np.allclose(total, dst.reindex(total.index, fill_value=0) + unmatched,
                                                                          equal_nan=True, rtol=0, atol=0))
        if final is not None:
            for year in (2016, 2022):
                column = f"voyageurs_cohorte_{year}"
                if column in final:
                    check(f"cohorte_{year}_nonnegative", final[column].dropna().ge(0).all())
            if {"voyageurs_cohorte_2016", "voyageurs_cohorte_2022", "croissance_rail_2016_2022_pct"}.issubset(final):
                known = final.voyageurs_cohorte_2016.notna()
                check("cohorte_denominateur_strictement_positif", final.loc[known, "voyageurs_cohorte_2016"].gt(0).all())
                expected_ratio = 100 * (final.loc[known, "voyageurs_cohorte_2022"] / final.loc[known, "voyageurs_cohorte_2016"] - 1)
                check("cohorte_croissance_arithmetiquement_exacte", np.allclose(expected_ratio,
                      final.loc[known, "croissance_rail_2016_2022_pct"], equal_nan=True, rtol=1e-12, atol=1e-9))
                eligibility = long.pivot(index="code_uic", columns="annee", values="voyageurs")
                eligible = eligibility.index[eligibility[2016].gt(0) & eligibility[2022].notna()]
                totals = long[long.code_uic.isin(eligible) & long.code_commune.notna()].groupby("annee").voyageurs.sum()
                check("cohorte_somme_sans_multiplication_par_jointure", all(np.isclose(
                    final[f"voyageurs_cohorte_{y}"].sum(), totals[y], rtol=0, atol=0) for y in (2016, 2022)))
        quality_path = root / "outputs/tables/qualite_jointures.json"
        if quality_path.exists():
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            station_rows = long.drop_duplicates("code_uic")
            actual = {
                "gares_frequentation": len(station_rows),
                "gare_avec_commune": int(station_rows.code_commune.notna().sum()),
                "valeurs_manquantes_frequentation": int(long.voyageurs.isna().sum()),
                "valeurs_nulles_frequentation": int(long.voyageurs.eq(0).sum())}
            discrepancies = {key: {"annonce": quality[key], "observe": value}
                             for key, value in actual.items() if key in quality and quality[key] != value}
            check("effectifs_rapport_qualite_conformes_aux_tables", not discrepancies, discrepancies)
        ref = tables.get("gares_referentiel")
        if ref is not None and "dispersion_projections_reseau_m" in ref:
            ambiguous = ref.source_coordonnees.fillna("").str.startswith("SNCF Réseau") & ref.dispersion_projections_reseau_m.gt(1000)
            check("aucune_coordonnee_reseau_ambigue_utilisee", not ambiguous.any(),
                  {"uic_ambigus_utilises": ref.loc[ambiguous, "code_uic"].tolist()})

    parc = tables.get("climat_parc_communes_cog2025")
    if parc is not None and demo is not None:
        check("parc_cog2025_codes_valides", parc.code_commune.isin(demo.code_commune).all(),
              {"communes_parc": len(parc), "communes_insee": len(demo)})
        if final is not None:
            check("parc_effectifs_apres_jointure", final.vp_2022.notna().sum() == parc.vp_2022.notna().sum())
            check("parc_totaux_apres_jointure", all(np.isclose(final[c].sum(), parc[c].sum(), rtol=0, atol=1e-5)
                  for c in parc if re.fullmatch(r"vp_\d{4}", c)))
    source_parc, fictive = tables.get("climat_parc_communes"), read("climat_parc_codes_fictifs")
    national_path = root / "outputs/climat/parc_national.csv"
    if source_parc is not None and fictive is not None and national_path.exists():
        national = pd.read_csv(national_path)
        check("parc_codes_communes_et_fictifs_conservent_total", all(np.isclose(
            source_parc[f"vp_{int(r.annee_stock_1_janvier)}"].sum() + fictive[f"vp_{int(r.annee_stock_1_janvier)}"].sum(),
            r.vp_tous_codes, rtol=0, atol=1e-5) for r in national.itertuples()))

    annual, monthly = tables.get("aviation_trafic_annuel"), tables.get("aviation_trafic_mensuel")
    if annual is not None and monthly is not None:
        domestic = annual[annual.LSN_FSC.eq("MET_INTERIEUR")].set_index("annee").passagers
        summed = monthly.groupby("annee").LSN_PAX.sum().reindex(domestic.index)
        check("avion_lsn_conservation_mensuel_annuel", np.array_equal(domestic, summed))
        check("avion_lsn_douze_mois", monthly.groupby(["annee", "LSN_FSC"]).mois.nunique().eq(12).all())
    pap = tables.get("aviation_pap_annuel_observe")
    if pap is not None:
        check("pap_censure_et_couverture_explicites", pap.mois_publies.between(1, 12).all()
              and pap.serie_annuelle_complete.eq(pap.mois_publies.eq(12)).all())
    context_path = processed / "contexte_lgv.csv"
    if context_path.exists():
        context = pd.read_csv(context_path)
        check("scraping_contexte_trois_pages_uniques", len(context) == 3 and context.url_source.is_unique
              and context.robots_autorise.eq(True).all())
        check("scraping_contexte_empreintes_html", all(_digest(root / r.fichier_html) == r.sha256_html
                                                           for r in context.itertuples()))

    if final is not None:
        warnings.append("Accessibilité : distance du centroïde communal à une gare SNCF comptée en 2024, en France continentale ; Corse et Outre-mer non mesurés. Ce n'est ni une distance individuelle ni un horaire de desserte.")
        warnings.append("Cohorte 2016–2022 : exclut les gares sans fréquentation strictement positive en 2016 ; n'évalue pas les effets des nouvelles gares.")
    warning_sources = root / "outputs/aviation/indicateurs.json"
    if warning_sources.exists():
        warnings.extend(json.loads(warning_sources.read_text(encoding="utf-8")).get("warnings", []))
    failures = [x for x in checks if not x["conforme"]]
    result = {"date_client_reference": "2026-10-26", "executed_at_utc": datetime.now(timezone.utc).isoformat(),
              "statut": "ECHEC" if failures else ("PARTIEL" if skipped else "CONFORME"),
              "nombre_controles": len(checks), "nombre_echecs": len(failures), "controles": checks,
              "controles_reportes": skipped, "avertissements_methodologiques": warnings,
              "portee": "Audit d'intégrité, cohérence et conservation ; ne prouve pas l'exactitude de toutes les observations des producteurs."}
    target = root / "outputs/tables/validation_globale.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "controles"}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["nombre_echecs"] else 0)
