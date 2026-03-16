# Character rotation controls in layer panel

## Summary
- added clockwise and anticlockwise rotation buttons in the `Controles de calque` panel
- added a live angle readout so the current character rotation stays visible while editing
- limited rotation controls to character layers only (`Perso`, `2`, `3`, `4`)
- applied character rotation in the live preview so the viewport matches the requested angle
- applied the same character rotation in export rendering and export validation so preview and final output stay aligned
- reset character rotation to `0` when a fresh auto-placement is applied from import/guides

## Notes
- rotation uses 5-degree steps per click
- non-character layers keep the existing behavior and do not expose the rotation buttons

## Validation
- `py -3.11 -m py_compile ARPlus.py`
