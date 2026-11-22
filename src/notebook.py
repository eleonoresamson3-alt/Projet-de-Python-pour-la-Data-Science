"""Créer et exécuter le notebook de restitution, avec un noyau local au projet."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def generate():
    import nbformat as nbf
    nb=nbf.v4.new_notebook()
    md=nbf.v4.new_markdown_cell
    code=nbf.v4.new_code_cell
    nb.cells=[
        md("""# Le rail suit-il la France qui grandit ?

Analyse descriptive de données publiques : population, gares et mobilités. Comparaison principale **2016–2022**, contexte SNCF **2015–2024**. Aucun chiffre simulé ni imputation aléatoire.

Ce notebook part des archives locales brutes et reconstruit les tables, figures et contrôles. Il fonctionne hors ligne une fois les sources collectées. Les méthodes, hypothèses, exceptions et limites sont expliquées dans [la méthodologie](docs/METHODOLOGIE.md) et les colonnes dans [le dictionnaire](docs/DICTIONNAIRE_DONNEES.md)."""),
        code("""from pathlib import Path
import os, sys
ROOT = Path.cwd()
if not (ROOT / 'run.py').exists():
    ROOT = ROOT.parent
assert (ROOT / 'run.py').is_file(), 'Ouvrir le notebook à la racine du projet'
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))

# True : reconstruction depuis les fichiers bruts (comportement de restitution).
# False : lecture des tables déjà produites, pour une exploration rapide.
DEPUIS_LES_BRUTS = True
from run import execute
from src.validation import run as valider
validation = execute(documents=False) if DEPUIS_LES_BRUTS else valider()
assert validation['statut'] == 'CONFORME'
print(f"Validation : {validation['nombre_controles']} contrôles, {validation['nombre_echecs']} échec.")"""),
        md("""## 1. Population statistique et qualité des jointures

