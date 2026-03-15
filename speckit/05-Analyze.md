# Analyze

## Vue architecture actuelle

Le projet repose aujourd'hui sur un centre de gravite unique : `ARPlus.py`.

Ce fichier porte presque tout :

- structure UI
- etat applicatif
- rendu preview
- rendu export
- gestion des assets
- persistance projet
- typotheque locale
- integration DaFont
- integration du workspace TOP
- splash video

En pratique, cela rend le projet tres rapide a faire evoluer localement, mais plus couteux a maintenir sur la duree.

## Observations techniques

### 1. Monolithe fonctionnel

Le produit est deja riche, mais la concentration dans un seul fichier augmente :

- le risque de duplication
- les regressions transverses
- le cout de comprehension

### 2. Logique metier tres specifique

Le projet contient beaucoup de regles qui ne sont pas "generiques image editor", mais purement metier :

- placement des persos
- gestion du logo texte
- variantes poster / info / nologo
- exports TOP
- validations avant export

Ces regles doivent rester documentees, sinon elles se reperdent vite.

### 3. Couplage preview / export

C'est une force et un risque a la fois :

- force : le rendu reste coherent pour l'utilisateur
- risque : un ajustement visuel peut casser l'export sans etre evident

### 4. Dette historique

`TopAR+.py` sert encore de reference historique.
Cela veut dire qu'il existe au moins 2 verites possibles :

- la logique legacy
- la logique integree dans `ARPlus.py`

Tant que le legacy n'est pas completement absorbe ou archive proprement, il faut le garder comme point de comparaison.

### 5. Flux typo hybride

La bibliotheque locale est saine.
Le flux DaFont est utile, mais reste fragile parce qu'il depend de HTML externe et de contraintes de compatibilite / licence.

## Risques majeurs

- casser un export en corrigeant seulement la preview
- reintroduire d'anciennes valeurs par defaut
- faire diverger `TOP` autonome et `KIT Replay`
- casser les noms attendus des fichiers
- laisser des assets ou dossiers ambigus se multiplier

## Levier principal d'amelioration

Le meilleur gain n'est pas forcement une grosse refonte immediate.
Le levier le plus rentable est :

1. documenter les regles metier
2. centraliser les helpers critiques
3. modulariser progressivement

## Recommendation

Ne pas tenter une decomposition massive en une passe.
Faire une migration par zones :

- exports
- snapshots
- typos
- TOP
- rendu principal
