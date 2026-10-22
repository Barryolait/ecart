"""Historique du prix du gazole à partir des archives annuelles officielles
(donnees.roulez-eco.fr/opendata/annee/AAAA : chaque changement de prix de chaque station).

Méthode : chaque jour, chaque station compte avec le dernier prix qu'elle a déclaré
ce jour-là ou avant, s'il date de 7 jours au plus (même règle que la couche live).
  - France métropolitaine + Corse : médiane, 1er et 9e décile, par jour ;
  - par département : médiane par semaine (lundi-dimanche) de tous les prix station-jour,
    publiée si au moins MIN_STATIONS stations distinctes ont un prix dans la semaine.
L'année précédant la première année publiée sert seulement d'amorce (prix en vigueur au 1er janvier).

Usage :
  python3 scripts/fetch_carburants_historique.py              # recalcule l'année en cours (amorce : année précédente)
  python3 scripts/fetch_carburants_historique.py --depuis 2022  # recalcul complet (local, ~10 min)
  --dossier DIR : lit DIR/AAAA.zip au lieu de télécharger
Sorties : data/series/gazole.json (format commun des séries) et data/carburants_departements.json"""
import collections, datetime, io, json, pathlib, re, sys, tempfile, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_SERIE = ROOT / "data/series/gazole.json"
OUT_DEP = ROOT / "data/carburants_departements.json"
URL = "https://donnees.roulez-eco.fr/opendata/annee/{}"
PAGE = "https://www.prix-carburants.gouv.fr/rubrique/opendata/"
FRESH = datetime.timedelta(days=7)
MIN_STATIONS = 5
ONE = datetime.timedelta(days=1)

RE_PDV = re.compile(r'<pdv id="(\d+)"[^>]*\bcp="(\d{5})"')
RE_GAZ = re.compile(r'<prix nom="Gazole"[^>]*\bmaj="(\d{4}-\d{2}-\d{2})[T ][^"]*"[^>]*\bvaleur="([\d.]+)"')

def departement(cp):
    if cp.startswith("20"):
        return "2A" if cp < "20200" else "2B"
    return None if cp.startswith("97") or cp.startswith("98") else cp[:2]

def monday(d):
    return d - datetime.timedelta(days=d.weekday())

def open_year(year, dossier):
    if dossier:
        return zipfile.ZipFile(pathlib.Path(dossier) / f"{year}.zip")
    tmp = tempfile.TemporaryFile()
    with urllib.request.urlopen(URL.format(year), timeout=600) as r:
        while chunk := r.read(1 << 20):
            tmp.write(chunk)
    tmp.seek(0)
    return zipfile.ZipFile(tmp)

def stations(year, dossier):
    """Itère (id, département, [(date, prix_millièmes)]) pour chaque station de l'archive."""
    z = open_year(year, dossier)
    with z.open(z.namelist()[0]) as raw:
        cur, dep, ev = None, None, []
        for line in io.TextIOWrapper(raw, encoding="latin-1"):
            m = RE_PDV.search(line)
            if m:
                if cur and dep:
                    yield cur, dep, ev
                cur, dep, ev = m.group(1), departement(m.group(2)), []
                continue
            g = RE_GAZ.search(line)
            if g and dep:
                v = float(g.group(2))
                mil = round(v if v > 100 else v * 1000)  # avant 2022 : prix en millièmes d'euro
                if 500 <= mil <= 5000:  # écarte les saisies aberrantes (< 0,50 € ou > 5 €)
                    ev.append((datetime.date.fromisoformat(g.group(1)), mil))
        if cur and dep:
            yield cur, dep, ev

def median_of(counter, q=0.5):
    total = sum(counter.values())
    rank, acc = q * (total - 1), 0
    for value in sorted(counter):
        acc += counter[value]
        if acc > rank:
            return value / 1000

