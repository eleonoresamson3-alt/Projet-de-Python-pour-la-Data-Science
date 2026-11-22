"""Figures et agrégats démographiques calculés exclusivement sur le socle INSEE."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .collecte import ROOT


def run():
    df = pd.read_parquet(ROOT / "data/processed/demographie_communes.parquet")
    df = df[df.metropole].copy()
    target = ROOT / "outputs/demographie"
    target.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "#ffffff",
                         "axes.labelcolor": "#334155", "text.color": "#0f172a",
                         "savefig.facecolor": "#ffffff"})

    def save(fig, name, note):
        fig.text(.02, .015, note, ha="left", va="bottom", fontsize=8, color="#475569")
        fig.tight_layout(rect=(0, .065, 1, 1))
        fig.savefig(target / f"{name}.png", dpi=180)
        fig.savefig(target / f"{name}.svg")
        plt.close(fig)

    x = df.tcam_population_2016_2022_pct.dropna()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(x, bins=np.linspace(-20, 20, 121), color="#2563eb", edgecolor="white", linewidth=.25)
    ax.axvline(0, color="#0f172a", linewidth=1)
    ax.axvline(x.median(), color="#c2410c", linestyle="--", label=f"Médiane : {x.median():.2f} %")
    ax.set(xlabel="Taux annuel moyen de variation de population 2016–2022 (%)",
           ylabel="Nombre de communes", title="Des trajectoires démographiques très dispersées entre communes")
    ax.legend(frameon=False)
    save(fig, "01_distribution_tcam", f"Source : Insee, RP2022, géographie 2025. France métropolitaine ; {len(x):,} communes avec taux défini.\n"
         "Distribution non pondérée : chaque commune a le même poids. Les taux extrêmes concernent souvent de petits effectifs.")

    years = [1968, 1975, 1982, 1990, 1999, 2006, 2011, 2016, 2022]
    population = pd.DataFrame({"annee": years, "population": [df[f"population_{y}"].sum() for y in years]})
    population.to_csv(target / "population_metropole_historique.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(population.annee, population.population / 1e6, color="#2563eb", marker="o", linewidth=2)
    ax.set(xlabel="Année de référence du recensement", ylabel="Population (millions d'habitants)",
           title="La France métropolitaine compte 65,85 millions d'habitants en 2022")
    ax.set_xticks(years)
    ax.grid(axis="y", color="#e2e8f0", linewidth=.6)
    save(fig, "02_population_historique", "Source : Insee, séries historiques RP2022, géographie communale constante au 01/01/2025.\n"
         "Les points correspondent aux années publiées ; les segments les relient sans créer d'observations annuelles.")

    aggregates = ["population_2016", "population_2022", "variation_population_2016_2022",
                  "solde_naturel_2016_2022", "solde_migratoire_apparent_2016_2022"]
    regions = df.groupby(["code_region", "nom_region"])[aggregates].sum(min_count=1).reset_index()
    regions["tcam_population_2016_2022_pct"] = 100 * ((regions.population_2022 / regions.population_2016) ** (1 / 6) - 1)
    regions.to_csv(target / "soldes_population_regions.csv", index=False, encoding="utf-8-sig")
    regions = regions.sort_values("variation_population_2016_2022")
    positions = np.arange(len(regions))
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(positions - .18, regions.solde_naturel_2016_2022 / 1000, height=.34,
            color="#2563eb", label="Solde naturel")
    ax.barh(positions + .18, regions.solde_migratoire_apparent_2016_2022 / 1000, height=.34,
            color="#059669", label="Solde migratoire apparent")
    ax.axvline(0, color="#0f172a", linewidth=1)
    ax.set_yticks(positions, regions.nom_region)
    ax.set(xlabel="Contribution à la variation 2016–2022 (milliers d'habitants)",
           title="Les composantes de la croissance varient fortement entre régions")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "03_soldes_regions", "Source : Insee, séries historiques RP2022. Champ : France métropolitaine, géographie 2025.\n"
         "Solde naturel : naissances moins décès 2016–2021. Le solde migratoire apparent est un résidu, sensible aux ajustements du recensement.")

    coherent = df.mobilite_geographie_comparable_2016 & df.mobilite_geographie_comparable_2022
    comparable = df[coherent].copy()
    modal_vars = [f"{v}_{y}" for v in ("navetteurs_voiture", "actifs_occupes_15p") for y in (2016, 2022)]
    modes = comparable.groupby("trajectoire_demographique")[modal_vars].sum(min_count=1).reset_index()
    for year in (2016, 2022):
        modes[f"part_voiture_{year}_pct"] = 100 * modes[f"navetteurs_voiture_{year}"] / modes[f"actifs_occupes_15p_{year}"]
    modes = modes[modes.trajectoire_demographique.ne("indetermine")]
    modes.to_csv(target / "part_voiture_par_trajectoire.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = {"declin": "Déclin", "stable": "Stable", "croissance": "Croissance"}
    positions = np.arange(len(modes))
    ax.bar(positions - .17, modes.part_voiture_2016_pct, width=.32, color="#94a3b8", label="2016")
    ax.bar(positions + .17, modes.part_voiture_2022_pct, width=.32, color="#2563eb", label="2022")
    ax.set_xticks(positions, [labels[x] for x in modes.trajectoire_demographique])
    ax.set(ylim=(0, 100), ylabel="Part de la voiture parmi les actifs occupés de 15 ans ou plus (%)",
           xlabel="Trajectoire démographique de la commune 2016–2022", title="La place de la voiture diffère selon les trajectoires territoriales")
    ax.legend(frameon=False)
    save(fig, "04_voiture_trajectoires", "Source : Insee, RP2022. France métropolitaine ; communes comparables aux deux dates. Ratio des sommes.\n"
         "Trajectoires : déclin < −0,2 %/an ; stable ±0,2 %/an ; croissance > +0,2 %/an. Ce croisement descriptif ne prouve pas un report vers le rail.")

    summary = {
        "communes_metropole": len(df), "population_2016": float(df.population_2016.sum()),
        "population_2022": float(df.population_2022.sum()),
        "croissance_population_2016_2022_pct": float(100 * (df.population_2022.sum() / df.population_2016.sum() - 1)),
        "mediane_tcam_communes_pct": float(x.median()), "moyenne_tcam_communes_non_ponderee_pct": float(x.mean()),
        "nombre_communes_en_croissance": int(df.trajectoire_demographique.eq("croissance").sum()),
        "nombre_communes_en_declin": int(df.trajectoire_demographique.eq("declin").sum()),
        "nombre_communes_stables": int(df.trajectoire_demographique.eq("stable").sum()),
        "population_communes_croissance_2022": float(df.loc[df.trajectoire_demographique.eq("croissance"), "population_2022"].sum()),
        "communes_mobilite_comparables_2016_2022": len(comparable),
        "source": "Insee, RP2022, géographie COG2025", "champ": "France métropolitaine"}
    (target / "synthese.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    run()
