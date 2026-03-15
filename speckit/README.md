# Speckit - ARplus-WebKitV2

## Topo rapide

ARplus-WebKitV2 est une application desktop Python basee sur `PySide6` et `Pillow`.
Le produit sert a composer rapidement des visuels multi-calques pour un flux "replay / social / diffusion" puis a les exporter en plusieurs formats.

Le projet tourne aujourd'hui autour de 2 experiences principales :

- `KIT Replay` : composition du poster principal, du logo, des backgrounds, des banners, et generation des exports associes.
- `TOP` : mini-programme integre, autonome, qui reprend la logique historique de `TopAR+.py` pour produire les `TOP 1` a `TOP 5`.

## Fichiers pivots

- `ARPlus.py`
  - point d'entree principal
  - UI principale
  - logique des calques
  - gestion des typos locales + DaFont
  - pipeline preview / export / snapshots projet
  - integration du workspace `TOP`
- `TopAR+.py`
  - reference legacy du programme TOP autonome
  - utile comme source de verite historique pour le comportement des TOP
- `CHANGELOG.md`
  - trace des grosses evolutions recentes
- `README.md`
  - doc minimale du repo

## Dossiers importants

- `asset/Boot`
  - video de demarrage
- `asset/gabarits`
  - gabarits poster / hero / fullscreen / background
- `asset/TOP`
  - templates `top-1.png` a `top-5.png`
- `asset/logo`
  - icones application
- `asset/Typographie`
  - bibliotheque locale de typos + imports DaFont
- `data`
  - etat UI, cache previews, sante DaFont, projet courant
- `autosafe`
  - snapshots auto `.arplus.json`
- `exports`
  - sorties generees

## Flux produit actuel

1. Import des assets visuels dans `KIT Replay`.
2. Ajustement des calques par preset.
3. Preview temps reel dans le canvas principal.
4. Preview strip des gabarits.
5. Validation avant export sur certains cas bloquants.
6. Export multi-format + `metadata.json`.
7. Sauvegarde / reimport projet via snapshots `.arplus.json`.

En parallele :

1. Onglet `TOP`.
2. Import autonome par TOP.
3. Reglages `offset / zoom / stretch`.
4. Export individuel ou par lot.

## Ce que le projet fait bien aujourd'hui

- UX orientee production rapide.
- Gestion avancee du `logo texte`.
- Export multi-sorties depuis un meme etat.
- Gestion de plusieurs personnages et ajustements visuels.
- Typotheque locale exploitable dans l'app.
- Integration du workflow TOP sans sortir du programme.

## Zones sensibles

- `ARPlus.py` concentre encore la quasi-totalite du produit.
- Beaucoup de logique UI, etat, rendu et export restent couples.
- Il existe encore des traces legacy / doublons de builders dans le fichier principal.
- Le flux DaFont repose sur du parsing HTML, donc fragile par nature.
- La logique de nommage, validations export et variantes poster reste tres metier et doit rester strictement documentee.

## Ce que contient ce speckit

- `01-Specify.md`
- `02-Clarify-Checklist.md`
- `03-Plan.md`
- `04-Tasks.md`
- `05-Analyze.md`
- `06-Implement.md`

L'objectif est de donner une base claire pour continuer le projet sans re-decouvrir tout le code a chaque passe.
