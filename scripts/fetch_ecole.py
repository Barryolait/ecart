"""Couche école, à partir de data.education.gouv.fr (Licence Ouverte), sans clé.

1. IPS des collèges (indice de position sociale, rentrées 2023 et suivantes) joint à
l'annuaire de l'éducation par le code UAI pour la localisation et l'éducation prioritaire.
Les moyennes départementales et nationales public / privé sont celles publiées par le
ministère ; l'écart privé - public est calculé ici.
Les séries 2016-2021 ne sont pas reprises : la méthode de l'IPS a changé en 2022.
2. Effectifs des écoles publiques depuis 2009 : nombre d'écoles, d'élèves, de classes,
et élèves par classe (calculé ici : élèves / classes), agrégés par l'API du ministère.

Les fichiers ne sont réécrits que si les données changent.
Sorties : data/ecole_colleges.json (carte), data/series/ecole.json (frise, format commun)"""
import datetime, gzip, json, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_MAP = ROOT / "data/ecole_colleges.json"
OUT_SERIE = ROOT / "data/series/ecole.json"
API = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
PAGE = "https://data.education.gouv.fr/explore/dataset/"
IPS = "fr-en-ips-colleges-ap2023"
EFFECTIFS = "fr-en-ecoles-effectifs-nb_classes"
ANNUAIRE = "fr-en-annuaire-education"

def get_json(url):
    # Le serveur répond parfois en gzip même sans le demander ; urllib ne décompresse pas.
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return json.loads(gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body)

def export(dataset, select=None):
    return get_json(f"{API}{dataset}/exports/json" + (f"?select={select}" if select else ""))

def query(dataset, params):
    return get_json(f"{API}{dataset}/records?" + urllib.parse.urlencode(params))["results"]

def rentree_mois(r):  # "2025-2026" -> "2025-09" : la rentrée sur l'axe du temps
    return r[:4] + "-09"

