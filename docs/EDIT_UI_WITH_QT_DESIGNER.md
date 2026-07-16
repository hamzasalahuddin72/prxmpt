# Editing the prxmpt popup with Qt Widgets Designer

The running popup is defined by:

`src/clearcue/assets/prxmpt-main.ui`

This is an ordinary Qt Designer form loaded directly by PySide6 at runtime. You
can change the layout without editing generated Python or rebuilding the Windows
installer after every adjustment.

## One-time Windows setup

Open PowerShell in the source folder:

```powershell
py -3.12 -m venv .venv-ui
.\.venv-ui\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ui\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv-ui\Scripts\pyside6-designer.exe
```

Open `src\clearcue\assets\prxmpt-main.ui` in Designer.

## Previewing changes

Save the `.ui` file, close the running source instance of prxmpt, then run:

```powershell
.\.venv-ui\Scripts\python.exe -m clearcue.main
```

An installer rebuild is only needed when the patch is ready to distribute.

## Reference geometry

The form uses a fixed logical canvas. Do not change the outer canvas unless a
new approved reference size replaces it.

| Object | Position | Size |
|---|---:|---:|
| `TransparentRoot` | `0, 0` | `551 × 827` |
| `PopupHeader` | `20, 12` | `515 × 64` |
| `AudioCard` | `20, 12` inside the body | `166 × 178` |
| `QuestionCard` | `192, 13` inside the body | `350 × 178` |
| `AnswerCard` | `10, 203` inside the body | `532 × 393` |
| `HistoryCard` | `8, 607` inside the body | `537 × 132` |

The body begins at `0, 77`, so its child coordinates correspond to the approved
SVG positions. On a smaller work area, the application scales the whole fixed
canvas uniformly instead of allowing individual sections to stretch.

## Safe editing rules

- Keep every outer section's minimum and maximum size identical.
- Edit spacer widths numerically for exact alignment.
- Keep the existing object names; Python signal wiring and the QSS theme use
  them to find and style controls.
- Keep image files beside the `.ui` file. Designer and the runtime loader use
  that folder as their resource working directory.
- Do not run `pyside6-uic` and then edit its generated Python output. The app
  loads the `.ui` source directly.
- `ToggleSwitch` is a custom Python control. Designer may display it as a custom
  widget placeholder, while the running app renders the approved switch asset.

## Styling and functionality

- Change geometry, margins and widget hierarchy in `prxmpt-main.ui`.
- Change colours, borders, fonts and radii in `src/clearcue/ui/theme.py`.
- Change icons in `src/clearcue/assets/` while preserving their filenames, or
  update both the `.ui` reference and `main_window.py` asset mapping.
- Keep button actions, transcription state and meeting history logic in
  `src/clearcue/ui/main_window.py`.
