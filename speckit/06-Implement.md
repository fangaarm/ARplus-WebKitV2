# Implement

## Regle de travail recommandee

Pour toute future evolution :

1. partir d'une demande fonctionnelle claire
2. verifier si la regle existe deja ailleurs dans `ARPlus.py` ou `TopAR+.py`
3. modifier le moins de surfaces possible
4. verifier la syntaxe
5. verifier le flux reel affecte
6. mettre a jour la doc si la regle change

## Workflow conseille

### A. Avant de coder

- confirmer le comportement attendu
- reperer les fonctions centrales deja en place
- verifier si le changement touche `KIT Replay`, `TOP`, ou les deux
- identifier les impacts export / preview / snapshot

### B. Pendant l'implementation

- garder les changements localises
- factoriser les helpers si la logique est appelee a plusieurs endroits
- eviter d'ajouter une nouvelle branche speciale si une regle peut etre centralisee

### C. Verification minimale

- `py -3.11 -m py_compile ARPlus.py`
- smoke test offscreen si possible
- verification manuelle du flux utilisateur si le changement est UI ou rendu

## Sequence de modularisation recommandee

Ordre suggere si le projet continue a grandir :

1. `export_naming.py`
2. `project_state.py`
3. `font_library.py`
4. `top_workspace.py`
5. `render_pipeline.py`

## Candidats concrets pour la suite

- sortir toute la logique de nommage dans un helper dedie
- sortir toute la logique snapshots / autosafe / import projet
- sortir la logique typo locale + DaFont
- sortir le rendu TOP dans un module propre
- poser une doc "matrice d'exports" dans le repo

## Definition of done recommandee

Une evolution est consideree propre quand :

- le comportement est conforme a la demande
- les sorties export sont correctes
- les valeurs par defaut restent coherentes
- aucun flux critique connu n'est casse
- la regle ajoutee est facile a retrouver dans le code ou la doc
