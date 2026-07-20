# Editing the prxmpt popup components with Qt Widgets Designer

prxmpt 1.0.24 uses four independent Designer forms in
`src\clearcue\assets`:

Read `docs\UI_BASELINE.md` before changing a form. It is the authoritative
geometry and interaction contract for continued UI development.

| Form | Logical size | Purpose |
|---|---:|---|
| `prxmpt-top-bar.ui` | 720 × 58 | Drag, audio, live status, logo, opacity and window controls |
| `prxmpt-prompt-screen.ui` | 720 × 35 | One-line question field and icon actions |
| `prxmpt-feedback-window.ui` | 720 × 261 | Generated answer, navigation and answer controls |
| `prxmpt-history-popup.ui` | 720 × 164 max | Adaptive one-to-four-row saved-session list |

The application loads these files directly. You can change a component and test
it from source without rebuilding the Windows installer.

## One-time Windows setup

Open PowerShell in the source folder:

```powershell
py -3.12 -m venv .venv-ui
.\.venv-ui\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ui\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv-ui\Scripts\pyside6-designer.exe
```

Open one of the four `.ui` files listed above.

## Previewing changes

Save the form, close the running source instance of prxmpt, then run:

```powershell
.\.venv-ui\Scripts\python.exe -m clearcue.main
```

An installer rebuild is only needed when a patch is ready to distribute.

## Component positioning

The individual component sizes are fixed. The cluster controller positions
them with these logical gaps:

- Top bar to prompt screen: 6 px
- Prompt screen to feedback or history: 6 px
- Feedback and History use the same top-left anchor and are never visible together

History retains the 164 px four-row Designer canvas, but its native window mask
automatically animates to 50, 88, 126 or 164 px according to the number of saved
meetings. Additional meetings use the custom smooth wheel/trackpad scroll area.

Do not add inter-component spacing inside the forms. Shared positioning and
screen-edge clamping are implemented in `src\clearcue\ui\popup_helpers.py`.
The complete cluster scales uniformly on a smaller screen.

## Safe editing rules

- Keep each root widget's minimum and maximum size equal to its reference size.
- Keep existing object names. Python signal wiring and the theme locate widgets
  by these names.
- Keep image files beside the forms. Designer and the runtime loader use that
  directory as their working directory.
- Keep transparent root backgrounds; each component is a frameless native popup.
- Do not run `pyside6-uic` and edit generated Python. prxmpt loads the `.ui`
  source directly.
- `ToggleSwitch` is a custom Python control. Designer can show it as a custom
  widget placeholder; the app renders the approved switch asset.
- Icon `QPushButton` objects are replaced with the shared
  `TactileIconButton` at load time. It preserves the supplied PNG at rest and
  provides hover, press and keyboard-focus feedback. The model badge uses the
  separate `GlassButton` pill.
- The translucent lavender answer and history surfaces are defined in
  `src\clearcue\ui\theme.py` and remain editable without generated Python.
- If a component's outer shape changes, update its mask function in
  `src\clearcue\ui\popup_cluster.py` so click-through corners remain accurate.

## SVG and icon sources

The four approved `prxmpt-*.svg` files are retained beside the Designer forms.
Tests verify their exact SHA-256 values. The separately supplied canonical PNG
artwork is also hash-locked in `asset_manifest.json`.

- Edit component geometry in the corresponding `.ui` form.
- Edit ordinary widget colours, borders, fonts and radii in
  `src\clearcue\ui\theme.py`; tactile icon controls live in
  `src\clearcue\ui\glass_controls.py`.
- Preserve asset filenames when replacing icons, then update
  `asset_manifest.json` intentionally.
- Keep behavior and signal wiring in `src\clearcue\ui\main_window.py`.
