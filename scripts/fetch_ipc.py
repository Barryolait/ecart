"""Récupère l'indice des prix à la consommation (INSEE, base 2025, rétropolé
depuis 1996) via l'API SDMX ouverte de la BDM, sans clé.
Glissements annuels publiés par l'INSEE, sauf pour la comparaison « ménages
modestes » : l'INSEE ne publie que l'indice du premier quintile, le glissement
est calculé ici (indice du mois / indice du même mois un an avant - 1) sur la
même base « hors tabac » que la série de comparaison.

Le fichier n'est réécrit que si les données changent (pas de commit inutile).
Sortie : data/series/ipc.json  (format commun des séries temporelles, cf. README)"""
import json, pathlib, re, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/series/ipc.json"
API = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/"
PAGE = "https://www.insee.fr/fr/statistiques/serie/"

# (id, libellé, idbank, nature) ; nature "glissement" = publié par l'INSEE, "indice" = glissement calculé ici
SERIES = [
    ("ensemble", "Ensemble", "011814632", "glissement"),
    ("alimentation", "Alimentation", "011813719", "glissement"),
    ("frais", "Produits frais", "011813740", "glissement"),
    ("energie", "Énergie", "011813866", "glissement"),
    ("petroliers", "Produits pétroliers", "011813887", "glissement"),
    ("q1", "20 % les plus modestes (hors tabac)", "011818264", "indice"),
    ("hors_tabac", "Ensemble hors tabac", "011814056", "indice"),
]

def fetch(idbanks):
    req = urllib.request.Request(API + "+".join(idbanks), headers={"Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        xml = r.read().decode("utf-8")
    out = {}
    for m in re.finditer(r"<Series ([^>]*)>(.*?)</Series>", xml, re.S):
        idbank = re.search(r'IDBANK="(\d+)"', m.group(1)).group(1)
        obs = re.findall(r'TIME_PERIOD="(\d{4}-\d{2})" OBS_VALUE="([-\d.]+)"', m.group(2))
        out[idbank] = sorted((t, float(v)) for t, v in obs)
    return out

def yoy(points):
    by = dict(points)
    res = []
    for t, v in points:
        prev = f"{int(t[:4]) - 1}{t[4:]}"
        if prev in by:
            res.append((t, round((v / by[prev] - 1) * 100, 2)))
    return res

def main():
    raw = fetch([s[2] for s in SERIES])
    lines = []
    for sid, label, idbank, nature in SERIES:
        pts = raw.get(idbank)
        if not pts:
            raise RuntimeError(f"série {idbank} absente de la réponse INSEE")
        if nature == "indice":
            pts = yoy(pts)
        lines.append({
            "id": sid, "label": label, "idbank": idbank, "url": PAGE + idbank,
            "calcul": "glissement calculé par ÉCART à partir de l'indice INSEE" if nature == "indice" else None,
            "points": [[t, v] for t, v in pts],
        })
    doc = {
        "id": "ipc", "titre": "Inflation sur un an", "unite": "%", "frequence": "mensuelle",
        "portee": "France entière (métropole + DOM), national uniquement",
        "source": {"label": "INSEE, indices des prix à la consommation, base 2025", "url": "https://www.insee.fr/fr/statistiques/serie/011814632"},
        "methode": "Glissement annuel : évolution de l'indice du mois par rapport au même mois de l'année précédente. "
                   "Séries base 2025 rétropolées par l'INSEE jusqu'en 1996.",
        "limites": "Panier moyen de consommation : il sous-estime la hausse vécue par les ménages pour qui l'énergie, "
                   "l'alimentation ou le carburant pèsent plus. Pas de déclinaison régionale en métropole. "
                   "Le dernier mois est parfois une estimation provisoire, révisée mi-mois suivant.",
        "lignes": lines,
    }
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if old.get("lignes") == doc["lignes"]:
            print("IPC inchangé")
            return
    doc["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    last = {l["id"]: l["points"][-1] for l in lines}
    print(f"IPC mis à jour : {last['ensemble']} ensemble, {last['q1']} modestes")

if __name__ == "__main__":
    main()
