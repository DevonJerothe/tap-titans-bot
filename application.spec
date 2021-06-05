# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['application.py'],
    pathex=['C:\\Users\\Votum\\repos\\tap-titans-bot'],
    binaries=[],
    datas=[
        ('C:\\Users\\Votum\\repos\\tap-titans-bot\\media\\flame.ico', 'media'),
    ],
    hiddenimports=[
        "sentry_sdk.integrations.stdlib",
        "sentry_sdk.integrations.django",
        "sentry_sdk.integrations.flask",
        "sentry_sdk.integrations.bottle",
        "sentry_sdk.integrations.falcon",
        "sentry_sdk.integrations.sanic",
        "sentry_sdk.integrations.celery",
        "sentry_sdk.integrations.rq",
        "sentry_sdk.integrations.aiohttp",
        "sentry_sdk.integrations.tornado",
        "sentry_sdk.integrations.sqlalchemy",
        "sentry_sdk.integrations.excepthook",
        "sentry_sdk.integrations.dedupe",
        "sentry_sdk.integrations.modules",
        "sentry_sdk.integrations.argv",
        "sentry_sdk.integrations.logging",
        "sentry_sdk.integrations.threading",
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
    name='ttb',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='media\\flame.ico',
)
