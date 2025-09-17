# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['professional_dashboard_api.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates')],
    hiddenimports=['flask', 'selenium', 'pandas', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'jax', 'jaxlib', 'PIL', 'Pillow', 'gradio', 'imageio', 'scikit-image', 'rembg', 'torchvision', 'torch'],
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
    name='LinkedInAutoBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=['vcruntime140.dll', 'msvcp140.dll', 'vcruntime140_1.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'api-ms-win-*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
