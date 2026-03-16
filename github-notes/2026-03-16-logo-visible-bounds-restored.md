## Logo visible-bounds placement restored

### Summary
- Restored visible-bounds based placement for the `logo` preset.
- Kept the separate fix that neutralizes Qt HiDPI filename suffix handling such as `@2x` and `@3x`.

### Why this change
- The temporary fallback to full-frame placement was added while investigating tiny logos.
- The real root cause turned out to be Qt's automatic HiDPI handling for filenames containing suffixes like `@3x`.
- Once the HiDPI filename issue was fixed, the fallback became unnecessary and caused the logo preset to align against the full image frame instead of the true visible content.

### Fix
- Removed the fallback that forced full-frame/bottom placement for some imported logos.
- Restored the `bottom_left_visible` placement mode for the `logo` preset so the app positions the logo from its visible content bounds again.
- This keeps the original intended logo framing while preserving the HiDPI filename import fix.

### Validation
- `py -3.11 -m py_compile ARPlus.py`
