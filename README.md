# ClearCue

ClearCue is a native Windows interview-practice and disclosed meeting coaching
assistant written in Python and PySide6. It provides local system-audio capture,
microphone capture, local speech-to-text, question detection, context retrieval,
grounded answer generation, a visible always-on-top overlay and local session
history.

See [README_INSTALLATION.md](README_INSTALLATION.md) for the complete Windows
installation, first-run and troubleshooting guide.

## Product boundaries

ClearCue deliberately does not implement screen-capture exclusion, screen-share
evasion, DLL injection, proctoring bypass or hidden processes. Its overlay is an
ordinary transparent Windows window and should be used for practice or in
contexts where assistance and transcription are allowed.

## Main capabilities

- WASAPI loopback meeting-audio capture through SoundCard
- Separate microphone channel and speaker labels
- In-memory resampling and utterance segmentation
- Local faster-whisper transcription
- Interview-question detection
- PDF, DOCX, TXT and Markdown context ingestion
- Lightweight local context retrieval without a framework dependency
- Local grounded-outline mode
- OpenAI Responses API provider
- Local Ollama provider
- PySide6 dashboard and adjustable always-on-top overlay
- SQLite profiles, documents and optional transcript history
- API-key storage through Windows Credential Manager
- PyInstaller and Inno Setup build pipeline
- Windows GitHub Actions build workflow

## Architecture

```text
WASAPI loopback + microphone
            |
     capture and downmix
            |
     16 kHz resampling
            |
    speech segmentation
            |
      faster-whisper
            |
     question detection
            |
context retrieval from SQLite
            |
 local / OpenAI / Ollama provider
            |
 dashboard + visible overlay
```

Raw audio is not persisted. Transcription and answer generation run away from
the Qt interface thread so the window remains responsive.

## Source layout

```text
src/clearcue/
├── audio/          # devices, capture, VAD segmentation and transcription
├── documents/      # PDF/DOCX/text ingestion and chunking
├── intelligence/   # question detection, retrieval, prompts and providers
├── services/       # session orchestration and shortcuts
├── storage/        # SQLite persistence
├── ui/             # PySide6 dashboard, dialogs and overlay
├── config.py
├── paths.py
├── security.py
└── main.py
```

## Developer setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m clearcue.main
```

The application can also be launched using `INSTALL_AND_RUN.bat`.

## Build pipeline

`scripts/build_windows.ps1` performs the reproducible Windows build:

1. Creates a dedicated build environment.
2. Installs application and development dependencies.
3. Runs the unit tests.
4. Builds an onedir PyInstaller application.
5. Compiles `installer/ClearCue.iss` with Inno Setup.
6. Produces `installer/output/ClearCueUpdate_1.0.5.exe`.

An onedir application is intentionally used behind the single installer. Large
Qt and AI dependencies start more reliably this way than when every dependency
is unpacked from a PyInstaller one-file executable at each launch.

## OpenAI implementation

The optional OpenAI provider uses the Responses API:

```python
response = client.responses.create(
    model=model,
    instructions=SYSTEM_INSTRUCTIONS,
    input=prompt,
)
answer = response.output_text
```

The model name is user-configurable so an installer does not need to be rebuilt
when model access or preferences change.

## Testing

The test suite covers:

- configuration persistence
- document chunking
- question detection
- context ranking
- grounded local output
- SQLite profile, context and transcript lifecycle
- audio resampling and segmentation helpers

Audio-device enumeration, live WASAPI capture, PyInstaller output and the Inno
Setup installer must additionally be tested on a clean Windows 10/11 machine.
