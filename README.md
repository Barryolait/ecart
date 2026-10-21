# ÉCART — observatoire des chiffres de la mobilisation

Carte isométrique de la France qui croise trois couches :

| Couche | Source | Mise à jour |
|---|---|---|
| Prix du gazole (moyenne par cellule de 0,2°, prix de moins de 7 j) | data.economie.gouv.fr, flux instantané v2 | automatique, toutes les 15 min |
| Signal médiatique de protestation (CAMEO 14, géolocalisé ville) | GDELT 2.0 | automatique, toutes les 15 min, fenêtre de 7 jours |
| Comptages de participation | `data/participation.csv` | manuel |

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
