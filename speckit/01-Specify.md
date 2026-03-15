# Specify

## Produit

Construire et maintenir un outil desktop unique de production visuelle pour :

- generer un poster principal
- decliner automatiquement plusieurs formats derives
- produire les `TOP 1` a `TOP 5`
- garder un niveau de controle manuel suffisant pour les cas de prod reels

## Probleme resolu

L'utilisateur a besoin d'un outil rapide pour monter des visuels de replay sans passer par plusieurs logiciels ou manipulations manuelles repetitives.

Le logiciel doit :

- centraliser imports, placement, typo, previews et exports
- reduire les erreurs d'export
- conserver des comportements tres specifiques au metier
- permettre de revenir sur un projet sauvegarde

## Cibles

- operateur replay
- graphiste / habillage TV
- personne chargee de produire des visuels derivatifs depuis un kit unique

## Scope actuel

Dans le scope :

- `KIT Replay`
- `TOP`
- imports fond / personnages / logo
- `logo texte`
- typo locale + ajout DaFont
- gabarits et previews
- exports images
- snapshots projet et autosafe

Hors scope pour l'instant :

- tests automatises complets
- architecture multi-fichiers mature
- API distante
- moteur plugin
- packaging installeur complet

## Contraintes metier

- les exports doivent respecter des noms precis
- certaines validations doivent bloquer l'export
- les templates TOP doivent garder leur placement exact
- les typos "personal use only" ne doivent pas polluer le flux normal
- l'utilisateur travaille en iteration courte et veut un feedback visuel immediat

## Resultats attendus

Le projet est considere en bon etat si :

- le flux `import -> preview -> export` reste rapide
- les presets sortent des fichiers correctement nommes
- les snapshots permettent de recharger un travail sans surprise
- le `logo texte` reste stable en preview et export
- `TOP` peut vivre en autonomie sans casser `KIT Replay`
