# prxmpt

prxmpt is a native Windows interview-practice and disclosed meeting coaching
assistant written in Python and PySide6. It provides local system-audio capture,
microphone capture, local speech-to-text, question detection, context retrieval,
grounded answer generation, a compact always-on-top popup and local session
history.

See [README_INSTALLATION.md](README_INSTALLATION.md) for the complete Windows
installation, first-run and troubleshooting guide.

## Product boundaries

prxmpt deliberately does not implement screen-capture exclusion, screen-share
evasion, DLL injection, proctoring bypass or hidden processes. Its popup is an
ordinary visible Windows window and should be used for practice or in
contexts where assistance and transcription are allowed. The Stealth switch in
1.0.10 is a non-functional placeholder.

## Main capabilities

- WASAPI loopback meeting-audio capture through SoundCard
- PortAudio microphone capture through sounddevice for broader driver compatibility
- Separate microphone channel and speaker labels
- In-memory resampling and utterance segmentation
- Local faster-whisper transcription with bundled `tiny.en` weights
- Interview-question detection
- PDF, DOCX, TXT and Markdown context ingestion
- Lightweight local context retrieval without a framework dependency
- Local grounded-outline mode
- OpenAI Responses API provider
- Local Ollama provider
- Five coordinated fixed-size top-centre PySide6 popup surfaces
- Top-bar-only startup with mutually exclusive Plot and History views
- Uniform whole-cluster downscaling on smaller Windows work areas
- Five editable Qt Widgets Designer forms in `src/clearcue/assets/`
- Exact SVG-derived PNG controls packaged as native Qt button assets
- Independent live microphone and meeting-audio controls
- SQLite profiles, documents, transcripts and generated-answer history
- API-key storage through Windows Credential Manager
- PyInstaller and Inno Setup build pipeline
- Windows GitHub Actions build workflow
- Verified in-app update notifications backed by permanent GitHub Releases

## Architecture

```text
SoundCard loopback + PortAudio microphone
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
 top-centre always-on-top popup
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
├── ui/             # PySide6 popup, tray integration and supporting dialogs
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

To edit the popup visually, run `pyside6-designer` from the same environment and
open any of the five `prxmpt-*.ui` component forms in `src/clearcue/assets/`.
The forms are loaded directly by the application, so saved layout changes can
be tested by restarting the source application without rebuilding an installer. See
[`docs/EDIT_UI_WITH_QT_DESIGNER.md`](docs/EDIT_UI_WITH_QT_DESIGNER.md).

The application can also be launched using `INSTALL_AND_RUN.bat`.

## Build pipeline

`scripts/build_windows.ps1` performs the reproducible Windows build:

1. Creates a dedicated build environment.
2. Installs application and development dependencies.
3. Runs the unit tests.
4. Downloads and validates the distributable `tiny.en` faster-whisper snapshot.
5. Builds an onedir PyInstaller application containing that local speech model.
6. Compiles `installer/prxmpt.iss` with Inno Setup.
7. Produces `installer/output/prxmptUpdate_1.0.10.exe`.

Tagged builds such as `v1.0.10` are also published as permanent GitHub Releases.
Installed clients query the public latest-release endpoint, compare semantic
versions, download in the background and verify GitHub's SHA-256 asset digest
before starting a silent in-place update.

The installed application, executable, shortcuts, tray menu, update installer
and Windows Apps entry now consistently use the `prxmpt` name.

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
- SQLite profile, context, transcript and generated-answer lifecycle
- audio resampling and segmentation helpers
- CUDA-to-CPU transcription recovery
- incomplete Whisper-cache repair
- bundled-model discovery and transcription activity reporting
- pause-based multi-fragment question collection
- fixed Designer geometry, compact-popup scaling and meeting-label helpers
- release parsing, version comparison and update integrity helpers

Audio-device enumeration, live WASAPI/PortAudio capture, PyInstaller output,
in-app update handoff and the Inno Setup installer must additionally be tested
on a clean Windows 10/11 machine.
