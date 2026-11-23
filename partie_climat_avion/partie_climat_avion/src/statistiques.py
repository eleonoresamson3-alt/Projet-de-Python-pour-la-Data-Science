def build_resume_groupes(table, groupe, annee_fin):
    """Par groupe de communes : poids dans la population, part de la voiture et CO2 par actif (ratios de sommes)."""
    resume = table.groupby(groupe).agg(
        communes=("code_commune", "count"),
        habitants=(f"pop_{annee_fin}", "sum"),
        actifs=("actifs", "sum"),
        actifs_voiture=("actifs_voiture", "sum"),
        co2_kg=("co2_kg", "sum"),
        distance_gare_mediane_km=("distance_gare_km", "median"),
        voitures_1000_hab_mediane=("voitures_1000_hab", "median"),
    )
    resume["part_habitants_pct"] = resume["habitants"] / resume["habitants"].sum() * 100
    resume["part_voiture_pct"] = resume["actifs_voiture"] / resume["actifs"] * 100
    resume["co2_kg_par_actif"] = resume["co2_kg"] / resume["actifs"]
    colonnes = ["communes", "part_habitants_pct", "part_voiture_pct", "co2_kg_par_actif",
                "distance_gare_mediane_km", "voitures_1000_hab_mediane"]
    return resume[colonnes]