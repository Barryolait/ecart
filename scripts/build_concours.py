"""Convertit data/concours.csv (saisi à la main, une source par ligne) en data/series/concours.json.

Chaque ligne garde le périmètre exact de sa source : les communiqués du ministère ne comptent pas
toujours de la même façon (tous concours / concours externes, sessions supplémentaires incluses ou non),
et révisent parfois les chiffres de l'année précédente. Le graphe ne relie que les lignes d'une même
`serie` (même périmètre) ; les autres lignes restent consultables dans le tableau des sources.
Valeur tracée : postes offerts - admis, calculée par ÉCART."""
import csv, json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data/concours.csv", ROOT / "data/series/concours.json"
SERIES = {
    "pe_externe": "1er degré public · concours externes",
    "pe_tous": "1er degré public · tous concours",
    "second_externe": "2nd degré public · concours externes",
    "second_tous": "2nd degré public · tous concours",
}

def num(v):
    v = (v or "").replace(" ", "").replace(",", ".").strip()
    return float(v) if "." in v else int(v) if v else None

rows = []
with SRC.open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({k: num(r[k]) if k in ("postes", "admis", "non_pourvus_annonces", "taux_pourvus_annonce") else r[k].strip()
                     for k in r})

lignes = []
for sid, label in SERIES.items():
    pts = sorted((r for r in rows if r["serie"] == sid and r["postes"] is not None and r["admis"] is not None),
                 key=lambda r: r["session"])
    lignes.append({
        "id": sid, "label": label, "url": pts[-1]["source_url"] if pts else None,
        "calcul": "postes offerts - admis, calculé par ÉCART",
        # résultats publiés en juillet : le point est placé au 1er juillet de la session
        "points": [[f"{r['session']}-07", r["postes"] - r["admis"]] for r in pts],
        "details": [{"session": r["session"], "perimetre": r["perimetre"], "postes": r["postes"], "admis": r["admis"],
                     "annonce": r["non_pourvus_annonces"], "taux": r["taux_pourvus_annonce"], "note": r["note"],
                     "source": {"label": r["source_label"], "url": r["source_url"]}} for r in pts],
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "id": "concours", "titre": "Concours enseignants", "unite": "postes", "frequence": "annuelle (résultats en juillet)",
    "portee": "enseignement public (et privé sous contrat dans le tableau)", "mode": "manuel",
    "source": {"label": "data.education.gouv.fr (2016-2020) et communiqués du ministère (2024-2026)",
               "url": "https://www.education.gouv.fr/concours-enseignants-de-la-session-2026-premiers-effets-de-la-reforme-de-la-formation-initiale-des-505268"},
    "methode": "Postes offerts moins candidats admis, calculé par ÉCART pour chaque ligne publiée. "
               "Les chiffres « annoncés » (postes non pourvus, taux de postes pourvus) sont repris tels quels, avec leur source.",
    "limites": "Le périmètre change d'une source à l'autre (tous concours ou concours externes, sessions supplémentaires) et le ministère "
               "révise parfois l'année précédente : seules les lignes de même périmètre sont reliées. Des admis peuvent être comptés deux fois "
               "(double admissibilité). Baisser les postes offerts là où il manque des candidats fait monter le taux de postes pourvus sans "
               "ajouter d'enseignants. Pas de données ouvertes entre 2021 et 2023 pour l'instant.",
    "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
    "lignes": lignes, "tableau": rows,
}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(rows)} lignes -> {OUT.name} : " + ", ".join(f"{l['id']} {len(l['points'])} pts" for l in lignes))
