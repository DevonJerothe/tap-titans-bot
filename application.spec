# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

repository = "<REPO_DIR>"
environment = "<ENV_DIR>"

a = Analysis(
    ['application.py'],
    pathex=[repository],
    binaries=[],
    datas=[
        (repository + '\\media\\flame.ico', 'media'),
        (repository + '\\database\\migrations', 'database\\migrations'),
        (repository + '\\bot\\data\\images', 'bot\\data\\images'),
        (repository + '\\bot\\data\\schema', 'bot\\data\\schema'),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='taptitansbot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='media\\flame.ico',
)