Les tables gardent leurs grains : une commune dans la table finale, un UIC × année dans le panel ferroviaire. Les comptages des gares ne sont pas des voyages uniques. Le champ démographique est le COG2025, hors Mayotte ; l'analyse territoriale principale est métropolitaine."""),
        code("""import json
import pandas as pd
from IPython.display import display, Image, Markdown
communes = pd.read_parquet('data/processed/dataset_final_communes.parquet')
gares = pd.read_parquet('data/processed/gares_annees.parquet')
qualite = json.loads(Path('outputs/tables/qualite_jointures.json').read_text(encoding='utf-8'))
display(pd.DataFrame([{'communes': len(communes), 'UIC': gares.code_uic.nunique(),
                      'observations_UIC_annee': len(gares),
                      'jointure_commune_pct': qualite['taux_jointure_commune_pct']}]))
assert not communes.code_commune.duplicated().any()
assert not gares.duplicated(['code_uic', 'annee']).any()
display(pd.read_csv('outputs/tables/gares_jointure_incomplete.csv', dtype={'code_uic': str}))"""),
        md("""## 2. Trajectoires démographiques

On distingue taux annuels communaux, croissance agrégée et soldes naturel/migratoire apparent. Une moyenne de taux communaux n'est pas la croissance de la population totale. Les couleurs des cartes sont saturées aux seuils annoncés ; les tables conservent toutes les valeurs."""),
        code("""display(pd.read_csv('outputs/demographie/population_metropole_historique.csv'))
display(Image(filename='outputs/figures/07_carte_demographie.png', width=850))
display(Image(filename='outputs/demographie/03_soldes_regions.png', width=850))"""),
        md("""## 3. Concentration, Covid et reprise des comptages

La concentration impose de regarder médiane, quantiles et Lorenz/Gini. Les zéros publiés sont conservés et ne prouvent pas une fermeture. L'indice base100en2019 distingue le choc Covid de la reprise. Le périmètre SNCF est non exhaustif et l'historique révisable."""),
        code("""display(pd.read_csv('outputs/tables/frequentation_annuelle.csv'))
display(pd.read_csv('outputs/tables/distribution_gares_2024.csv'))
display(Image(filename='outputs/figures/01_evolution_rail.png', width=900))
display(Image(filename='outputs/figures/02_concentration.png', width=950))"""),
        md("""## 4. Le rail et la population évoluent-ils ensemble ?

La cohorte comporte les mêmes UIC aux deux dates : comptage2016strictement positif,2022observé, y compris zéro. Les nouvelles gares et bases nulles ne sont donc pas représentées par ce taux. Les alertes géographiques INSEE sont exclues du croisement principal.

L'échantillon est constitué de communes d'implantation de gares observées ; ce n'est pas un tirage représentatif des communes françaises. Les taux comparent une population résidente à un usage dont le bassin peut dépasser largement la commune."""),
        code("""principal = communes[communes.metropole
                     & communes.tcam_rail_2016_2022_pct.notna()
                     & communes.tcam_population_2016_2022_pct.notna()
                     & ~communes.alerte_comparabilite_rail_population].copy()
x = principal.tcam_population_2016_2022_pct
y = principal.tcam_rail_2016_2022_pct
part_population = 100 * principal.population_2022.sum() / communes.loc[communes.metropole, 'population_2022'].sum()
display(pd.DataFrame([{'communes': len(principal), 'part_population_metropole_pct': part_population,
                      'Pearson': x.corr(y), 'Spearman': x.corr(y, method='spearman'),
                      'population_hausse_rail_baisse': int(((x > 0) & (y < 0)).sum())}]))
display(pd.read_csv('outputs/tables/sensibilite_correlations.csv'))
display(Image(filename='outputs/figures/03_rail_population.png', width=950))"""),
        md("""Les associations calculées sont faibles dans les variantes étudiées. Elles ne mesurent ni l'adéquation de l'offre ni l'effet de la population sur l'usage ferroviaire. Les quadrants classent des signes ; les taux nuls figurent dans≥0."""),
        md("""## 5. Mobilité automobile, densité et variation de la part voiture

Les parts sont calculées comme ratios des effectifs agrégés sur le même ensemble de communes valides. La population de référence est celle des actifs occupés de15ansou plus, y compris les personnes sans déplacement. La catégorie INSEE « transports en commun » ne se réduit pas au train. Les corrélations n'identifient pas un report modal."""),
        code("""display(pd.read_csv('outputs/tables/mobilites_par_densite.csv'))
display(pd.read_csv('outputs/tables/correlation_rail_evolution_voiture.csv'))
display(Image(filename='outputs/figures/11_rail_evolution_voiture.png', width=900))
display(Image(filename='outputs/figures/05_correlations.png', width=850))"""),
        md("""## 6. Éloignement des gares SNCF : portée du proxy

La distance relie le **centroïde géométrique** communal à une gare du fichier SNCF avec comptage positif en2024. La Corse est hors champ et laissée manquante ; la source ne couvre pas tous les réseaux ferrés, notamment RATP et Chemins de fer de Provence. Ce n'est ni une distance individuelle, ni un temps d'accès, ni une mesure de desserte.

La pondération affecte tous les habitants d'une commune au classement de son centroïde. La « croissance positive » est la somme des hausses communales écrêtées à zéro, et non la croissance nette."""),
        code("""display(pd.read_csv('outputs/tables/accessibilite_proxy.csv'))
display(Image(filename='outputs/figures/09_carte_distance.png', width=850))"""),
        md("""## 7. Climat et scénarios de population

Le parc de voitures est un stock ; il ne mesure pas les émissions routières d'une commune. Les facteurs ADEME sont des références enCO₂epar voyageur.km, construction incluse et voiture à un occupant. Sans distances, origines–destinations et report observé, aucun total d'émissions évitées n'est calculé.

Les projections Omphale sont des scénarios INSEE départementaux, base2018. Les variantes bas/haut ne sont pas des intervalles de confiance et ne sont pas transformées en prévision de trafic."""),
        code("""display(pd.read_parquet('data/processed/climat_facteurs_ademe.parquet'))
display(Image(filename='outputs/climat/facteurs_ademe.png', width=850))
display(Image(filename='outputs/figures/10_carte_projections.png', width=850))
display(Image(filename='outputs/climat/projections_2050.png', width=850))"""),
        md("""## 8. Avion : complément descriptif et censure des liaisons

La tendance intérieure métropolitaine repose sur LSN, agrégée. PAP est censurée par secret statistique et seuils : une absence n'est jamais un zéro et les deux sens déjà réunis ne sont pas doublés. Les unités DGAC et les comptages SNCF diffèrent ; leur comparaison ne mesure pas un report avion–train ni l'effet du décret2023-385."""),
        code("""display(pd.read_csv('outputs/aviation/trafic_metropole_2015_2024.csv'))
display(pd.read_csv('outputs/aviation/couverture_pap_metropole.csv'))
display(Image(filename='outputs/aviation/trafic_aerien_base100.png', width=850))
display(pd.read_csv('data/processed/contexte_lgv.csv')[['ligne', 'mise_en_service_brute', 'date_exacte_iso_si_disponible', 'url_source']])"""),
        md("""## 9. Validation et restitution

L'audit contrôle les empreintes, les clés, les sommes, les ratios et les champs. Il ne remplace pas les notices ni un contrôle indépendant chez les producteurs. Les limites majeures sont la sélection des communes avec gare, les bassins de desserte non mesurés, les révisions de comptage et la censure aérienne.

Les documents finaux sont [le rapport](docs/RAPPORT_ANALYSE.html), [la méthodologie](docs/METHODOLOGIE.html) et [le support de soutenance](docs/SOUTENANCE.md)."""),
        code("""validation_finale = valider()
display(pd.DataFrame([{k: validation_finale[k] for k in ['statut', 'nombre_controles', 'nombre_echecs']}]))
assert validation_finale['statut'] == 'CONFORME'
print('Reconstruction et analyse terminées sans erreur à partir des archives brutes.')"""),
    ]
    nb.metadata={"kernelspec":{"display_name":"Projet statistique (Python3.13)","language":"python","name":"projet-statistique"},
                 "language_info":{"name":"python","version":sys.version.split()[0]}}
    nbf.write(nb,ROOT/"main.ipynb")
    return nb


