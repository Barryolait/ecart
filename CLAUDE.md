# ÉCART — contexte projet

Observatoire des chiffres de la mobilisation sociale en France (automne 2026).
Croise chiffres de participation (Intérieur / organisateurs / comptage indépendant),
prix du gazole et événements de protestation, sur une carte isométrique.

## Principes non négociables
- Chaque chiffre affiché a une source cliquable. Jamais de donnée inventée présentée comme réelle :
  une couche simulée porte le badge « démo ».
- Toujours afficher une fourchette de participation, pas un chiffre unique.
- Aucune donnée personnelle : pas de visages, pas d'identification d'individus
  (manifestants, policiers, journalistes), pas de suivi des forces de l'ordre.

## Stack (gratuite, sans serveur)
- `index.html` : page unique, deck.gl 8.9.35 (UMD via unpkg), lit `./data/*.json`,
  bascule sur des données de démo si un fichier manque.
- `scripts/` : Python stdlib uniquement.
  - `build_participation.py` : `data/participation.csv` (saisi à la main) → JSON
  - `fetch_carburants.py` : flux instantané v2 data.economie.gouv.fr → grille 0,2°
  - `fetch_events.py` : export GDELT 2.0, CAMEO racine 14, FR, fenêtre 7 jours
- `.github/workflows/update.yml` : cron 15 min, commit des JSON. Hébergement GitHub Pages.

## Direction artistique
Écran de contrôle sci-fi / holographique : fond noir, wireframe, vue isométrique
(pitch 52°, bearing -24°). Palette : jaune signal #ffd400, cyan #3ae6ff, rouge alerte #ff4a3d.
Polices : Chakra Petch (titres), IBM Plex Mono (données). Scanlines, coins de cadre, ticker.
Références : topologie réseau, isométrique filaire multicolore, terrain holographique.

## Pistes suivantes
- Vérifier les noms de champs de l'API carburants au premier run réel.
- Comptage indépendant : vidéo en plongée depuis un point haut + YOLO/tracker (franchissement
  de ligne) ou P2PNet, traitement local, seuls les chiffres sont conservés → colonne `independant`.
- Couches sociales : IPS des lycées (data.education.gouv.fr), IPC INSEE.
- Contour de France plus précis (GeoJSON simplifié embarqué).

## Préférences de l'auteur (Aël)
Répondre en français. Livrer fichier par fichier pour les changements incrémentaux.
Expliquer simplement avant de coder une décision d'architecture importante.
