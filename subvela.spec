# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SubVela — subtitle generator desktop app.
Build:  pyinstaller subvela.spec
Output: dist/SubVela/SubVela.exe
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Paths ────────────────────────────────────────────────────────────
ROOT = SPECPATH

# ── Hidden imports ───────────────────────────────────────────────────
hiddenimports = [
    # customtkinter internals
    *collect_submodules("customtkinter"),
    # transformers tokenizer internals used by local NLLB
    *collect_submodules("transformers"),
    # tkinterdnd2
    "tkinterdnd2",
    # faster-whisper and its backend
    "faster_whisper",
    "ctranslate2",
    # huggingface download support
    "huggingface_hub",
    # cloud transcription
    "groq",
    "openai",
    "google.genai",
    "anthropic",
    # video / image
    "cv2",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    # media players
    "mpv",
    "vlc",
    # font tools
    "fontTools",
    "fontTools.ttLib",
    "transformers",
    "sentencepiece",
    "langdetect",
    # misc
    "dotenv",
    "keyring",
    "keyring.backends",
    "tqdm",
    "tqdm.auto",
    # RTL / BiDi text processing
    "arabic_reshaper",
    "bidi",
    "bidi.algorithm",
]

# ── Data files ───────────────────────────────────────────────────────
def optional_asset(name):
    p = os.path.join(ROOT, "assets", name)
    if os.path.exists(p):
        return [(p, "assets")]
    else:
        print(f"WARNING: assets/{name} not found, skipping")
        return []

datas = [
    # customtkinter assets (themes, icons)
    *collect_data_files("customtkinter"),
    # tkinterdnd2 Tcl/Tk package
    *collect_data_files("tkinterdnd2"),
    # arabic-reshaper font data
    *collect_data_files("arabic_reshaper"),
    # app assets
    (os.path.join(ROOT, "assets", "favicon.ico"), "assets"),
    (os.path.join(ROOT, "assets", "presets.json"), "assets"),
    *optional_asset("user_presets.json"),
    *optional_asset("config.json"),
]

# ── Binaries ─────────────────────────────────────────────────────────
binaries = []
for bin_name in ["libmpv-2.dll", "ffmpeg.exe", "ffprobe.exe"]:
    bin_path = os.path.join(ROOT, bin_name)
    if os.path.exists(bin_path):
        binaries.append((bin_path, "."))
    else:
        print(f"WARNING: {bin_name} not found in project root, skipping")

# ── Analysis ─────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "tensorflow",
        "tensorflow_cpu",
        "tensorflow-gpu",
        "tensorboard",
        "keras",
        "lightning",
        "pytorch_lightning",
        "pyannote",
        "pyannote.audio",
        "torch",
        "torchaudio",
        "torchvision",
        "openvino",
        "notebook",
        "jupyter",
        "IPython",
        "pytest",
        "tkinter.test",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SubVela",
    icon=os.path.join(ROOT, "assets", "favicon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # windowed app, no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SubVela",
)
