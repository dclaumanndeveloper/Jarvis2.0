# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('jarvis.gif', '.'),
        ('models', 'models'),
        ('web', 'web'),
        ('documents', 'documents'),
        ('services', 'services'),
        ('Orbitron-Regular.ttf', '.'),
        ('interface_bg.webp', '.'),
        ('.env', '.')
    ],
    hiddenimports=[
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.QtCore', 'PyQt6.QtWebChannel',
        'pyautogui', 'pygetwindow', 'screeninfo', 'PIL', 'numpy', 'psutil', 'aiohttp',
        'sentence_transformers', 'llama_cpp', 'playwright'
    ],
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
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='Jarvis2.0',
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
    icon='jarvis.gif' # gif as icon placeholder
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Jarvis2.0'
)
