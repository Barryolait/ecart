"""Convertit data/participation.csv (saisi à la main) en data/participation.json."""
import csv, json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data/participation.csv", ROOT / "data/participation.json"

def num(v):
    v = (v or "").strip().replace(" ", "")
    return int(v) if v else None

rows = []
with SRC.open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "date": r["date"], "perimetre": r["perimetre"], "ville": r["ville"],
            "lat": float(r["lat"]) if r["lat"] else None,
            "lon": float(r["lon"]) if r["lon"] else None,
            "interieur": num(r["interieur"]), "organisateurs": num(r["organisateurs"]),
            "independant": num(r["independant"]),
            "source": {"label": r["source_label"], "url": r["source_url"]} if r["source_url"] else None,
        })

OUT.write_text(json.dumps({
    "mode": "manuel",
    "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
    "rows": rows,
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(rows)} lignes -> {OUT.name}")