def main():
    args = sys.argv
    today = datetime.date.today()
    first = int(args[args.index("--depuis") + 1]) if "--depuis" in args else today.year
    dossier = args[args.index("--dossier") + 1] if "--dossier" in args else None
    end = today - ONE  # la journée en cours est incomplète

    day_counts = collections.defaultdict(collections.Counter)                          # jour -> prix -> n
    week_counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # lundi -> dép -> prix -> n
    week_stations = collections.defaultdict(collections.Counter)                       # lundi -> dép -> stations
    last = {}  # station -> (date, prix) : amorce d'une année sur l'autre
    last_seen = datetime.date(first - 1, 1, 1)

    for year in range(first - 1, today.year + 1):
        y_end = min(datetime.date(year, 12, 31), end)
        for sid, dep, ev in stations(year, dossier):
            ev.sort()
            if ev:
                last_seen = max(last_seen, ev[-1][0])
            seed = last.get(sid)
            if seed:
                ev.insert(0, seed)
            if not ev:
                continue
            d, i, cur, weeks = datetime.date(year, 1, 1), 0, None, set()
            while d <= y_end:
                while i < len(ev) and ev[i][0] <= d:
                    cur = ev[i]
                    i += 1
                if cur and d - cur[0] <= FRESH:
                    day_counts[d][cur[1]] += 1
                    w = monday(d)
                    week_counts[w][dep][cur[1]] += 1
                    weeks.add(w)
                d += ONE
            for w in weeks:
                week_stations[w][dep] += 1
            last[sid] = ev[-1]
        print(f"{year} lu", flush=True)

    end = min(end, last_seen)  # l'archive peut avoir un jour de retard
    day_from = datetime.date(first, 1, 1)
    week_from = monday(day_from)
    days = [d for d in sorted(day_counts) if day_from <= d <= end]
    weeks = [w for w in sorted(week_counts) if week_from <= w <= end]

    # Fusion avec l'historique déjà calculé (années antérieures à `first`)
    lines = {"mediane": [], "d1": [], "d9": []}
    if OUT_SERIE.exists():
        for l in json.loads(OUT_SERIE.read_text(encoding="utf-8"))["lignes"]:
            lines[l["id"]] = [p for p in l["points"] if p[0] < day_from.isoformat()]
    for d in days:
        c = day_counts[d]
        lines["mediane"].append([d.isoformat(), median_of(c)])
        lines["d1"].append([d.isoformat(), median_of(c, 0.1)])
        lines["d9"].append([d.isoformat(), median_of(c, 0.9)])

    deps_old, weeks_old = {}, []
    if OUT_DEP.exists():
        old = json.loads(OUT_DEP.read_text(encoding="utf-8"))
        keep = [k for k, w in enumerate(old["semaines"]) if w < week_from.isoformat()]
        weeks_old = [old["semaines"][k] for k in keep]
        deps_old = {dep: [vals[k] for k in keep] for dep, vals in old["deps"].items()}
    all_deps = sorted(set(deps_old) | {dep for w in weeks for dep in week_counts[w]})
    deps = {dep: deps_old.get(dep, [None] * len(weeks_old)) +
                 [median_of(week_counts[w][dep]) if week_stations[w][dep] >= MIN_STATIONS else None for w in weeks]
            for dep in all_deps}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    source = {"label": "Ministère de l'Économie, archives annuelles des prix des carburants (donnees.roulez-eco.fr)", "url": PAGE}
    methode = ("Chaque jour, chaque station compte avec le dernier prix du gazole qu'elle a déclaré, s'il date de 7 jours au plus. "
               "Médiane et déciles calculés par ÉCART sur toutes les stations de métropole et de Corse.")
    limites = ("Prix déclarés par les stations elles-mêmes, avec des oublis et des retards. "
               "Le prix à la pompe ne dit pas combien chaque foyer dépense : cela dépend de la distance parcourue et de l'accès aux transports. "
               "Outre-mer exclu (prix administrés).")
    OUT_SERIE.parent.mkdir(parents=True, exist_ok=True)
    OUT_SERIE.write_text(json.dumps({
        "id": "gazole", "titre": "Prix du gazole", "unite": "€/L", "frequence": "quotidienne",
        "portee": "France métropolitaine et Corse", "source": source, "methode": methode, "limites": limites,
        "updated": now,
        "lignes": [
            {"id": "mediane", "label": "Médiane", "url": PAGE, "calcul": "médiane calculée par ÉCART", "points": lines["mediane"]},
            {"id": "d1", "label": "1er décile (10 % des stations moins chères)", "url": PAGE, "calcul": "décile calculé par ÉCART", "points": lines["d1"]},
            {"id": "d9", "label": "9e décile (10 % des stations plus chères)", "url": PAGE, "calcul": "décile calculé par ÉCART", "points": lines["d9"]},
        ],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    OUT_DEP.write_text(json.dumps({
        "source": source, "updated": now, "carburant": "gazole", "unite": "€/L",
        "methode": methode.replace("sur toutes les stations de métropole et de Corse",
                                   f"par département et par semaine (lundi-dimanche), publiée si au moins {MIN_STATIONS} stations ont un prix"),
        "limites": limites, "semaine_en_cours": monday(end).isoformat() if end.weekday() < 6 else None,
        "semaines": weeks_old + [w.isoformat() for w in weeks], "deps": deps,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(lines['mediane'])} jours, {len(weeks_old) + len(weeks)} semaines, {len(deps)} départements ; "
          f"dernier jour {end} : médiane {lines['mediane'][-1][1] if lines['mediane'] else '—'} €")

if __name__ == "__main__":
    main()
