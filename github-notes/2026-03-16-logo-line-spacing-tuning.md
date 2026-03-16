## Logo line spacing tuning

### Summary
- Adjusted logo text line spacing so the rendered effect is stronger than the displayed UI value.
- The UI still shows the same values such as `20`, `40`, `60`, `80`, `100`, but the real spacing applied in rendering is doubled internally.

### Why this change
- The visible result was too subtle compared to the selected line spacing value.
- This made the spacing controls feel weaker than expected in both preview and export.

### Fix
- Added `_logo_line_spacing_effective_offset()`.
- The selected line spacing value is still stored and displayed as before.
- The rendering engine now uses double that value when computing the line spacing ratio.

### Validation
- `py -3.11 -m py_compile ARPlus.py`
