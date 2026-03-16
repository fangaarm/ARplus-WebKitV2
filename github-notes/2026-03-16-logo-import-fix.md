## Logo import placement fix

### Summary
- Fixed a regression in the `logo` preset where some imported logos were placed too small in the upper-left area.
- Added a safer placement rule that distinguishes transparent logo assets from logos that effectively fill their full image bounds.

### Root cause
- The `logo` preset had a special placement mode called `bottom_left_visible`.
- That mode works well when the logo file has real transparent margins, because the app can align the visible content instead of the full image rectangle.
- For logos that do not expose meaningful transparent margins, the app treated the whole image as visible content and pinned it from the left edge, which made some logos appear small and stuck near the upper-left area.

### Fix
- Added `_logo_has_meaningful_transparent_margins()` to detect whether the imported logo really has useful transparent padding.
- The `logo` preset now:
  - keeps `bottom_left_visible` only for logos with meaningful transparent margins,
  - falls back to a centered bottom placement for logos that behave like full-frame images.
- This preserves the improved behavior for transparent logo assets while avoiding bad placement for opaque or tightly bounded logos.

### Validation
- `py -3.11 -m py_compile ARPlus.py`
