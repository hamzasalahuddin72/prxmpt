# ClearCue installation and first-run guide

ClearCue is a Windows interview-practice and disclosed meeting coach. It captures
the Windows output device and microphone, transcribes speech locally, detects
questions and builds suggestions grounded in context you provide.

It is not designed to conceal itself from screen sharing, proctoring or other
participants. Confirm that transcription is permitted and inform participants
where required.

## System requirements

- Windows 10 or Windows 11, 64-bit
- At least 8 GB RAM; 16 GB recommended for the larger speech models
- Headphones strongly recommended
- Internet access for the initial Python/package and Whisper-model downloads
- Optional: OpenAI API key or a local Ollama installation
- Optional: VoiceMeeter for advanced routing; it is not required or bundled

## Option 1 — install and run from this source package

This is the quickest way to test the application before producing an installer.

1. Install 64-bit Python 3.12 from <https://www.python.org/downloads/windows/>.
2. During Python installation, select **Add Python to PATH** and install the
   Python Launcher.
3. Extract the ClearCue ZIP to a normal folder such as `Documents\ClearCue`.
4. Double-click `INSTALL_AND_RUN.bat`.
5. Wait while the private environment and packages are installed.

Future launches can use the same `INSTALL_AND_RUN.bat`. It reuses the existing
environment rather than downloading everything again.

## Option 2 — create the ClearCue 1.0.7 update installer

The supplied build creates a self-contained Windows application. End users do
not need Python after installing that build.

1. Extract this project to a folder whose path does not contain unusual symbols.
2. Double-click `BUILD_INSTALLER.bat`.
3. If Python 3.12 is missing, the script installs it through Windows Package
   Manager. Approve the Windows prompt if one appears. If the script asks you to
   restart it after Python installation, close the window and double-click the
   builder again.
4. The script verifies or repairs its isolated build environment, installs build
   dependencies, runs the tests and builds the PyInstaller application.
5. If Inno Setup is missing, the script installs it through Windows Package
   Manager. Approve the Windows prompt if one appears. If Windows Package
   Manager is unavailable, install Inno Setup manually from
   <https://jrsoftware.org/isdl.php> and run the builder again.
6. The finished installer appears at:

   `installer\output\ClearCueUpdate_1.0.7.exe`

You can also run the build directly from PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

PyInstaller must build a Windows executable on Windows. The included GitHub
Actions workflow can perform the same build on a Windows runner and return the
installer as a workflow artifact. Pushing a version tag such as `v1.0.7` also
publishes the installer as a permanent GitHub Release for the in-app updater.

If a previous build was interrupted and left a broken `.venv-build` folder, the
builder now detects and replaces that folder automatically. You do not need to
delete it yourself.

## First-run configuration

### 1. Create a profile

Open the gear menu and choose **Profiles and context**, then create a profile for
the role you are practising. Import:

- Your current CV
- The target job description
- Project summaries
- Verified STAR examples
- Company and role notes

Supported files are PDF, DOCX, TXT and Markdown. Text is stored locally in the
ClearCue database.

### 2. Configure audio

Open **Settings → Audio**.

- **Meeting/system audio:** select the same speakers or headphones used by
  Teams, Zoom or your browser.
- **Your microphone:** select the microphone you will speak into.

ClearCue uses Windows WASAPI loopback for meeting audio and PortAudio for the
microphone. This hybrid backend avoids the SoundCard format assertion produced
by some USB, headset and virtual microphone drivers. If VoiceMeeter is installed,
its virtual devices appear in the same lists and can be selected normally.

Use headphones. Playing meeting audio through speakers may cause the microphone
to hear it again and produce duplicate transcripts.

### 3. Choose transcription settings

The recommended default for an ordinary laptop is:

- Model: `tiny.en`
- Device: CPU
- Compute type: `int8`

The model downloads the first time a listening session starts. This can take a
few minutes. Later sessions use the cached model under the user's local ClearCue
application-data folder.

For a compatible NVIDIA GPU, try CUDA and `float16`. If the CUDA runtime or its
DLLs are unavailable, ClearCue automatically reloads the current model on
CPU/`int8` and retries the interrupted segment once.

