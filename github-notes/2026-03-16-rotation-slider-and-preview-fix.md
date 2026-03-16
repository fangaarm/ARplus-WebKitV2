# Rotation slider and bottom preview fix

## Summary
- replaced the character rotation buttons with a centered horizontal slider from `-180` to `180`
- kept the live angle readout next to the slider so the current value remains visible
- wired the slider to live preview updates while keeping the final refresh on release
- fixed the bottom preset preview pipeline regression that was causing `N/A` thumbnails after the rotation export changes
- preserved the same character rotation behavior in preview and export

## Notes
- the slider starts at `0`, so the handle sits in the middle by default
- the thumbnail fix comes from making the export renderer return a safe value even when a character layer has no source image

## Validation
- `py -3.11 -m py_compile ARPlus.py`
