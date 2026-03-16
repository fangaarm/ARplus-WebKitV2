# UI theme, previews and TOP view polish

## Summary
- reduced the preset preview thumbnails by about 25 percent to lighten the bottom strip
- added a dark/light UI theme switch in the top-right toolbar and persisted the choice in `ui_state.json`
- added standard Qt icons to the main export/project action buttons to make the right-side menu clearer
- kept the TOP workspace centered and fit-scaled when entering the `TOP` tab
- replaced the harsh white preview surround with a softer light gray
- added a light red warning fill in the main preview when the current preset has the same kind of layout issue that would block export (background/visual not filling the frame, or a character not touching the bottom)
- updated preset thumbnail cards so their colors follow the current light/dark theme

## Notes
- preview warning detection is debounced to limit extra work while editing
- the feedback is applied to the main ARPlus preview without changing export rules
- no executable rebuild was done in this change set

## Validation
- `py -3.11 -m py_compile ARPlus.py`