def write_if_changed(path, doc, key):
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if all(old.get(k) == doc.get(k) for k in key):
            return False
    doc["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return True

def ips_colleges():
    rows = export(IPS)
    annu = {a["identifiant_de_l_etablissement"]: a for a in export(
        ANNUAIRE, "identifiant_de_l_etablissement,latitude,longitude,appartenance_education_prioritaire")}
    rentrees = sorted({r["rentree_scolaire"] for r in rows})
    k = {r: i for i, r in enumerate(rentrees)}
    colleges, deps, nat, sans_geo = {}, {}, {}, set()
    for r in rows:
        i, dep = k[r["rentree_scolaire"]], r["code_du_departement"]
        nat.setdefault(i, (r["ips_national_public"], r["ips_national_prive"], r["ips_national"]))
        if len(dep) != 2:  # métropole et Corse (2A, 2B) sur la carte ; l'outre-mer reste dans les moyennes nationales
            continue
        d = deps.setdefault(dep, {"pu": [None] * len(rentrees), "pr": [None] * len(rentrees)})
        d["pu"][i], d["pr"][i] = r["ips_departemental_public"], r["ips_departemental_prive"]
        a = annu.get(r["uai"])
        if not a or a.get("latitude") is None:
            sans_geo.add(r["uai"])
            continue
        c = colleges.setdefault(r["uai"], [
            r["uai"], r["nom_de_l_etablissement"], r["nom_de_la_commune"], dep,
            "pu" if r["secteur"] == "public" else "pr", a.get("appartenance_education_prioritaire") or "",
            round(a["longitude"], 4), round(a["latitude"], 4), [None] * len(rentrees), [None] * len(rentrees)])
        c[8][i], c[9][i] = r["ips"], r["ecart_type_de_l_ips"]
    source = {"label": "Ministère de l'Éducation nationale, IPS des collèges", "url": PAGE + IPS + "/"}
    methode = ("L'IPS résume la position sociale des élèves à partir de la profession de leurs représentants légaux : "
               "plus il est élevé, plus le milieu est favorisé. Moyennes départementales et nationales publiées par le ministère ; "
               "l'écart privé - public est calculé par ÉCART.")
    limites = ("Profession des parents, pas leurs revenus. Une moyenne par collège masque la diversité des élèves (écart-type affiché). "
               "Privé hors contrat absent. Méthode modifiée en 2022 : les années 2016-2021 ne sont pas comparables et ne sont pas reprises.")
    doc_map = {"source": source, "annuaire": PAGE + ANNUAIRE + "/", "methode": methode, "limites": limites,
               "rentrees": rentrees, "sans_coordonnees": len(sans_geo), "ips_national": [nat[i][2] for i in range(len(rentrees))],
               "colonnes": ["uai", "nom", "commune", "dep", "secteur", "education_prioritaire", "lon", "lat", "ips", "ecart_type"],
               "colleges": sorted(colleges.values()), "deps": deps}
    lignes = [
        {"id": "ips_public", "groupe": "ips", "unite": "indice", "label": "IPS moyen, collèges publics", "url": source["url"], "calcul": None,
         "points": [[rentree_mois(r), nat[i][0]] for i, r in enumerate(rentrees)]},
        {"id": "ips_prive", "groupe": "ips", "unite": "indice", "label": "IPS moyen, collèges privés sous contrat", "url": source["url"], "calcul": None,
         "points": [[rentree_mois(r), nat[i][1]] for i, r in enumerate(rentrees)]},
    ]
    return doc_map, lignes, source, methode, limites

def effectifs_ecoles():
    rows = query(EFFECTIFS, {
        "select": "rentree_scolaire,count(*) as ecoles,sum(nombre_total_eleves) as eleves,sum(nombre_total_classes) as classes",
        "where": 'secteur="PUBLIC"', "group_by": "rentree_scolaire", "order_by": "rentree_scolaire", "limit": 100})
    pts = [(r["rentree_scolaire"][:4] + "-09", r["ecoles"], int(r["eleves"]), int(r["classes"])) for r in rows]
    url = PAGE + EFFECTIFS + "/"
    return [
        {"id": "eleves_par_classe", "groupe": "classes", "unite": "élèves", "label": "Élèves par classe, écoles publiques", "url": url,
         "calcul": "moyenne calculée par ÉCART : total des élèves / total des classes", "points": [[t, round(e / c, 2)] for t, _, e, c in pts]},
        {"id": "ecoles_publiques", "groupe": "ecoles", "unite": "écoles", "label": "Écoles publiques", "url": url, "calcul": None,
         "points": [[t, n] for t, n, _, _ in pts]},
        {"id": "eleves_publics", "groupe": "eleves", "unite": "élèves", "label": "Élèves des écoles publiques", "url": url, "calcul": None,
         "points": [[t, e] for t, _, e, _ in pts]},
    ]

def main():
    doc_map, lignes, source, methode, limites = ips_colleges()
    lignes += effectifs_ecoles()
    methode += (" Effectifs : élèves et classes des écoles publiques (maternelle et élémentaire) au constat de rentrée ; "
                "élèves par classe calculé par ÉCART.")
    limites += (" Moins d'écoles ne veut pas dire autant de fermetures : une partie vient de regroupements administratifs "
                "(maternelle et élémentaire réunies en école primaire). La baisse du nombre d'élèves par classe vient en grande partie "
                "du dédoublement des CP et CE1 en éducation prioritaire et de la baisse des naissances ; la moyenne masque les classes chargées.")
    changed = write_if_changed(OUT_MAP, doc_map, ["rentrees", "colleges", "deps", "ips_national"])
    serie = {"id": "ecole", "titre": "École", "frequence": "annuelle (rentrée scolaire)",
             "groupes": {"ips": "IPS des collèges, public / privé", "classes": "Élèves par classe (écoles publiques)",
                         "ecoles": "Nombre d'écoles publiques", "eleves": "Élèves des écoles publiques"},
             "portee": "France entière (moyennes nationales)", "source": source,
             "methode": methode, "limites": limites, "lignes": lignes}
    changed |= write_if_changed(OUT_SERIE, serie, ["lignes"])
    last = doc_map["rentrees"][-1]
    print(f"IPS collèges : {len(doc_map['colleges'])} collèges localisés, {doc_map['sans_coordonnees']} sans coordonnées, "
          f"rentrées {doc_map['rentrees'][0]} à {last}" + ("" if changed else " (inchangé)"))

if __name__ == "__main__":
    main()
