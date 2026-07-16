from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


project_root = Path(SPECPATH).parent
if project_root.name == "build":
    project_root = project_root.parent

hiddenimports = []
hiddenimports += collect_submodules("keyring.backends")
hiddenimports += collect_submodules("pynput")
hiddenimports += [
    "soundcard.mediafoundation",
    "sounddevice",
    "_sounddevice_data",
    "faster_whisper",
]

datas = collect_data_files("faster_whisper")
datas += collect_data_files("_sounddevice_data")
datas += collect_data_files("clearcue", includes=["assets/*"])
model_dir = project_root / "build" / "models" / "faster-whisper-tiny.en"
required_model_files = ("config.json", "model.bin", "tokenizer.json")
missing_model_files = [name for name in required_model_files if not (model_dir / name).is_file()]
if missing_model_files:
    raise RuntimeError(
        "Bundled tiny.en model is incomplete. Run scripts/fetch_tiny_model.py first; "
        f"missing: {', '.join(missing_model_files)}"
    )
datas += [(str(model_dir), "models/faster-whisper-tiny.en")]
binaries = collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("_sounddevice_data")

a = Analysis(
    [str(project_root / "src" / "clearcue" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(project_root / "build" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pandas", "scipy", "torch", "tensorflow"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="prxmpt",
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
    icon=str(project_root / "src" / "clearcue" / "assets" / "prxmpt.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="prxmpt",
)
