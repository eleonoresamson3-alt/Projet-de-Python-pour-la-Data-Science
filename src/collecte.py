"""Collecte publique avec cache, empreintes SHA-256 et pagination vérifiée."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
USER_AGENT = "Projet-universitaire-rail-demographie/1.0 (collecte de donnees publiques)"


def fetch(url: str, path: Path, *, refresh=False, offline=False) -> bytes:
    """Ne remplace jamais un fichier existant, sauf demande explicite --refresh."""
    if path.exists() and not refresh:
        return path.read_bytes()
    if offline:
        raise FileNotFoundError(f"Cache brut absent en mode hors ligne : {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=180) as response:
                content = response.read()
                headers = dict(response.headers)
                resolved = response.url
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(content)
    temporary.replace(path)
    provenance = {
        "url": url, "resolved_url": resolved,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_reference_date": "2026-10-26", "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "last_modified": headers.get("Last-Modified"),
        "content_type": headers.get("Content-Type"),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collecte {path.relative_to(ROOT)} : {len(content):,} octets", flush=True)
    return content


def ods(dataset: str, *, offline=False, refresh=False):
    """API Explore v2.1 : cache de chaque page, nombre total contrôlé."""
    folder = ROOT / "data/raw/sncf" / dataset
    meta = json.loads(fetch(BASE + dataset, folder / "metadata.json", offline=offline, refresh=refresh))
    rows, offset = [], 0
    while True:
        query = urlencode({"limit": 100, "offset": offset})
        page = json.loads(fetch(BASE + dataset + "/records?" + query,
                                folder / f"page_{offset:05}.json", offline=offline, refresh=refresh))
        total = page["total_count"]
        rows.extend(page["results"])
        offset += len(page["results"])
        if offset >= total:
            break
        if not page["results"]:
            raise ValueError("Pagination interrompue avant le total annoncé")
        if not offline:
            time.sleep(.12)
    if len(rows) != total:
        raise ValueError(f"{dataset}: {len(rows)} lignes pour {total} annoncées")
    print(f"{dataset}: {total} enregistrements contrôlés", flush=True)
    return rows, meta


def run(*, offline=False, refresh=False):
    for name in ("frequentation-gares", "gares-de-voyageurs", "liste-des-gares"):
        ods(name, offline=offline, refresh=refresh)
    geo = "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/"
    for filename in ("communes-100m.geojson.gz", "departements-100m.geojson.gz", "regions-100m.geojson.gz"):
        fetch(geo + filename, ROOT / "data/raw/geographie" / filename, offline=offline, refresh=refresh)
    # Export GeoJSON : fond de réseau, pas une mesure de l'offre voyageurs.
    fetch(BASE + "formes-des-lignes-du-rfn/exports/geojson",
          ROOT / "data/raw/sncf/reseau.geojson", offline=offline, refresh=refresh)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    run(offline=args.offline, refresh=args.refresh)
