# Tasks

## P0 - Toujours critique

- [ ] Documenter la matrice d'export complete dans le repo
- [ ] Documenter les validations bloquantes de fond / personnage
- [ ] Lister les valeurs par defaut officielles du projet
- [ ] Verifier les variants poster avec et sans bandeau
- [ ] Verifier la coherence `KIT Replay` -> exports TOP 1..5
- [ ] Verifier la coherence `TOP` autonome -> export individuel / export lot

## P1 - Architecture

- [ ] Isoler un module de nommage d'exports
- [ ] Isoler un module de snapshots projet
- [ ] Isoler un module de gestion typo locale / DaFont
- [ ] Isoler un module de rendu TOP
- [ ] Recenser les builders ou handlers legacy encore presents dans `ARPlus.py`

## P1 - UX

- [ ] Passer les labels restants en terminologie homogone
- [ ] Identifier les boutons primaires vs secondaires
- [ ] Revoir les messages d'erreur et de succes
- [ ] Revoir les placeholders des champs projet

## P1 - Assets

- [ ] Nettoyer les reliquats `asset/typo` vs `asset/Typographie`
- [ ] Distinguer assets source, caches et imports externes
- [ ] Normaliser les noms de templates et gabarits

## P2 - Qualite

- [ ] Ajouter une batterie de smoke tests de nommage
- [ ] Ajouter une batterie de smoke tests de snapshots projet
- [ ] Ajouter des checks de presence assets critiques au demarrage
- [ ] Evaluer un packaging Windows propre
