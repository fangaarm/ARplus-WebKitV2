# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ARPlus.py'],
    pathex=[],
    binaries=[],
    datas=[('asset', 'asset'), ('data', 'data')],
    hiddenimports=['PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name='KitReplay-AR+',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['asset\\logo\\arplus.ico'],
)
