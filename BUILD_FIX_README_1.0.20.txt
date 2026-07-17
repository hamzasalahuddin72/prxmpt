prxmpt 1.0.20 BUILD FIX (SECOND CORRECTION)
===========================================

This correction fixes the case where the tiny.en download completes but
PyInstaller immediately reports that config.json, model.bin, and tokenizer.json
are missing. The previous spec walked one directory too far upward when
resolving the repository root.

The failed build did not damage the virtual environment or tiny.en model.

1. Close the failed builder window.
2. Extract the build-fix ZIP directly into the ClearCue project folder:
   C:\Users\hamza\Desktop\GitHub\ClearCue
3. Allow Windows to replace scripts\prxmpt.spec (and any other included files).
4. Confirm this file now exists:
   scripts\prxmpt.spec
5. Run BUILD_UPDATE_V1.0.20.bat again.

The builder will reuse .venv-build and build\models. It may briefly verify
dependencies, but it should not need to redownload the 78 MB speech model.
