## HiDPI filename import fix

### Summary
- Fixed imported images being displayed too small when their filenames contained Qt HiDPI suffixes such as `@2x` or `@3x`.
- This notably affected some logos that appeared tiny and stuck near the upper-left area after import.

### Root cause
- Qt automatically interprets filenames ending with patterns like `@2x` and `@3x` as high-DPI assets.
- When loaded as `QPixmap`, those files keep their raw pixel dimensions but also receive a `devicePixelRatio` greater than `1.0`.
- `QGraphicsPixmapItem` then renders them using the device-independent size, which makes them appear smaller than expected.

### Fix
- Added `_load_user_pixmap()` for user-imported images.
- The loader now normalizes `QPixmap.devicePixelRatio()` back to `1.0` for imported assets.
- This keeps the visual size consistent with the real image pixels, regardless of filename conventions.

### Validation
- `py -3.11 -m py_compile ARPlus.py`
- Confirmed separately with Qt that files named `*@3x.png` are rendered at one-third of their apparent size unless the device pixel ratio is reset.
