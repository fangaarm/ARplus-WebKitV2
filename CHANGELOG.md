# Changelog

## 2026-03-15

### Interface
- Correction du crash au lancement lie a `_build_import_toolbar`.
- Ajout d'une barre d'import bleue au-dessus de la preview.
- Organisation de la barre d'import en groupes distincts : `Importer fond`, personnages, puis `Importer logo`.
- Ajout de separateurs visuels entre les groupes d'import.
- Renommage et simplification du panneau gauche en `Gestionnaire des gabarits`.
- Deplacement de `Controles de calque` a droite, juste au-dessus de `Exports`.
- Passage du bloc `Exports` sur 2 colonnes pour gagner de la place.
- Reorganisation des boutons lies aux typos pour eviter l'ecrasement visuel.

### Projet et fichiers
- Memorisation du dernier dossier utilise pour l'import.
- Memorisation du dernier dossier utilise pour l'export.
- Memorisation du dernier dossier utilise pour la sauvegarde projet.
- Ajout de `Importer projet...` pour recharger un fichier `.arplus.json`.
- Memorisation du dernier dossier utilise pour le chargement projet.
- Sauvegarde et restauration du dossier d'export dans les snapshots projet.
- Autosave de securite avant certaines operations de reset et de chargement projet.

### Calques et personnages
- Correction de la selection souris des PNG personnages pour ne prendre que les pixels visibles.
- Les zones transparentes des personnages ne bloquent plus la prise en main.
- Amelioration du deplacement des personnages superposes.
- Import de `character2`, `character3` et `character4` avec comportement proche du personnage principal.
- Repartition automatique des personnages charges pour qu'ils se laissent de la place dans le gabarit.
- Conservation d'un ancrage bas pour le placement auto des personnages.
- Prise en compte du vide transparent au-dessus de la tete dans le placement auto.
- Prise en compte plus juste des largeurs visibles pour les PNG detoures.
- Ajout du support `Ctrl+Z` pour les actions principales du projet.

### Logo texte
- Correction du placement du `logo texte` dans les zones `logo` des gabarits.
- Correction du placement du `logo texte` dans le preset `Logo`.
- Collage du `logo texte` sur le bord bas et le bord gauche du preset `Logo`.
- Reduction du `logo texte` avec un point d'ancrage bas-gauche visible.
- Redimensionnement du `logo texte` pour eviter tout depassement du cadre.
- Uniformisation de la logique preview/export du `logo texte`.
- Correction des cas ou certaines typos faisaient flotter le texte dans le preset `Logo`.
- Correction des cas ou l'ombre du logo faisait sortir le rendu du cadre.
- Refit automatique du logo quand les reglages d'ombre changent.
- Case `Majuscule` activee par defaut.
- Debounce sur la frappe du texte logo pour limiter la latence de recalcul.
- Correction du changement d'alignement qui reagissait mal.
- Suppression du champ `Taille` dans l'interface, avec valeur interne par defaut conservee a `300`.

### Typos locales
- Remplacement du flux principal DaFont par une bibliotheque locale dans `asset/Typographie`.
- Fenetre `Choisir typo` avec apercu genere a partir de la police elle-meme.
- Classement initial des typos locales par style demande.
- Detection automatique des nouvelles typos ajoutees dans `asset/Typographie`.
- Ajout d'une recherche dans la bibliotheque locale.
- Ajout de la suppression d'une typo locale depuis l'interface.
- Filtrage plus propre des variantes pour limiter les doublons.

### Ajout typo / DaFont
- Ajout d'une fenetre `Ajouter une typo` basee sur DaFont FR.
- Navigation par categorie, sous-theme et page.
- Tri alphabetique des sous-themes.
- Tri alphabetique des polices affichees.
- Passage a 25 typos par page logique.
- Filtrage des typos `personal use`, `PERSONAL USE ONLY`, `€` et non compatibles.
- Ajout d'un systeme de verification/cache DaFont en tache de fond.
- Allegement du chargement de la fenetre DaFont pour accelerer son ouverture.
- Suppression du champ de recherche dans `Ajouter une typo`.
- Renommage du bouton `Ajouter DaFont` en `Ajouter typo`.

### Divers
- Stabilisation generale de l'ergonomie autour du logo texte, des gabarits et des imports.
