# Plan

## Phase 1 - Stabiliser le noyau produit

Objectif :
fiabiliser les comportements critiques sans changer l'usage de base.

Actions :

- verrouiller les conventions de nommage d'export
- documenter les validations bloquantes
- nettoyer les valeurs par defaut sensibles
- verifier la coherence preview / export sur les cas critiques

Sortie attendue :

- un flux `KIT Replay` fiable
- un flux `TOP` fiable
- des exports predictibles

## Phase 2 - Rendre l'architecture plus lisible

Objectif :
reduire la dette autour du gros fichier unique `ARPlus.py`.

Actions :

- cartographier les zones UI / logique / export / typo / TOP
- isoler les helpers de nommage / persistance / assets
- identifier et supprimer les builders legacy inutiles

Sortie attendue :

- un code plus simple a reprendre
- moins de duplications implicites

## Phase 3 - Formaliser les workflows metier

Objectif :
transformer les regles implicites en regles explicites.

Actions :

- formaliser la matrice des exports
- formaliser les variantes poster avec ou sans bandeau
- formaliser la relation `KIT Replay` / `TOP`
- formaliser la politique typo locale / DaFont

Sortie attendue :

- moins d'ambiguite lors des futures demandes

## Phase 4 - Renforcer la maintenance

Objectif :
faciliter les evolutions futures.

Actions :

- introduire des verifications manuelles standardisees
- poser des tests legers sur les noms d'export et payloads projet
- preparer un decoupage modulaire progressif

Sortie attendue :

- un projet plus robuste face aux regressions
