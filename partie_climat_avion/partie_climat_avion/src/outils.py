import os

import requests
import yaml


def charger_config():
    """Lit config.yaml et renvoie les paramètres sous forme de dictionnaire."""
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_fichier(url, chemin):
    """Télécharge url dans chemin, sauf si le fichier existe déjà (cache)."""
    if os.path.exists(chemin):
        print("déjà téléchargé :", chemin)
        return chemin
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    reponse = requests.get(url, timeout=60)
    reponse.raise_for_status()
    with open(chemin, "wb") as f:
        f.write(reponse.content)
    print("téléchargé :", chemin)
    return chemin
    