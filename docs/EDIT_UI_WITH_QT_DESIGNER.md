# Editing the prxmpt popup components with Qt Widgets Designer

prxmpt 1.0.10 uses five independent Designer forms in
`src\clearcue\assets`:

| Form | Logical size | Purpose |
|---|---:|---|
| `prxmpt-top-bar.ui` | 516 × 46 | Settings, logo, drag, hide and tray controls |
| `prxmpt-audio-handler.ui` | 516 × 161 | Audio sources, live status and question controls |
| `prxmpt-activity-buttons.ui` | 191 × 22 | Plot and History view toggles |
| `prxmpt-plot-popup.ui` | 516 × 393 | Generated answer and answer controls |
| `prxmpt-history-popup.ui` | 516 × 390 | Scrollable saved-session list |

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

Open one of the five `.ui` files listed above.

## Previewing changes

Save the form, close the running source instance of prxmpt, then run:

```powershell
.\.venv-ui\Scripts\python.exe -m clearcue.main
```

An installer rebuild is only needed when a patch is ready to distribute.

## Component positioning

The individual component sizes are fixed. The cluster controller positions
them with these logical gaps:

- Top bar to audio handler: 8 px
- Audio handler to activity buttons: 6 px
- Activity buttons to Plot or History: 6 px
- Activity buttons are horizontally centred beneath the 516 px surfaces
- Plot and History use the same top-left anchor and are never visible together

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
- If a component's outer shape changes, update its mask function in
  `src\clearcue\ui\popup_cluster.py` so click-through corners remain accurate.

## SVG and icon sources

The five approved `prxmpt-*.svg` files are retained beside the Designer forms.
Tests verify their exact SHA-256 values and confirm that every embedded raster
icon matches the optimized PNG used by the Qt controls.

- Edit component geometry in the corresponding `.ui` form.
- Edit colours, borders, fonts and radii in `src\clearcue\ui\theme.py`.
- Preserve asset filenames when replacing icons, then update
  `asset_manifest.json` intentionally.
- Keep behavior and signal wiring in `src\clearcue\ui\main_window.py`.
