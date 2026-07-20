# prxmpt 1.0.23

This focused visual update improves meeting-history scanning and strengthens
the existing top-bar logo feedback without changing layout or controls.

## Meeting-record hover focus

- Hovering a saved meeting keeps that record at full opacity while its sibling
  records smoothly dim to 64% opacity.
- Moving between records immediately transfers focus to the newly hovered row.
- Leaving the meeting list smoothly restores every record to full opacity.
- Transcript, notes and delete controls remain visible, responsive and fully
  clickable throughout the effect.

## Stronger logo glow

- Slightly increases the existing artwork-only glow around the centered prxmpt
  logo.
- Preserves the exact logo asset, dimensions and position.
- Keeps the established subtle press squeeze and unlocked dragging behaviour.

## Windows build reliability

- Runs pytest with a private temporary directory inside the project build
  folder, avoiding Windows access-denied failures from a stale system
  `pytest-current` link.
- Real test failures still stop the installer build as before.

## Included previous work

- Keeps the v1.0.22 responsive audio lamps, top-bar arrangement and tactile logo
  control.
- Keeps the v1.0.21 validated model dropdown and v1.0.20 Windows build fixes.
