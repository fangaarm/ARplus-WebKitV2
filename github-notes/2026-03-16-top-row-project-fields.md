## Top row project fields layout

### Summary
- Moved `ID` and `Nom du projet` onto the same top row as the preset preview selector.
- Pushed the `Gabarit en apercu` selector to the right side of that row.
- Removed the duplicate `ID` and project name fields from the exports panel on the right.

### Why this change
- The project metadata fields are used often and fit better near the main working area.
- The preset selector reads more clearly when it stays grouped on the right side of the row.
- This reduces duplication and frees space in the exports panel.

### Fix
- Created the shared metadata inputs earlier in `_build_ui()`.
- Added `ID` and `Nom du projet` to the canvas top row.
- Kept the preset combo on the same line, aligned to the right with a stretch spacer.
- Removed the metadata widgets from `_build_exports_box()`.

### Validation
- `py -3.11 -m py_compile ARPlus.py`