### 4. Updates

ClearCue checks the public GitHub Release feed shortly after launch and every
six hours while running. A Windows tray notification appears when a stable newer
version exists. Open the gear menu and choose the available update to download it,
verify its SHA-256 digest, stop listening safely and update in place. Profiles,
context, settings, model files and history are preserved.

Use **Gear → Check for updates** to check immediately. Automatic checks can be
disabled under **Settings → Updates**. Update installation always requires
confirmation.

### 5. Choose an answer provider

ClearCue offers three modes:

1. **Local grounded outline:** no API key and no context leaves the computer.
   This produces verified talking points rather than a polished AI response.
2. **OpenAI Responses API:** enter an OpenAI API key and choose a model. The key
   is saved in Windows Credential Manager, not in `settings.json`.
3. **Ollama:** run Ollama locally, enter its address and choose an installed
   model such as `qwen3:8b`.

OpenAI API usage is billed separately from ChatGPT subscriptions.

## Starting a practice session

1. Start the Teams, Zoom or browser test call.
2. Leave the blue microphone and speaker buttons enabled for both sources, or
   disable either source by clicking its button.
3. Click the centre three-dot pill. Confirm permission the first time ClearCue
   asks; the pill displays `LIVE` while listening.
4. Detected questions appear in the upper question field.
5. Click **Answer** or enable the **Auto answer** switch.
6. Click the `LIVE` pill again when finished. Recent meetings appear at the
   bottom with transcript, generated-answer and delete controls.
7. The red X hides ClearCue in the system tray; use the tray icon to reopen or
   quit it.

Global shortcuts:

- `Ctrl+Alt+S` — start or stop listening
- `Ctrl+Alt+A` — generate an answer for the current question
- `Ctrl+Alt+O` — show or hide the popup

## Privacy behaviour

- Raw audio is processed in memory and is never saved.
- Session transcripts are local and can be disabled in Settings.
- Saved sessions can be viewed, exported or deleted from History.
- API keys use Windows Credential Manager.
- Local-outline and Ollama modes can operate without sending context to OpenAI.
- In OpenAI mode, the current question and selected context excerpts are sent to
  the configured API.
- Diagnostic logs do not intentionally include transcript or answer content.

## Troubleshooting

### No meeting audio level

- Confirm that the meeting is playing through the output selected in Settings.
- Refresh the audio-device list after connecting a headset.
- Avoid changing the Windows output device after starting a session.
- Close applications holding the device in exclusive mode.
- If direct loopback remains unreliable, configure VoiceMeeter and select its
  virtual output from ClearCue.

### Bluetooth headset behaves strangely

Windows may expose separate Stereo and Hands-Free profiles. Select the same
profile used by the meeting application. Wired or USB headphones usually give
more reliable simultaneous playback and microphone capture.

### First transcription takes a long time

The local model is downloading or loading. Keep `tiny.en` for minimum latency,
or try `base.en` when you want more accuracy and the computer can keep up. If an
interrupted download leaves `model.bin` missing, ClearCue 1.0.7 removes only the
incomplete model cache and retries the download once.

### CUDA or CTranslate2 error

Select CPU and `int8`. GPU mode requires compatible NVIDIA libraries that are
not bundled by the basic installer. ClearCue 1.0.7 also performs this fallback
automatically if CUDA fails during the first inference.

### OpenAI answer fails

- Confirm that the API key is an OpenAI Platform API key.
- Check the model name and account access.
- Confirm internet access and available API credit.
- Switch to Local grounded outline to verify the rest of the application.

### Windows SmartScreen warning

Locally built applications are unsigned. For public distribution, sign both
`ClearCue.exe` and `ClearCueUpdate_1.0.7.exe` with an Authenticode code-signing
certificate. Do not advise users to bypass organisational security controls.

## Uninstalling

Installer builds can be removed from **Windows Settings → Apps → Installed
apps → ClearCue**. The uninstaller removes program files. User-created context,
settings and history remain in the local ClearCue application-data directory so
an update does not delete them. Remove that folder manually only if you also
want to erase all ClearCue data.
