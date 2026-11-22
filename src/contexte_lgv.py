"""Scraping limité de trois infobox Wikipédia : contexte des ouvertures de LGV.

robots.txt archivé et respecté, temporisation >= 2 s, cache et SHA-256.
Une date absente ou donnée comme intervalle n'est jamais inventée.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.robotparser import RobotFileParser

from .collecte import ROOT, USER_AGENT, fetch

PAGES = ["LGV_Sud_Europe_Atlantique", "LGV_Bretagne-Pays_de_la_Loire", "LGV_Atlantique"]
BASE = "https://fr.wikipedia.org/wiki/"


class Rows(HTMLParser):
    """Extrait le texte des cellules de tableaux, sans exécuter le HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.stack.append({"cells": [], "current": None})
        elif tag in ("th", "td") and self.stack:
            self.stack[-1]["current"] = []
        elif tag == "br" and self.stack and self.stack[-1]["current"] is not None:
            self.stack[-1]["current"].append(" ")

    def handle_data(self, value):
        for row in self.stack:
            if row["current"] is not None:
                row["current"].append(value)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.stack:
            row = self.stack[-1]
            if row["current"] is not None:
                row["cells"].append(" ".join("".join(row["current"]).split()))
                row["current"] = None
        elif tag == "tr" and self.stack:
            self.rows.append(self.stack.pop()["cells"])


def run(*, offline=True, refresh=False):
    raw = ROOT / "data/raw/contexte"
    output = ROOT / "data/processed"
    raw.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    robots_url = "https://fr.wikipedia.org/robots.txt"
    robots = fetch(robots_url, raw / "robots_wikipedia.txt", offline=offline, refresh=refresh)
    rules = RobotFileParser()
    rules.parse(robots.decode("utf-8").splitlines())
    delay = max(2, rules.crawl_delay(USER_AGENT) or 0)
    records, manifest = [], []
    manifest_path = raw / "manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    previous_hashes = {x["file"]: x["sha256"] for x in previous}

    def remember(path, url):
        blob = path.read_bytes()
        name = path.relative_to(ROOT).as_posix()
        sha = hashlib.sha256(blob).hexdigest()
        if not refresh and name in previous_hashes:
            assert previous_hashes[name] == sha, f"Cache modifié : {path}"
        manifest.append({"file": name, "url": url, "sha256": sha, "bytes": len(blob),
                         "local_file_mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})

    remember(raw / "robots_wikipedia.txt", robots_url)
    last_request = time.monotonic()
    for title in PAGES:
        url = BASE + title
        if not rules.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt interdit cette collecte : {url}")
        path = raw / f"{title}.html"
        if not offline and (refresh or not path.exists()):
            time.sleep(max(0, delay - (time.monotonic() - last_request)))
            content = fetch(url, path, offline=False, refresh=refresh)
            last_request = time.monotonic()
        else:
            content = fetch(url, path, offline=offline, refresh=refresh)
        remember(path, url)
        parser = Rows()
        parser.feed(content.decode("utf-8"))
        cells = [row for row in parser.rows if len(row) >= 2 and row[0] == "Mise en service"]
        assert len(cells) == 1, f"Structure HTML modifiée, date non univoque : {title}, {cells}"
        raw_date = cells[0][1]
        years = sorted(set(int(y) for y in re.findall(r"\b(?:18|19|20)\d{2}\b", raw_date)))
        assert years, f"Aucune année extraite : {raw_date}"
        iso_date = ""
        exact = re.fullmatch(r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})", raw_date)
        if exact:
            months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            iso_date = f"{exact[3]}-{months.index(exact[2]) + 1:02d}-{int(exact[1]):02d}"
            datetime.fromisoformat(iso_date)  # contrôle de validité du calendrier
        records.append({"ligne": title.replace("_", " "), "champ_html": "Mise en service",
                        "mise_en_service_brute": raw_date, "date_exacte_iso_si_disponible": iso_date,
                        "annee_min": years[0], "annee_max": years[-1], "url_source": url,
                        "fichier_html": path.relative_to(ROOT).as_posix(),
                        "sha256_html": hashlib.sha256(content).hexdigest(), "robots_autorise": True,
                        "role": "Contexte documentaire ; aucune attribution causale ni jointure aux communes"})
    assert len(records) == 3
    with (output / "contexte_lgv.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    quality = {"pages": len(records), "robots_url": robots_url, "delay_seconds_minimum": delay,
               "extraction": "HTMLParser, cellules de la ligne Mise en service", "client_date": "2026-10-26",
               "dates_exactes": sum(bool(r["date_exacte_iso_si_disponible"]) for r in records),
               "selection": "Trois LGV de l'ouest : échantillon de contexte raisonné, non exhaustif"}
    (raw / "controle.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(offline=args.offline, refresh=args.refresh), ensure_ascii=False, indent=2))
