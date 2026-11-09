# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-directory build for Imprint v6."""

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
ICON = ROOT / "packaging" / "imprint.ico"

datas = []
qml_root = SRC / "imprint" / "ui" / "qml"
for qml_file in qml_root.rglob("*"):
    if qml_file.is_file():
        relative = qml_file.relative_to(qml_root)
        datas.append(
            (
                str(qml_file),
                str(Path("imprint") / "ui" / "qml" / relative.parent),
            )
        )
datas += collect_data_files("insightface")
datas += collect_data_files("onnxruntime")
datas += collect_data_files(
    "PySide6",
    includes=[
        "Qt/qml/**/*",
        "Qt/translations/*.qm",
    ],
)

binaries = []
binaries += collect_dynamic_libs("insightface")
binaries += collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("cv2")

hiddenimports = []
hiddenimports += collect_submodules("insightface")
hiddenimports += [
    "imprint.ui.app",
    "imprint.ui.bridge",
    "imprint.engine.pipeline",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
]

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="Imprint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
    version=str(ROOT / "packaging" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Imprint",
)
