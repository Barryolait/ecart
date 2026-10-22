# ÉCART — observatoire des chiffres de la mobilisation

Carte isométrique de la France qui croise trois couches :

| Couche | Source | Mise à jour |
|---|---|---|
| Prix du gazole (moyenne par cellule de 0,2°, prix de moins de 7 j) | data.economie.gouv.fr, flux instantané v2 | automatique, toutes les 15 min |
| Signal médiatique de protestation (CAMEO 14, géolocalisé ville) | GDELT 2.0 | automatique, toutes les 15 min, fenêtre de 7 jours |
| Comptages de participation | `data/participation.csv` | manuel |
| Inflation sur un an (frise) : ensemble, alimentation, produits frais, énergie, produits pétroliers, 20 % les plus modestes | INSEE, IPC base 2025 (API SDMX ouverte) | automatique, mensuelle (vérifiée toutes les heures) |
| Gazole, historique : médiane et 1er–9e décile par jour (frise), médiane par département et par semaine (carte, pilotée par le curseur) | archives annuelles prix-carburants (donnees.roulez-eco.fr), depuis 2022 | automatique, une fois par jour |
| École : IPS des collèges (carte, rentrées 2023 et suivantes) et écart d'IPS privé − public par département ; effectifs des écoles publiques depuis 2009 (frise) | data.education.gouv.fr (IPS, annuaire, effectifs) | automatique, vérifiée chaque semaine (données annuelles) |

Sans fichier de données, la page affiche des couches de démonstration clairement signalées.

## Mise en ligne (gratuit)

1. Crée un dépôt **public** sur GitHub et pousse ce dossier.
2. *Settings → Pages* : source = branche `main`, dossier `/ (root)`.
3. *Actions* : lance une fois « Mise à jour des données » (bouton *Run workflow*).
4. Le site est en ligne sur `https://<ton-pseudo>.github.io/<depot>/`.

## Ajouter un comptage

Modifie `data/participation.csv` directement sur GitHub (une ligne par ville et par journée) en indiquant toujours la source. Le commit relance la conversion en JSON.

## Test en local

```bash
python3 scripts/build_participation.py
python3 -m http.server 8000   # puis http://localhost:8000
```

## Séries temporelles (`data/series/*.json`)

Chaque fichier suit le même format, lu par la frise en bas de page :

```json
{"id": "ipc", "titre": "...", "unite": "%", "frequence": "mensuelle", "portee": "...",
 "source": {"label": "...", "url": "..."}, "methode": "...", "limites": "...", "updated": "...",
 "lignes": [{"id": "ensemble", "label": "Ensemble", "idbank": "...", "url": "...", "calcul": null,
             "points": [["2026-09", 3.1], ...]}]}
```

`calcul` est renseigné quand la valeur n'est pas publiée telle quelle par la source mais calculée par ÉCART.

## Historique du gazole

`scripts/fetch_carburants_historique.py` recalcule chaque jour l'année en cours (l'année précédente sert d'amorce)
et la fusionne avec l'historique déjà publié. Recalcul complet depuis 2022, en local :

```bash
python3 scripts/fetch_carburants_historique.py --depuis 2022
```

Les contours des départements (`data/departements.geojson`, Etalab, Licence Ouverte) se régénèrent avec
`python3 scripts/build_departements.py 2026`.
