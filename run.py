"""Point d'entrée : reconstruire le projet depuis les archives, sans réseau par défaut."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))


def execute(*, download=False, refresh=False, documents=True):
    from src import collecte, demographie, climat, aviation, contexte_lgv
    from src import preparation, analyse, analyse_demographie, validation
    if download:
        collecte.run(refresh=refresh)
    else:
        # Vérifie que toutes les pages et les fonds attendus sont présents.
        collecte.run(offline=True)
    demographie.build(offline=not download, refresh=refresh)
    if download:
        climat.collect(refresh=refresh)
    climat.process_parc()
    climat.harmonize_parc_cog2025()
    climat.process_factors()
    climat.process_projections()
    climat.make_figures()
    aviation.run(offline=not download, refresh=refresh)
    contexte_lgv.run(offline=not download, refresh=refresh)
    preparation.build()
    analyse_demographie.run()
    analyse.run()
    result = validation.run()
    if result["statut"] != "CONFORME":
        raise RuntimeError("Validation incomplète ou en échec : consulter outputs/tables/validation_globale.json")
    from src.dictionnaire import generate as dictionnaire
    dictionnaire()
    if documents:
        from src.rapport import generate
        generate()
    return result


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--offline", action="store_true", help="Archives locales uniquement (défaut)")
    group.add_argument("--download", action="store_true", help="Compléter les archives depuis les sources publiques")
    parser.add_argument("--refresh", action="store_true", help="Renouveler les instantanés (avec --download)")
    parser.add_argument("--sans-documents", action="store_true")
    args = parser.parse_args()
    if args.refresh and not args.download:
        parser.error("--refresh nécessite --download")
    execute(download=args.download, refresh=args.refresh, documents=not args.sans_documents)
