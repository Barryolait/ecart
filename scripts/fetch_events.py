"""Récupère les exports GDELT 2.0 (un fichier toutes les 15 min), garde les
événements de protestation (code CAMEO racine 14) géolocalisés en France au
niveau ville ou région, et les fusionne dans une fenêtre glissante de 7 jours.

Le cron de GitHub Actions est souvent retardé ou sauté : chaque run rattrape
tous les créneaux de 15 min manqués depuis le dernier traité (24 h max).
Amorçage local sur 7 jours : python3 scripts/fetch_events.py --backfill 7

Sortie : data/events.json
  {mode, updated, last_slot, source, events: [{id, date, lieu, precision, code, articles, lon, lat, url}]}"""
import csv, io, json, pathlib, sys, urllib.error, urllib.request, zipfile, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/events.json"
BASE = "https://data.gdeltproject.org/gdeltv2/"
KEEP_DAYS = 7
MAX_SLOTS = 96  # rattrapage max par run : 24 h
SLOT = datetime.timedelta(minutes=15)
# Colonnes de l'export GDELT 2.0 (61 colonnes)
C_ID, C_CODE, C_ROOT, C_ARTICLES = 0, 26, 28, 33
C_GEOTYPE, C_PLACE, C_COUNTRY, C_LAT, C_LON, C_ADDED, C_URL = 51, 52, 53, 56, 57, 59, 60
# ActionGeo_Type : 1 = pays (point fictif au centre), 4 = ville, 5 = région (centroïde)
PRECISION = {"4": "ville", "5": "région"}

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()

def latest_slot():
    for line in get(BASE + "lastupdate.txt").decode().splitlines():
        if line.endswith(".export.CSV.zip"):
            stamp = line.split("/")[-1][:14]
            return datetime.datetime.strptime(stamp, "%Y%m%d%H%M%S")
    raise RuntimeError("export introuvable")

def read_slot(slot, events):
    url = f"{BASE}{slot:%Y%m%d%H%M%S}.export.CSV.zip"
    try:
        z = zipfile.ZipFile(io.BytesIO(get(url)))
    except urllib.error.HTTPError as e:
        if e.code == 404:  # GDELT saute parfois un créneau
            return 0
        raise
    raw = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    n = 0
    for row in csv.reader(io.StringIO(raw), delimiter="\t"):
        if len(row) < 61 or row[C_ROOT] != "14" or row[C_COUNTRY] != "FR":
            continue
        if row[C_GEOTYPE] not in PRECISION or not row[C_LAT] or not row[C_LON]:
            continue
        added = row[C_ADDED]  # AAAAMMJJHHMMSS
        events[row[C_ID]] = {
            "id": row[C_ID],
            "date": f"{added[:4]}-{added[4:6]}-{added[6:8]}T{added[8:10]}:{added[10:12]}Z",
            "lieu": row[C_PLACE], "precision": PRECISION[row[C_GEOTYPE]],
            "code": row[C_CODE], "articles": int(row[C_ARTICLES] or 0),
            "lon": float(row[C_LON]), "lat": float(row[C_LAT]), "url": row[C_URL],
        }
        n += 1
    return n

def main():
    backfill = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
    events, last = {}, None
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        if prev.get("mode") == "live":
            events = {e["id"]: e for e in prev["events"] if e.get("precision")}
            if prev.get("last_slot"):
                last = datetime.datetime.strptime(prev["last_slot"], "%Y%m%d%H%M%S")

    newest = latest_slot()
    max_slots = backfill * 96 if backfill else MAX_SLOTS
    start = newest - SLOT * (max_slots - 1)
    if last and not backfill:
        start = max(start, last + SLOT)
    slot, done = start, 0
    while slot <= newest:
        done += 1
        read_slot(slot, events)
        slot += SLOT

    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%dT%H:%MZ")
    kept = sorted((e for e in events.values() if e["date"] >= cutoff),
                  key=lambda e: e["date"], reverse=True)
    OUT.write_text(json.dumps({
        "mode": "live",
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
        "last_slot": f"{newest:%Y%m%d%H%M%S}",
        "source": "https://www.gdeltproject.org/", "events": kept,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"{done} créneaux lus, {len(kept)} événements sur {KEEP_DAYS} jours")

if __name__ == "__main__":
    main()
