"""Contours des départements (métropole + Corse) pour la carte, à lancer une fois par an.
Source : Etalab, contours administratifs simplifiés à 1 000 m, Licence Ouverte.
Coordonnées arrondies à 3 décimales (~100 m) pour alléger la page.
Sortie : data/departements.geojson"""
import gzip, json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/departements.geojson"
YEAR = sys.argv[1] if len(sys.argv) > 1 else "2026"
URL = f"https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/{YEAR}/geojson/departements-1000m.geojson.gz"

def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]

def main():
    with urllib.request.urlopen(URL, timeout=120) as r:
        src = json.loads(gzip.decompress(r.read()))
    feats = [{"type": "Feature", "properties": {"code": f["properties"]["code"], "nom": f["properties"]["nom"]},
              "geometry": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}}
             for f in src["features"] if len(f["properties"]["code"]) == 2]
    OUT.write_text(json.dumps({"type": "FeatureCollection", "source": URL, "licence": "Licence Ouverte 2.0",
                               "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(feats)} départements -> {OUT.name} ({OUT.stat().st_size // 1024} Ko)")

if __name__ == "__main__":
    main()
