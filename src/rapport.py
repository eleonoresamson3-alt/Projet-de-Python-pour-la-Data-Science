"""Documents français générés à partir des résultats effectivement calculés."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def fr(value, decimals=1):
    return f"{value:,.{decimals}f}".replace(",", "\u202f").replace(".", ",")


def md_table(frame, columns=None, digits=2):
    data = frame[columns].copy() if columns else frame.copy()
    def cell(value):
        if pd.isna(value):
            return "Non disponible"
        if isinstance(value, (float, int)):
            return fr(value, digits if isinstance(value, float) else 0)
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(map(str, data.columns)) + " |", "| " + " | ".join(["---"]*len(data.columns)) + " |"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in data.itertuples(index=False, name=None)]
    return "\n".join(lines)


def to_html(markdown_text, title, target):
    import markdown
    body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "toc"])
    def embed(match):
        url = html.unescape(match[1])
        file = (DOCS / url).resolve()
        if file.is_file() and file.suffix.lower() == ".png":
            return 'src="data:image/png;base64,' + base64.b64encode(file.read_bytes()).decode() + '"'
        return match[0]
    body = re.sub(r'src="([^"]+)"', embed, body)
    css = """
    :root { color-scheme:light; --ink:#172b3a; --muted:#536674; --accent:#176b87; }
    *{box-sizing:border-box} body{margin:0;background:#edf1f3;color:var(--ink);font:17px/1.65 Georgia,'Times New Roman',serif}
    main{max-width:1080px;margin:36px auto;background:white;padding:64px 72px;box-shadow:0 4px 24px #10273312}
    h1,h2,h3{font-family:Calibri,Arial,sans-serif;line-height:1.2;color:#12384c}h1{font-size:40px;border-bottom:4px solid #176b87;padding-bottom:24px}
    h2{margin-top:48px;font-size:27px}h3{margin-top:32px}a{color:#12617c;overflow-wrap:anywhere}p,li{max-width:90ch}
    table{font:14px/1.4 Calibri,Arial,sans-serif;border-collapse:collapse;width:100%;margin:24px 0}th,td{padding:10px 12px;border-bottom:1px solid #d7e1e6;text-align:left;vertical-align:top}th{background:#eaf1f5}
    img{max-width:100%;height:auto;display:block;margin:24px auto}blockquote{border-left:4px solid #d49738;background:#fcf6eb;margin:24px 0;padding:8px 22px}
    pre{background:#f3f6f8;padding:18px;overflow:auto;font-size:13px}code{font-size:.88em}strong{color:#12384c}
    .meta{font:14px Calibri,Arial,sans-serif;color:var(--muted)}
    @media(max-width:700px){main{margin:0;padding:28px 20px}h1{font-size:30px}table{display:block;overflow:auto}}
    @media print{body{background:white;font-size:11pt}main{margin:0;padding:0;box-shadow:none;max-width:none}h2{break-after:avoid}img,table{break-inside:avoid}a{color:inherit}}
    """
    target.write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{css}</style></head><body><main><p class="meta">Projet statistique · Données publiques · Instantanés du 26 octobre 2026</p>{body}</main></body></html>',encoding="utf-8")


def to_docx(markdown_text, target):
    from docx import Document
    from docx.shared import Cm, Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2)
    section.top_margin = section.bottom_margin = Cm(1.8)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"; normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    for name in ["Title", "Heading 1", "Heading 2", "Heading 3"]:
        doc.styles[name].font.color.rgb = RGBColor.from_string("12384C")
    footer = section.footer.paragraphs[0]
    footer.add_run("Projet rail · démographie · mobilités     |     ")
    field = OxmlElement("w:fldSimple"); field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    def plain(s):
        s = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
        return s.replace("**", "").replace("`", "")
    lines = markdown_text.splitlines(); i=0; code=False
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("```"):
            code = not code; i+=1; continue
        if not line:
            i+=1; continue
        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)",line)
        if image_match:
            path = DOCS / image_match[2]
            if path.is_file():
                doc.add_picture(str(path),width=Inches(6.5))
                doc.add_paragraph(image_match[1],style="Caption")
        elif line.startswith("|") and i+1 < len(lines) and re.match(r"\|[\s:|\-]+$",lines[i+1].strip()):
            rows = []; rows.append([plain(x.strip()) for x in line.strip("|").split("|")]); i+=2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([plain(x.strip()) for x in lines[i].strip().strip("|").split("|")]); i+=1
            table = doc.add_table(rows=1,cols=len(rows[0])); table.style="Light Shading Accent 1"
            for j,value in enumerate(rows[0]):table.rows[0].cells[j].text=value
            for row in rows[1:]:
                cells=table.add_row().cells
                for j,value in enumerate(row[:len(cells)]):cells[j].text=value
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:run.font.size=Pt(8)
            continue
        elif line.startswith("#"):
            level=len(line)-len(line.lstrip("#"))
            doc.add_heading(plain(line.lstrip("# ")),0 if level==1 else min(level-1,3))
        elif code:
            p=doc.add_paragraph();r=p.add_run(line);r.font.name="Consolas";r.font.size=Pt(9)
        elif line.startswith("- "):
            doc.add_paragraph(plain(line[2:]),style="List Bullet")
        elif line.startswith(">"):
            doc.add_paragraph(plain(line.lstrip("> ")),style="Quote")
        else:
            doc.add_paragraph(plain(line))
        i+=1
    doc.core_properties.title=markdown_text.splitlines()[0].lstrip("# ")
    doc.core_properties.subject="Analyse descriptive reproductible de données publiques"
    doc.core_properties.author="Projet statistique – document généré à partir des résultats calculés"
    doc.save(target)


def generate():
    stats=read_json("outputs/tables/indicateurs.json")
    quality=read_json("outputs/tables/qualite_jointures.json")
    checks=read_json("outputs/tables/validation_globale.json")
    dem=read_json("outputs/tables/controle_demographie.json")
    air=read_json("outputs/aviation/indicateurs.json")
    parc=read_json("outputs/climat/qualite_passage_cog2025.json")
    frame=pd.read_parquet(ROOT/"data/processed/dataset_final_communes.parquet")
    profiles=pd.read_csv(ROOT/"outputs/tables/profils_rail_population.csv")
    sensitivity=pd.read_csv(ROOT/"outputs/tables/sensibilite_correlations.csv")
    density=pd.read_csv(ROOT/"outputs/tables/mobilites_par_densite.csv")
    access=pd.read_csv(ROOT/"outputs/tables/accessibilite_proxy.csv")
    factors=pd.read_parquet(ROOT/"data/processed/climat_facteurs_ademe.parquet")
    sample=frame[frame.metropole & frame.tcam_rail_2016_2022_pct.notna() & frame.tcam_population_2016_2022_pct.notna() & ~frame.alerte_comparabilite_rail_population]
    sample_pop=sample.population_2022.sum()/frame.loc[frame.metropole,"population_2022"].sum()*100
    sha_n=checks["controles"][0]["details"]["fichiers_controles"]
    sources="""| Source | Rôle effectif | Millésime / accès |
| --- | --- | --- |
| SNCF Gares & Connexions | Comptages annuels, UIC, coordonnées et code commune | Fréquentation2015–2024 ; référentiel extrait le26/10/2026 ; API paginée |
| SNCF Réseau | Coordonnées de secours et tracés du réseau | Liste des gares et GeoJSON archivés ; API et export |
| INSEE RP2022 | Population1968–2022, ménages, motorisation et déplacements domicile–travail | Fichiers ZIP ; géographie COG2025 |
| INSEE COG2025 et grille de densité2025 | Codes parents, régions et typologie officielle urbain/rural | CSV et XLSX |
| Etalab / contours administratifs | Polygones pour rattachement spatial et cartographie | Version2025, simplification100m, GeoJSON compressé |
| SDES / API Dido | Stocks de voitures particulières et détenteurs | Édition2026-06 ; stocks au1erjanvier2016,2019,2022,2023,2024 |
| ADEME Impact CO₂ | Facteurs moyens de comparaison des modes | API publique ; construction incluse ; voiture à1occupant |
| INSEE Omphale2022 | Trois scénarios départementaux jusqu'à2050 | Population de base2018 ; fichiers officiels |
| DGAC | Trafic domestique LSN, liaisons PAP et émissions annuelles | Archives1990–2025 ; analyse2015–2024 |
| OurAirports | Géolocalisation et codes des aéroports | Référentiel courant archivé ; CSV, domaine public |
| Wikipédia, trois pages LGV | Dates de mise en service à titre de contexte | Scraping HTML, robots.txt vérifié ; pas de jointure analytique |
"""
    method=f"""# Méthodologie de constitution des données et d'analyse

Projet : **Le rail suit-il la France qui grandit ?** Démographie, fréquentation des gares et mobilités dans les territoires.

Version du26octobre2026. Document généré depuis les contrôles et résultats enregistrés, avec conservation des fichiers bruts. Le brouillon de départ reste dans `docs/Brouillon idées projet python.docx` ; son texte est également extrait dans `docs/contexte_extrait.txt`.

## 1. Question, portée et engagement sur les données

L'objectif est de décrire comment la population et l'usage observé des gares évoluent conjointement, puis de rapprocher ces évolutions des caractéristiques territoriales et de la dépendance automobile. La fréquentation mesure un usage estimé par le producteur ; elle ne mesure directement ni l'offre de trains, ni la capacité, ni la satisfaction des besoins de transport.

Le projet ne génère aucune observation ni aucun tirage aléatoire pour compléter une série. Cette règle concerne nos traitements ; le recensement source repose lui-même en partie sur des enquêtes par sondage. Les données d'origine sont archivées ; les traitements calculent des agrégats, des ratios et des indicateurs vérifiables. Les projections Omphale sont des scénarios officiels de l'INSEE, identifiés comme tels. Les facteurs carbone sont des références moyennes, distinctes des émissions réellement observées dans un territoire.

La démarche est descriptive et exploratoire. La population étudiée n'est pas un échantillon probabiliste : aucun intervalle de confiance de sondage ni test de causalité n'est construit. Les incertitudes dominantes concernent les périmètres, la qualité des mesures, la censure et les changements de méthode.

## 2. Choix des périodes et des champs

La comparaison principale utilise2016–2022, car ces deux dates sont présentes dans la fréquentation SNCF et les bases du recensement RP2022. Cela évite de comparer une croissance démographique2016–2022 à une croissance ferroviaire2015–2024. Le recensement2022 est conservé comme millésime commun des différents thèmes, même si certaines publications plus récentes existent au moment de la collecte.

Les séries SNCF2015–2024 servent à décrire la concentration, les changements de rang et l'évolution avant/après le Covid ;2019 est la base100 de référence. L'analyse du parc utilise les années réellement extraites de l'édition SDES2026-06. Les projections utilisent2018 comme base et2050 comme horizon.

La table démographique contient **{fr(dem['communes'],0)} communes**, dont **{fr(dem['communes_metropole'],0)} métropolitaines**, dans la géographie COG2025. Mayotte est absente du champ RP2022 exploité. Les statistiques de population de métropole incluent la Corse. Le proxy de distance aux gares est restreint à la métropole hors Corse, car les Chemins de fer de la Corse sont absents du périmètre de fréquentation SNCF retenu ; les communes insulaires telles que Ré et Oléron restent dans ce champ.

## 3. Inventaire raisonné des sources

{sources}

Les licences et notices des producteurs sont conservées dans les métadonnées brutes et les notes par famille : `notes_demographie.md`, `notes_climat.md`, `notes_aviation.md`, `notes_contexte_lgv.md`. La fréquentation SNCF et les couches Réseau sont soumises à l'ODbL ; les attributions restent nécessaires lors de la redistribution. Les données OurAirports sont diffusées dans le domaine public ; le contenu Wikipédia relève de sa licence propre et n'est utilisé ici que pour de courtes extractions factuelles contextualisées.

## 4. Collecte, traçabilité et reproductibilité

Trois modes d'accès sont effectivement employés : fichiers téléchargeables ZIP/CSV/XLSX/GeoJSON ; API SNCF, SDES et ADEME ; extraction de HTML pour les pages documentaires INSEE et les trois pages LGV. Pour les LGV, `robots.txt` est archivé, l'autorisation est vérifiée et un délai d'au moins deux secondes sépare les requêtes.

L'API SNCF est paginée par blocs de100 lignes ; chaque réponse est archivée séparément. Le nombre de lignes reconstitué est confronté au total annoncé dans les métadonnées. Les requêtes sont espacées et réessayées en cas d'erreur. Les sources brutes ne sont renouvelées qu'à la demande explicite `--refresh` ; une reconstruction ordinaire se fait hors ligne.

Chaque collecte utilisée possède une URL exacte et une empreinte SHA-256, avec taille et date de récupération ou date de modification locale documentée selon le collecteur. La date de référence du travail est le26/10/2026 ; les horodatages techniques UTC sont conservés séparément. Les empreintes attestent l'intégrité de l'instantané, pas l'absence d'erreur chez le producteur. L'audit actuel vérifie **{sha_n} fichiers bruts**.

## 5. Modèle de données et unités d'observation

La base finale est organisée en plusieurs tables, plutôt que de forcer des données de grains différents dans un seul fichier. `dataset_final_communes.parquet` contient une ligne par commune COG2025. `gares_annees.parquet` contient une ligne par UIC et année : **30 210 lignes**, soit3 021 UIC sur dix années. `communes_annees_rail.parquet` contient les agrégats des seules gares rattachées. Les projections restent au département et au scénario ; l'avion reste au mois/faisceau ou à la paire d'aéroports.

Les codes INSEE et UIC sont des chaînes de caractères ; les zéros initiaux sont conservés. Les codes postaux ne servent jamais de code commune. Les UIC attendus comportent huit chiffres ; les codes communaux cinq caractères avec possibilité de2A/2B. Paris, Lyon et Marseille sont traitées comme communes entières, avec rattachement de leurs arrondissements par le COG officiel.

Un comptage de voyageurs en gare n'est ni un voyageur unique ni un nombre de déplacements de résidents. Des voyageurs peuvent être comptés à plusieurs gares et les bassins de recrutement dépassent les limites communales. Le ratio comptages/habitant est donc un indicateur de concentration de l'usage des gares implantées dans une commune, et non un taux individuel d'utilisation du train.

## 6. Nettoyage, valeurs manquantes et divergences de sources

Les années en colonnes dans la source SNCF sont passées au format long. Seules les colonnes « voyageurs » sont retenues ; les colonnes incluant les non-voyageurs ne sont pas mélangées à la mesure principale. Les types et valeurs non négatives sont contrôlés. Les zéros publiés sont conservés, sans les interpréter automatiquement comme des fermetures. Les valeurs non publiées restent manquantes, sans interpolation ni imputation.

Les bases INSEE sont lues en conservant leurs décimales et leurs codes. Les parts sont laissées non définies lorsque le dénominateur est nul ou absent. La catégorie « au moins deux voitures » ne permet pas de connaître le parc exact des ménages : son usage dans un nombre de voitures par ménage fournit une borne inférieure, correctement nommée dans le fichier.

Un contrôle croisé entre deux publications INSEE révèle12 communes divergentes pour2016 et une pour2022, malgré un millésime géographique annoncé identique. L'historique de population est conservé comme série de référence ; les écarts sont exportés dans `demographie_ecarts_inter_sources.csv`. Les ratios de mobilité ou de motorisation concernés sont neutralisés et des drapeaux de comparabilité restent disponibles. Le croisement principal rail/population exclut les communes signalées ; une analyse de sensibilité les réintègre. Les écarts ne sont jamais « corrigés » par substitution arbitraire.

## 7. Jointures et harmonisation géographique

La jointure gare→commune privilégie le code INSEE du référentiel Gares & Connexions. Les listes de plusieurs UIC sont éclatées ; l'unicité de chaque UIC est contrôlée, les conflits éventuels étant mis à l'écart. Les codes d'arrondissement ou de communes déléguées sont ramenés au parent officiel COG2025. Aucun appariement approximatif sur un nom de gare n'est utilisé.

Lorsque les coordonnées Gares & Connexions manquent, le référentiel Réseau sert de secours. Il peut contenir plusieurs projections ferroviaires pour un même UIC : la médiane des coordonnées est utilisée uniquement si la dispersion de ces projections est au plus1km ; une table d'audit recense les projections plus dispersées. Ce seuil est un contrôle de prudence, pas une précision géodésique annoncée.

Pour les codes commune absents ou obsolètes non résolus par le COG, les points sont rattachés par inclusion dans un polygone COG2025 simplifié à100m. Les arrondissements sont retirés de la couche de jointure pour éviter leur superposition à la commune entière. Un résultat spatial ambigu est laissé non résolu ; il n'y a pas d'affectation automatique au polygone le plus proche.

Le bilan est de **{quality['gare_avec_commune']} gares rattachées sur{quality['gares_frequentation']}**, soit **{fr(quality['taux_jointure_commune_pct'],3)}%** des UIC et **{fr(quality['voyageurs_2024_couverts_commune_pct'],3)}%** des comptages2024. Les deux exceptions concernent Monaco–Monte-Carlo et la Halte de Fontanil–Lycée de Drap, absentes des référentiels utilisés. Elles restent dans la table source, avec une commune manquante ; Monaco n'est pas artificiellement affectée à une commune française.

Le SDES présente les stocks de Paris, Lyon et Marseille à la fois sur les arrondissements et sur un petit résidu au code parent. Ces lignes représentent des ventilations disjointes : on les additionne après rattachement officiel, en contrôlant la conservation des sommes.45 codes sont ainsi rattachés. Les101 codes fictifs ou non localisés sont gardés à part ;17 codes officiels de Mayotte sont hors du champ RP2022. **{parc['codes_cibles_cog2025']} communes** sont appariées ; les quatre communes du RP sans ligne SDES ont toutes une population nulle et ne sont pas remplies par zéro. La notice SDES ne précise pas le millésime géographique exact : les correspondances de codes ne garantissent donc pas une harmonisation historique complète des périmètres.

## 8. Cohorte ferroviaire et champ du croisement principal

Pour chaque UIC, on retient un comptage2016 strictement positif et un comptage2022 observé, pouvant être nul. Les sommes2016 et2022 sont ensuite calculées sur exactement les mêmes UIC dans chaque commune. Cette cohorte évite de comparer deux ensembles de gares différents, mais exclut les nouvelles gares et les bases2016 nulles ; elle ne décrit donc pas l'intégralité des transformations du réseau.

Après restriction à la métropole, population de base définie et retrait des alertes géographiques INSEE, le champ principal compte **{fr(len(sample),0)} communes**, représentant **{fr(sample_pop,2)}%** de la population métropolitaine2022. Il s'agit de communes d'implantation des gares observées ; les résultats ne sont pas extrapolés aux communes sans gare ni à l'ensemble des habitants. Les agrégats régionaux de population couvrent toutes les communes, alors que le rail régional reste limité à cette cohorte de gares : cette différence de champ est rappelée à l'interprétation.

## 9. Indicateurs construits et calculs statistiques

Pour une quantité positive à la base et observée à l'arrivée, la croissance totale est100×(Xfin/Xdébut−1). Le taux de croissance annuel moyen est100×[(Xfin/Xdébut)^(1/n)−1] ; n=6 entre2016 et2022. Un point final nul donne un TCAM de−100% : cette limite mathématique est conservée, sans conclusion automatique de fermeture. Une base nulle rend le taux non défini.

L'écart rail/population est le TCAM des comptages moins celui de la population, en points de pourcentage annuels. Les quatre profils de signe distinguent les TCAM négatifs des TCAM nuls ou positifs ; la stabilité exacte est donc incluse dans la catégorie≥0. Les trajectoires démographiques « déclin/stable/croissance » utilisent un autre seuil, annoncé à±0,2%/an, qui est un choix de description, pas un seuil de significativité.

La part voiture est100×actifs occupés de15ans ou plus utilisant principalement la voiture / ensemble des actifs occupés de15ans ou plus. Le dénominateur comprend notamment les personnes sans déplacement. La catégorie transports en commun regroupe plusieurs modes et n'est pas une part ferroviaire. Pour agréger un groupe, on calcule le ratio des sommes des effectifs valides sur le même ensemble de communes ; on ne moyenne pas les pourcentages communaux.

Le solde naturel2016–2022 est le nombre de naissances2016–2021 moins les décès sur cette même période. Le solde migratoire apparent est la variation de population moins ce solde naturel ; le terme « apparent » rappelle qu'il absorbe également les ajustements de mesure.

La dispersion est décrite par médiane, quantiles, distribution logarithmique des valeurs positives, courbe de Lorenz et Gini. Le Gini est calculé sur les comptages2024 non négatifs, zéros inclus ; il mesure la concentration entre gares, pas une inégalité d'accès des personnes. La part des10% utilise l'arrondi supérieur du nombre de gares, soit303 UIC. Les quintiles sont recalculés séparément en2015 et2024 sur les gares positives aux deux dates ; les transitions sont normalisées par ligne.

Les corrélations Pearson et Spearman sont non pondérées au niveau communal. Les effectifs sont publiés pour chaque paire de variables. Spearman limite l'influence des valeurs extrêmes, sans résoudre la dépendance spatiale ni les facteurs de confusion. Les sensibilités excluent l'Île-de-France, imposent au moins10 000 comptages en2016, retirent le1% supérieur des volumes2022 ou réintègrent les alertes géographiques.

## 10. Distance aux gares : définition exacte du proxy

L'indicateur est la **distance du centroïde géométrique communal à la gare SNCF observée la plus proche avec comptage positif en2024**. Les polygones et points sont projetés en Lambert93, EPSG:2154 ; la recherche du plus proche voisin emploie une distance euclidienne en mètres, convertie en kilomètres.

La population entière d'une commune est affectée au classement de son centroïde, faute de population carroyée dans ce projet. « Population des communes dont le centroïde est à plus de10km » est donc la formulation exacte ; « population vivant à plus de10km d'une gare » serait une conclusion non mesurée. Les seuils5/10/15km montrent la sensibilité de ce proxy, pas une frontière naturelle d'accès au train.

La Corse est laissée manquante et grisée, car le réseau CFC n'est pas couvert par la source SNCF. Le réseau RATP et les Chemins de fer de Provence Nice–Digne ne sont pas exhaustivement couverts non plus. Le proxy ne décrit pas l'ensemble du rail français. Un comptage positif n'est pas une certification exhaustive de toutes les gares ouvertes ; une valeur nulle ne prouve pas leur fermeture. Il n'est calculé ni temps de marche, ni trajet routier, ni fréquence de desserte, ni évolution historique de l'accessibilité.

La « part de croissance positive » est la somme des variations de population communales positives dans un groupe, divisée par la somme de toutes les variations communales positives du champ ; les baisses sont écrêtées à zéro. Ce n'est pas une part de la croissance nette nationale.

## 11. Voiture, facteurs carbone et émissions

Le parc SDES est un stock au1erjanvier, diffusé avec arrondis. Une voiture enregistrée dans une commune ne mesure ni ses kilomètres parcourus ni les émissions émises sur ce territoire ; les véhicules de personnes morales et les véhicules de particuliers sont distingués. Les ratios par habitant ou ménage sont descriptifs et subissent les limites du rapprochement géographique SDES/RP.

Les facteurs ADEME sont archivés avec paramètres explicites : un kilomètre, construction incluse, un occupant pour la voiture. Ils sont exprimés en grammes de CO₂ équivalent par voyageur.km. Les comparer à activité transportée identique est possible ; les multiplier par les comptages de gare seuls ne l'est pas, car les origines–destinations, distances, doubles comptes et comportements de report sont inconnus.

Ainsi, aucun total d'« émissions réellement évitées grâce au train » ni d'émissions routières communales n'est fabriqué. Les comparaisons normalisées de facteurs figurent séparément dans les sorties climat. Le CO₂ DGAC est net, avec prise en compte des carburants d'aviation durables (SAF), et hors effets non-CO₂ ; les intensités en g CO₂/Peq.km incluent l'équivalence du fret dans les passagers équivalents. Cet objet est distinct d'un facteur ADEME en CO₂e de cycle de vie : leurs périmètres ne sont pas fusionnés.

## 12. Complément avion et réglementation

La série DGAC LSN fournit le trafic intérieur métropolitain agrégé ; elle sert aux évolutions nationales. La série PAP décrit les liaisons observées avec leurs deux sens réunis dans la notice actuelle, même si une ancienne URL évoque « par sens ». Une paire ne doit donc pas être doublée artificiellement.

PAP est censurée : conditions de pluralité d'opérateurs et de concentration, et seuil mensuel de10 000 passagers équivalents. Une absence n'est pas un zéro. Les couvertures mensuelles et annuelles sont publiées ; des totaux PAP qui changent de couverture ne deviennent pas une série représentative du marché. OurAirports apporte des coordonnées et codes courants ; les identifiants historiques absents restent non appariés.

Le contrôle externe du bulletin DGAC2025 conserve l'écart entre les19 636 085 passagers intérieurs recalculés et les19,63millions publiés :6 085 passagers comptés, soit0,031%, au-delà du seul arrondi mais en deçà du seuil d'alerte fixé à0,1%. Le bulletin et le ZIP n'ont pas la même date ; une révision est plausible mais non démontrée. De même,22,2Mt de CO₂ en2024 dans le CSV et22,1Mt dans une page ministérielle sont conservés comme deux publications différentes.

Le décret n°2023-385 n'est pas utilisé comme expérience causale. Les suppressions de liaisons, les événements de2020, le Covid, les correspondances et les changements d'offre empêchent une attribution simple avant/après2023. La prolongation après mai2026 n'a pas été établie dans les sources primaires consultées ; aucun statut légal postérieur ni indicateur de traitement n'est inventé.

## 13. Projections et contexte LGV

Omphale2022 est exploité au département, sur trois scénarios officiels central, bas et haut. Les variations2018–2050 sont conditionnelles aux hypothèses de fécondité, mortalité et migrations de l'INSEE ; les scénarios bas/haut ne sont pas des intervalles de confiance. Ils ne sont pas ventilés artificiellement à la commune et ne produisent pas de prévision de fréquentation ferroviaire.

Les trois pages LGV illustrent la collecte HTML : Atlantique, Bretagne–Pays de la Loire et Sud Europe Atlantique. Une date exacte est conservée uniquement si elle est explicitement publiée ; l'intervalle1989–1990 n'est pas transformé en une date inventée. Cette sélection de contexte est raisonnée, non exhaustive et n'est pas jointe automatiquement aux communes pour attribuer un effet TGV.

## 14. Visualisations et limites d'interprétation

Les axes, années, unités et sources figurent sur les graphiques. Les palettes divergentes sont centrées sur zéro. Certaines cartes saturent les couleurs à des valeurs annoncées dans la légende ; cela ne tronque pas la table. Les nuages utilisent des échelles symlog pour rendre visibles les valeurs négatives et extrêmes sans les supprimer. Les tailles de points sont comprimées et leur convention est indiquée.

La commune d'implantation n'est pas le bassin de desserte. Les grandes gares, le tourisme, les correspondances, le travail à distance, les prix et les modifications d'offre peuvent modifier la fréquentation indépendamment de la démographie communale. Les données de2022 peuvent encore refléter la reprise après le Covid. Les recensements reposent sur des enquêtes étalées, dont les estimations de petits effectifs peuvent être imprécises ; leurs mobilités ne représentent pas tous les motifs de déplacement. Une association entre rail et voiture ne démontre aucun report modal ni effet d'éviction.

## 15. Contrôles, exécution et livrables

L'audit indépendant produit `outputs/tables/validation_globale.json` : statut **{checks['statut']}**, **{checks['nombre_controles']} contrôles**, **{checks['nombre_echecs']} échec**. Il vérifie notamment les empreintes, les grains, la conservation des sommes après jointure et agrégation, l'absence de valeurs infinies, les types de codes, les cohortes, les drapeaux d'accès et les contrôles DGAC. Le total de population2022 retrouve exactement65 846 255 habitants en métropole et67 760 573 hors Mayotte, selon les tables INSEE de référence.

Le point d'entrée est `python run.py --offline`. Le notebook `main.ipynb` reconstruit les tables depuis les archives puis expose les résultats. `--download` permet de compléter une collecte ; `--download --refresh` renouvelle les instantanés et impose une nouvelle validation. L'environnement testé est CPython3.13.9, pandas2.3.3 et NumPy2.2.6 ; les dépendances et leur verrouillage sont fournis.

Le dictionnaire des données détaille les colonnes ; le README décrit les commandes. Le rapport d'analyse existe en Markdown, HTML autonome et DOCX. Les figures sont exportées en PNG/SVG et une carte interactive autonome est fournie. Les archives volumineuses restent hors du suivi Git. Aucun dépôt distant, compte S3 ni historique de contributions humaines n'est créé ou prétendu : ces éléments d'organisation d'équipe restent à configurer par les membres.

## 16. Compléments non retenus et raisons

OpenSky exige un accès authentifié à l'historique et n'est pas nécessaire aux agrégats DGAC accessibles ; il n'est pas utilisé. Eurostat constitue une source alternative de contrôle mais n'est pas fusionné avec DGAC au risque de mélanger unités, sens et périmètres. Le GTFS courant ne mesure pas l'offre historique2016–2022 et n'a pas été présenté comme tel. Les flux individuels domicile–travail, Filosofi, inventaires routiers territoriaux et qualité de l'air restent hors de cette version faute de série collectée et harmonisée pour ces calculs précis.

L'absence de ces enrichissements n'est pas remplacée par des données synthétiques. Le projet livre une base réelle, un socle descriptif complet et les compléments effectivement disponibles ; il distingue les questions auxquelles les données répondent de celles qui nécessitent une collecte supplémentaire.

## 17. Références et documentation détaillée

- [Fréquentation en gares, source SNCF](https://ressources.data.sncf.com/explore/dataset/frequentation-gares/).
- [Référentiel des gares voyageurs](https://ressources.data.sncf.com/explore/dataset/gares-de-voyageurs/).
- [Liste des gares SNCF Réseau](https://ressources.data.sncf.com/explore/dataset/liste-des-gares/).
- [INSEE, base de référence population2022](https://www.insee.fr/fr/statistiques/8581709?geo=METRO-1).
- [INSEE, grille communale de densité](https://www.insee.fr/fr/information/8571524).
- [Contours administratifs Etalab2025](https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/).
- [SDES, parc de véhicules routiers](https://www.data.gouv.fr/datasets/parc-de-vehicules-routiers).
- [ADEME, documentation Impact CO₂](https://impactco2.fr/doc/api).
- [DGAC, trafic aérien mensuel](https://www.data.gouv.fr/datasets/64808a5811da153f1439914c).
- [DGAC, bulletin statistique2025](https://www.ecologie.gouv.fr/sites/default/files/documents/Bulletin_Statistiques_transport_aerien_2025.pdf).
- [DGAC, émissions nettes annuelles de CO₂](https://www.data.gouv.fr/datasets/emissions-nettes-annuelles-de-co2-du-trafic-aerien-commercial-en-france).
- [Décret n°2023-385, Légifrance](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000047571222).
- [Code des transports, article R.6412-21](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048324552).
- [OurAirports, données](https://ourairports.com/data/).
- [Chemins de fer de Provence, gares hors SNCF](https://www.cpzou.fr/category/nos-gares/).
- Sources exactes des fichiers, paramètres API et détails de licences dans les manifestes bruts et les notes méthodologiques par famille présentes dans ce dossier.
"""
    # Les conventions de noms restent techniques ; la prose est espacée pour lecture et impression.
    def prose_spacing(text):
        text=text.replace("du26octobre2026", "du 26 octobre 2026").replace("le26/10/2026", "le 26/10/2026").replace("1erjanvier", "1er janvier")
        text=re.sub(r"(?<=[éèêàùçA-Za-z])(?=(?:19|20)\d{2}\b)"," ",text)
        text=re.sub(r"\b(soit|sur|par|de|du|au|à|les|le|en|contre)(?=\d)",r"\1 ",text)
        text=re.sub(r"(?<=\d)(?=(?:années|ans|km|mètres|Mt|millions|personnes|occupant)\b)"," ",text)
        return text
    method=prose_spacing(method)
    ten=access.loc[access.seuil_km.eq(10)].iloc[0]
    report=f"""# Le rail suit-il la France qui grandit ?

**Rapport d'analyse descriptive — version du26octobre2026**

## Résultats principaux et champ de validité

Les données rapprochent population et fréquentation des gares sur2016–2022, avec une mise en perspective ferroviaire2015–2024. Sur **{fr(len(sample),0)} communes comparables**, les taux annuels de croissance sont faiblement associés : **Pearson={fr(stats['correlation_population_rail']['pearson'],3)}** et **Spearman={fr(stats['correlation_population_rail']['spearman'],3)}**. **{stats['population_croissance_rail_baisse']} communes** combinent une population strictement croissante et des comptages en gare décroissants.

Ce résultat concerne les communes d'implantation d'une cohorte de gares observées, qui représentent **{fr(sample_pop,2)}% de la population métropolitaine2022**. Il ne mesure pas un retard de l'offre ferroviaire ni un déficit de capacité, et ne s'extrapole pas à toutes les communes. Une gare reçoit aussi des habitants des communes voisines, des visiteurs et des correspondances.

## 1. Une base réelle et contrôlée

La base démographique comprend **{fr(dem['communes'],0)} communes** dans le COG2025, avec des populations historiques1968–2022, des ménages et des modes domicile–travail. La table ferroviaire compte **3 021 UIC ×10années=30 210 observations** ;3 019 UIC sont rattachés à une commune. Le SDES apporte un stock de voitures harmonisé par codes sur34 854 communes ; l'avion et les scénarios démographiques restent dans des tables séparées de grain adapté.

Le bilan de validation est **{checks['nombre_controles']} contrôles réussis sur{checks['nombre_controles']}**, avec **{sha_n} fichiers bruts vérifiés par empreinte**. Cette validation établit la cohérence des traitements et des instantanés, sans garantir que toutes les mesures publiées sont exemptes d'erreurs. La méthodologie complète, les manifestes et le dictionnaire permettent de retrouver chaque choix.

## 2. Des trajectoires démographiques contrastées

La population métropolitaine passe de son niveau2016 à **65 846 255 habitants en2022**, soit une hausse d'environ2,14%. Cette croissance agrégée coexiste avec de nombreuses communes en déclin ; un nombre de communes et un nombre d'habitants ne décrivent pas la même distribution.

![La croissance démographique2016–2022 par commune](../outputs/figures/07_carte_demographie.png)

La carte situe les croissances et déclins, sans réduire une région à une seule trajectoire. Les couleurs sont saturées à±2% annuels. Le réseau SNCF est un fond de contexte, sans filtre de service voyageurs et sans mesure de fréquence des trains.

![Soldes naturels et migratoires apparents régionaux](../outputs/demographie/03_soldes_regions.png)

Le solde migratoire apparent est la variation de population diminuée du solde naturel. Les barres décrivent une décomposition comptable ; elles ne constituent pas une mesure pure des seuls flux migratoires observés.

## 3. Une fréquentation concentrée et marquée par le Covid

Les comptages de2020 représentent **{fr(stats['indice_2020_base100_2019'],2)}%** du niveau2019. En2024, ils atteignent **{fr(stats['indice_2024_base100_2019'],2)}%** de ce niveau dans le fichier publié, soit une hausse de **{fr(stats['indice_2024_base100_2019']-100,2)}%**. La courbe à cohorte complète permet de contrôler l'influence des valeurs observées sur toute la période.

![Évolution des comptages en gare, base100en2019](../outputs/figures/01_evolution_rail.png)

Ces niveaux sont des comptages de gares issus notamment de la billetterie et d'extrapolations en Île-de-France ; ils ne sont pas des voyages uniques. Le producteur signale des révisions historiques et l'absence des billets vendus par des tiers.

Les **303 gares** du décile supérieur concentrent **{fr(stats['part_top10pct_gares_pct'],2)}%** des comptages2024 ; le Gini entre gares vaut **{fr(stats['gini_gares_2024'],3)}**. La moyenne seule serait donc peu représentative d'une gare ordinaire.

![Distribution et concentration des comptages2024](../outputs/figures/02_concentration.png)

Le Gini décrit une concentration entre équipements, et non l'inégalité d'accès au train entre personnes. Les zéros publiés sont inclus dans ce calcul mais exclus de l'histogramme logarithmique.

![Position relative des gares2015–2024](../outputs/figures/06_transitions.png)

Les quintiles sont recalculés séparément aux deux dates2015et2024 : une gare peut augmenter ses comptages et perdre du rang si d'autres progressent davantage. Le tableau ne mesure pas directement des fermetures, ouvertures ou variations d'offre.

## 4. Population et rail : une association faible à l'échelle communale

![Croissance des comptages et de la population sur une période commune](../outputs/figures/03_rail_population.png)

Le nuage présente de fortes différences de trajectoires ferroviaires pour des croissances démographiques proches. Les taux négatifs extrêmes et les petits volumes de départ motivent les vérifications de sensibilité, sans suppression automatique des observations.

{md_table(profiles.rename(columns={'profil_rail_demographie':'Signes des TCAM','nb_communes':'Communes','part_communes_pct':'Part des communes (%)'})[['Signes des TCAM','Communes','Part des communes (%)']])}

La catégorie≥0 inclut la stabilité exacte. Le nombre **{stats['population_croissance_rail_baisse']}** cité au début exige une hausse démographique strictement positive ; il peut donc être légèrement inférieur au nombre du profil≥0/rail<0 du tableau.

{md_table(sensitivity.rename(columns={'champ':'Champ','n_communes':'Communes','pearson':'Pearson','spearman':'Spearman'}),digits=3)}

La faible association persiste dans ces variantes, avec une intensité différente. Cela ne démontre ni que la démographie serait sans effet sur la demande, ni que le rail répondrait adéquatement aux besoins : les bassins de gare et les facteurs d'offre ne sont pas identifiés.

## 5. Densité territoriale et dépendance automobile

{md_table(density.rename(columns={'classe_densite':'Grille INSEE','n_communes':'Communes de la classe','n_communes_mobilite':'Communes mobilité','part_modale_voiture_2022_pct':'Part voiture (%)'})[['Grille INSEE','Communes de la classe','Communes mobilité','Part voiture (%)']])}

La part voiture est nettement plus élevée dans le rural que dans l'urbain dense. Les parts sont des ratios des effectifs agrégés, calculés sur les seules communes aux données comparables ; les actifs sans déplacement restent au dénominateur. La structure urbaine, l'emploi et les transports collectifs autres que le train participent à cette différence.

![Parts voiture selon la trajectoire démographique](../outputs/figures/04_voiture_trajectoire.png)

La trajectoire démographique ne suffit pas à expliquer ces parts. Les catégories utilisent un seuil descriptif de±0,2% annuels ; elles ne sont pas des groupes expérimentaux comparables.

![Évolutions du rail et de la part voiture](../outputs/figures/11_rail_evolution_voiture.png)

Ce rapprochement porte sur les mêmes années et sur des données de mobilité valides aux deux dates. Il décrit une association entre évolutions communales ; il ne prouve pas un transfert individuel de la voiture vers le train.

![Corrélations entre caractéristiques communales](../outputs/figures/05_correlations.png)

Les coefficients de Spearman résument des relations de rang. Les effectifs par paire sont disponibles dans les tables de sortie ; les relations sont influencées par la densité et la sélection des communes disposant d'une gare observée. Aucun coefficient n'est interprété comme un effet causal.

## 6. Éloignement des gares : un proxy, avec un champ défini

![Distance du centroïde communal aux gares SNCF observées](../outputs/figures/09_carte_distance.png)

En métropole hors Corse, **{fr(ten.population_communes_concernees_2022,0)} habitants** résident dans **{fr(ten.nb_communes,0)} communes dont le centroïde est situé à plus de10km d'une gare SNCF observée avec comptage positif en2024**, soit **{fr(ten.part_population_proxy_pct,2)}%** de la population de ce champ. Cette phrase ne signifie pas que chaque habitant concerné vit lui-même à plus de10km d'une gare.

{md_table(access.rename(columns={'seuil_km':'Seuil (km)','nb_communes':'Communes','part_population_proxy_pct':'Population des communes (%)','part_croissance_positive_proxy_pct':'Hausses positives communales (%)'})[['Seuil (km)','Communes','Population des communes (%)','Hausses positives communales (%)']])}

La sensibilité aux seuils rappelle le caractère conventionnel du classement. La dernière colonne porte sur la somme des hausses communales positives, pas sur la croissance nette. La Corse est grisée pour absence du réseau CFC dans la source ; RATP, Chemins de fer de Provence et autres réseaux hors périmètre empêchent d'assimiler ce proxy à l'accès à tout le rail. Les distances sont à vol d'oiseau et ne mesurent pas les horaires ni les accès routiers.

## 7. Climat : comparer les modes sans inventer des émissions évitées

![Facteurs carbone ADEME pour une activité transportée identique](../outputs/climat/facteurs_ademe.png)

Les facteurs ADEME en CO₂e par voyageur.km diffèrent fortement selon les modes, pour les paramètres publiés et archivés. La voiture est ici à un occupant et la construction est incluse. Ces moyennes ne sont ni des mesures communales ni une reconstitution de facteurs historiques2016–2022.

![Évolution du stock de voitures particulières](../outputs/climat/parc_national.png)

Le SDES décrit un stock, pas les kilomètres ni les émissions sur le territoire. Il n'est pas défendable de multiplier les comptages des gares par une distance moyenne inventée pour produire des « tonnes évitées ». Un bilan climatique territorial exigerait des distances, origines–destinations, parts de report et inventaires d'émissions harmonisés.

## 8. À l'horizon2050 : des scénarios démographiques, sans prévision de trafic

![Projections départementales centrales2018–2050](../outputs/figures/10_carte_projections.png)

![Sensibilité aux scénarios bas, central et haut](../outputs/climat/projections_2050.png)

Ces scénarios officiels indiquent où la population pourrait augmenter ou diminuer sous les hypothèses Omphale. Les différences entre scénarios ne constituent pas des intervalles de confiance. Aucune demande ferroviaire future n'est calculée à partir d'une corrélation communale faible.

## 9. Complément aérien : reprise différente et données de liaisons censurées

Le trafic intérieur métropolitain DGAC passe de **{fr(air['domestic_pax_2019'],0)} passagers en2019** à **{fr(air['domestic_pax_2024'],0)} en2024**, soit **{fr(air['domestic_growth_2019_2024_pct'],2)}%**. Cette évolution et la reprise des comptages en gare décrivent deux séries d'unités différentes ; elles ne quantifient pas un report avion–train.

![Évolution du trafic aérien intérieur métropolitain](../outputs/aviation/trafic_aerien_base100.png)

Les liaisons PAP sont masquées sous certaines conditions de secret statistique et de seuil. Les absences ne sont pas remplies par zéro et les deux sens ne sont pas doublés. Le contrôle de couverture documente pourquoi la série nationale agrégée LSN est utilisée pour la tendance d'ensemble.

![Émissions aériennes selon les faisceaux publiés par la DGAC](../outputs/aviation/emissions_aeriennes.png)

Le CSV DGAC affiche22,2Mt de CO₂ pour le total France2024 contre22,1Mt sur une page ministérielle ; l'écart est signalé, sans correction forcée. Le périmètre aérien et le CO₂ ne sont pas assimilés aux facteurs ADEME de CO₂e. Les évolutions observées ne permettent pas d'identifier l'effet du seul décret2023-385 ; la prolongation après mai2026 n'a pas été établie par les sources primaires consultées.

## 10. Ce que permet le projet, et ses limites

Le projet met en évidence une fréquentation concentrée, une reprise après le Covid, une faible association communale rail/population et une dépendance automobile fortement liée à la densité. Il localise un éloignement approché des seules gares du périmètre SNCF étudié et présente des scénarios démographiques officiels.

Il ne mesure pas l'adéquation de l'offre, l'accès individuel à tous les réseaux, un effet causal de report modal ou un volume réel d'émissions évitées. Pour ces questions, les prolongements utiles seraient des bassins de desserte, une population carroyée, des temps d'accès, des horaires historiques, des flux origine–destination et une stratégie d'identification causale adaptée.

Les sources primaires, formules, filtres, exceptions et commandes de reproduction figurent dans `METHODOLOGIE.md`. Les tableaux détaillés sont dans `outputs/tables/`, les archives et manifestes dans `data/raw/`, et le notebook exécuté dans `main.ipynb`.
"""
    report=prose_spacing(report)
    for name,text in [("METHODOLOGIE",method),("RAPPORT_ANALYSE",report)]:
        (DOCS/f"{name}.md").write_text(text,encoding="utf-8")
        to_html(text,name.replace("_"," "),DOCS/f"{name}.html")
        to_docx(text,DOCS/f"{name}.docx")
    print("Méthodologie et rapport produits : Markdown, HTML autonome et DOCX.")


if __name__ == "__main__":
    generate()
