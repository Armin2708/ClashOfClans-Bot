# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ClashOfClansBot macOS .app bundle."""

import os

VERSION = os.environ.get('VERSION', '1.0.0')
block_cipher = None

# Collect all template images
template_datas = []
for root, dirs, files in os.walk('templates'):
    for f in files:
        src = os.path.join(root, f)
        dst = root  # preserve directory structure
        template_datas.append((src, dst))

# Collect bundled tools (ADB + Tesseract) — populated by build_macos.sh
tools_datas = []
if os.path.isdir('tools'):
    for root, dirs, files in os.walk('tools'):
        for f in files:
            src = os.path.join(root, f)
            dst = root
            tools_datas.append((src, dst))

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=template_datas + tools_datas,
    hiddenimports=[
        'cv2',
        'numpy',
        'pytesseract',
        'PIL',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'packaging',
        'packaging.version',
        'bot',
        'bot.battle',
        'bot.buildings',
        'bot.config',
        'bot.main',
        'bot.metrics',
        'bot.notify',
        'bot.resources',
        'bot.screen',
        'bot.settings',
        'bot.state_machine',
        'bot.updater',
        'bot.utils',
        'bot.vision',
        'bot.walls',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused heavy PySide6 modules to reduce app size
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DExtras',
        'PySide6.QtBluetooth',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtRemoteObjects',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClashOfClansBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No terminal window
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClashOfClansBot',
)

app = BUNDLE(
    coll,
    name='ClashOfClansBot.app',
    icon='icon.icns',
    bundle_identifier='com.cocbot.clashofclansbot',
    info_plist={
        'CFBundleName': 'ClashOfClansBot',
        'CFBundleDisplayName': 'Clash of Clans Bot',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
    },
)
