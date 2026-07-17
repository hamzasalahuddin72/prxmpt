# prxmpt 1.0.22

This patch implements the updated top bar while preserving the existing fixed
720×58 canvas and popup behavior.

## Top-bar layout

- Replaces the microphone and speaker artwork with the exact icons embedded in
  the supplied SVG.
- Positions the microphone at x=87 and speaker at x=145.
- Adds independent microphone and speaker activity lamps at the supplied
  coordinates.
- Leaves the x=490 profile position empty for the planned profile functionality.
- Moves the opacity control from x=491 to the former eye-control position at
  x=640.
- Removes the separate eye-shaped show/hide button from the interface.
- Preserves the settings and exit controls at their supplied positions.

## Live audio lamps

- Lamps now follow the actual level emitted by each audio source instead of a
  binary sound/no-sound property.
- A nonlinear level curve keeps quiet speech visible while preventing loud
  speech from saturating immediately.
- A 48 ms attack makes syllable peaks feel responsive; a 155 ms decay lets the
  light dim smoothly as speech becomes quieter.
- The microphone uses the supplied red lamp color and meeting audio uses the
  supplied blue lamp color.

## Tactile logo control

- The centered prxmpt logo is now the show/hide control while retaining its
  exact 104×56 artwork and location.
- Hover adds only a slight artwork glow, with no outline or button surface.
- Pressing applies a subtle 1.8% squeeze.
- When dragging is unlocked, dragging the logo moves the full popup cluster and
  suppresses the show/hide click after movement begins.
- The same restrained squeeze remains active during the drag for continuous
  tactile feedback.

## Included previous work

- Keeps the v1.0.21 validated model dropdown and both v1.0.20 Windows build
  corrections.
