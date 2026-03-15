# Clarify / Checklist

## Questions a clarifier avant une grosse evolution

- Quelle est la source de verite fonctionnelle quand `ARPlus.py` et `TopAR+.py` divergent ?
- Quelles variantes d'export sont obligatoires, optionnelles, ou historiques seulement ?
- Quelle logique de nommage est contractuelle et ne doit jamais bouger ?
- Jusqu'ou l'app doit-elle tolerer des assets imparfaits avant de bloquer l'export ?
- Quelle politique garder pour DaFont : outil d'appoint ou vrai flux supporte sur le long terme ?
- Faut-il figer certains assets / gabarits par version de projet ?
- Quel comportement exact doit etre conserve entre preview et export si les deux ne matchent pas au pixel pres ?

## Checklist produit

- [ ] Les noms d'onglets sont stabilises (`KIT Replay`, `TOP`)
- [ ] Les libelles UI critiques sont coherents
- [ ] Les valeurs par defaut sont lisibles pour un usage prod
- [ ] Les erreurs bloquantes d'export sont explicites
- [ ] Les actions courantes ont un feedback clair

## Checklist assets

- [ ] Les dossiers `asset/*` sont ranges par fonction
- [ ] Les noms des gabarits sont normalises
- [ ] Les templates TOP sont bien identifies
- [ ] Les typos locales sont rangees proprement
- [ ] Les caches techniques ne sont pas confondus avec les assets source

## Checklist export

- [ ] Les espaces sont remplaces par `-` dans les noms de fichiers
- [ ] Les variantes `POSTER`, `poster-info`, `poster-info-nologo`, `poster-nologo` sont documentees
- [ ] Les exports TOP sont homogones
- [ ] `metadata.json` suit les sorties reelles
- [ ] Les cas bloquants sont testes manuellement

## Checklist etat / persistance

- [ ] `ui_state.json` garde seulement l'etat UI utile
- [ ] les snapshots `.arplus.json` restent retro-compatibles autant que possible
- [ ] les derniers dossiers utilises sont bien restaures
- [ ] les resets projet ne reintroduisent pas des valeurs obsoletes

## Checklist technique

- [ ] toute nouvelle modif passe `py -3.11 -m py_compile ARPlus.py`
- [ ] les flux critiques sont verifies en smoke test GUI ou offscreen
- [ ] les changements ne dupliquent pas encore plus la logique existante
- [ ] les comportements legacy repris de `TopAR+.py` sont notes
