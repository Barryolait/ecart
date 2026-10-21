"""Récupère le flux instantané des prix carburants (data.economie.gouv.fr)
et l'agrège en grille de 0,2° : prix moyen du gazole par cellule.
Seuls les prix mis à jour depuis moins de FRESH_DAYS jours sont gardés.
Attention : gazole_maj est suffixé +00:00 mais c'est l'heure de Paris (cf. champ brut prix/@maj).
Sortie : data/carburants.json
  {mode, updated, carburant, source, stats: {stations, p05, mediane, p95, maj_max}, cells: [[lon, lat, prix, nb_stations]]}"""
import gzip, json, pathlib, statistics, urllib.request, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/carburants.json"
URL = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
       "prix-des-carburants-en-france-flux-instantane-v2/exports/json"
       "?select=geom,gazole_prix,gazole_maj")
STEP = 0.2
FRESH_DAYS = 7

def fetch(url):
    # Le serveur peut répondre en gzip même sans Accept-Encoding ; urllib ne décompresse pas.
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    return json.loads(gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body)

def main():
    stations = fetch(URL)
    now = datetime.datetime.now(datetime.timezone.utc)
    fresh_from = (now - datetime.timedelta(days=FRESH_DAYS)).isoformat()
    buckets, prices, maj_max = {}, [], ""
    for s in stations:
        g, p, maj = s.get("geom"), s.get("gazole_prix"), s.get("gazole_maj") or ""
        if not g or p is None or maj < fresh_from:
            continue
        lon, lat = g.get("lon"), g.get("lat")
        if lon is None or not (-5.5 < lon < 10 and 41 < lat < 51.5):  # métropole + Corse
            continue
        key = (round(lon / STEP) * STEP, round(lat / STEP) * STEP)
        buckets.setdefault(key, []).append(float(p))
        prices.append(float(p))
        maj_max = max(maj_max, maj)
    if not prices:
        raise RuntimeError("aucun prix gazole récent : champs de l'API modifiés ?")
    cells = [[round(k[0], 2), round(k[1], 2), round(statistics.mean(v), 3), len(v)]
             for k, v in buckets.items()]
    q = statistics.quantiles(prices, n=20)
    OUT.write_text(json.dumps({
        "mode": "live",
        "updated": now.isoformat(timespec="minutes"),
        "carburant": "gazole", "source": "https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/",
        "stats": {"stations": len(prices), "p05": round(q[0], 3), "mediane": round(statistics.median(prices), 3),
                  "p95": round(q[-1], 3), "maj_max": maj_max[:16]},
        "cells": cells,
    }), encoding="utf-8")
    print(f"{len(stations)} stations, {len(prices)} prix de moins de {FRESH_DAYS} j -> {len(cells)} cellules")

if __name__ == "__main__":
    main()