def execute_notebook():
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    for name in ["ipython", "jupyter_runtime", "jupyter_config"]:
        (ROOT/".cache"/name).mkdir(parents=True,exist_ok=True)
    os.environ["IPYTHONDIR"]=str(ROOT/".cache/ipython")
    os.environ["JUPYTER_RUNTIME_DIR"]=str(ROOT/".cache/jupyter_runtime")
    os.environ["JUPYTER_CONFIG_DIR"]=str(ROOT/".cache/jupyter_config")
    kernel_dir=ROOT/".runtime/kernels/projet-statistique"
    kernel_dir.mkdir(parents=True,exist_ok=True)
    spec={"argv":[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],
          "display_name":"Projet statistique (Python3.13)","language":"python"}
    (kernel_dir/"kernel.json").write_text(json.dumps(spec),encoding="utf-8")
    manager=KernelManager(kernel_name="projet-statistique",kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir.parent)]))
    nb=nbformat.read(ROOT/"main.ipynb",as_version=4)
    def progress(cell,cell_index,**kwargs):
        if cell.cell_type=="code":print(f"Exécution cellule{cell_index+1}/{len(nb.cells)}",flush=True)
    client=NotebookClient(nb,km=manager,timeout=1200,resources={"metadata":{"path":str(ROOT)}},on_cell_start=progress)
    client.execute()
    nbformat.write(nb,ROOT/"main.ipynb")
    print("Notebook exécuté et enregistré avec sorties.",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    generate()
    if args.execute:execute_notebook()
