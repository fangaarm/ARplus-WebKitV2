# ARplus-WebKitV2

Application desktop Python **ARPlus** pour composition visuelle multi-calques et export multi-formats.

## Lancer l'application

```bash
python3 -m pip install PySide6 Pillow
python3 ARPlus.py
```

## Fonctionnalités principales

- UI en français (ressources, contrôles de calques, exports, logs).
- Canvas de preview temps réel avec déplacement des calques et scaling via slider ou `Ctrl + molette`.
- Presets d'export fixes : Poster, FullScreen+Logo, Hero Banner, Logo, Background, Background (no logo).
- Transformations stockées **par preset** (`state[preset_id].layers[layer_id].transform` conceptuellement).
- Import images PNG/JPG/JPEG/WEBP.
- Logo image ou logo texte.
- Export haute qualité via Pillow + LANCZOS avec avertissement d'upscale.

## Structure

```text
/ARplus-WebKitV2
  ARPlus.py
  /data
    project.json
  /exports
```
