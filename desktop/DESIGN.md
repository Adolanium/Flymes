---
name: Flymes panel
description: An animated fruit-fly avatar beside measured controller decisions.
colors:
  primary: "#dfb476"
  avatar-paper: "#e9e4d6"
typography:
  body:
    fontFamily: "var(--font-sans, Segoe UI, sans-serif)"
    fontSize: "13px"
    lineHeight: 1.5
rounded:
  control: "5px"
  avatar: "4px"
spacing:
  panel: "22px"
  section: "18px"
---

# Design System: Flymes panel

## Overview

The default surface is now **Hermes task**. A top navigation switches to the
older **Built-in demo** without conflating the two execution paths. The native
surface binds a stored conversation ID, asks for an absolute task directory,
and exposes Enable, Pause, Resume and Return control. Experimental comparisons
remain in a disclosure. The normal Hermes conversation contains the actual tool
calls. Recorded harness views retain the RECORDED REPLAY label.

The panel remains an operating instrument beside a transcript. An articulated fruit-fly avatar illustrates the selected action; a large selected-action label explains the controller's latest decision. Technical measurements remain accessible through disclosures.

The browser harness uses the same component and CSS, identifies itself as a harness, and accepts exported real state or replay files. It does not ship invented run data.

## Colors

Host surface and text tokens preserve the Hermes theme. Their fallbacks form a dark charcoal panel with warm pale text. Ochre marks the primary control, state labels, selected scores, and active neural samples. The avatar sits on warm paper with brown caption text. Thin host-colored rules separate measurement groups.

## Typography

Interface text inherits the host sans-serif stack. Measurements and state labels use the host monospace stack where specified; tabular numerals keep values aligned. The selected action is 28px, growing to 32px in presentation mode. The title is 26px.

## Layout

The registered pane is 440px wide and scrolls vertically. The first view orders connection state, avatar, controller-to-Hermes explanation, selected action, latest test result, and run controls. Technical sections follow below. Preserve this vertical order without nested cards.

The canvas fills the available width with a 300px stage and scales its drawing proportionally. Below a 340px viewport, panel padding contracts to 14px, action text becomes 26px, and score columns tighten. Controls wrap as space narrows.

## Elevation & Depth

Flat surfaces and thin dividing rules organize the panel without shadows. The avatar paper creates the strongest surface contrast against the host panel.

## Shapes

Controls have modest rounded corners. The avatar stage has nearly square corners and clips the drawing. Score tracks are thin rectangular bars.

## Components

The canvas avatar articulates legs, wings, antennae, and body. SEARCH walks, INSPECT probes, IMPLEMENT works with its front legs, TEST hovers, REVIEW turns and grooms, and FINISH folds its wings. These movements are authored illustrations of software actions, not neural motor output.

Automatic motion requires a connected running state. Paused, stopped, stale, and reduced-motion states hold the pose. A separate motion control pauses the avatar. Reduced motion replaces that control with visible status and the accessible canvas label reports paused motion.

Try the movements exposes local previews with a MOTION PREVIEW caption and an explanation that the run is unchanged. Follow run returns to the selected action. Preview controls remain separate from run controls.

Connection status distinguishes live activity, recorded replay, and a disconnected view of the last frame. The selected action uses a plain-language headline with its action code below. Missing test results remain unavailable.

The action-selection disclosure contains relative readouts and the measured neural sample. Scores are not confidence values. Schematic layouts remain explicitly labeled. Graph frames change with telemetry or resizing. Neural graphs do not borrow avatar motion as evidence.

Run controls retain Prepare run or Run, Pause, Step, and Stop. The primary action uses ochre; secondary controls use a thin border. Keyboard focus uses a two-pixel ochre outline with a three-pixel offset. Disabled controls visibly dim. Stop remains available when disconnected.

Presentation mode enlarges the action and hides technical disclosures, workspace and model details, identifiers, raw records, and intervention controls. It retains connection and replay status, avatar, selected action, test result, main run controls, and Stop. Exit presentation restores the technical controls.

## Do's and Don'ts

- Do inherit host typography, surfaces, and text colors.
- Do label recordings and missing measurements explicitly.
- Do keep the fly recognizable and the selected action easy to read.
- Do keep technical evidence accessible through disclosures.
- Don't imply anatomical coordinates or full simulation coverage from a schematic sample.
- Don't present authored avatar motion as measured neural motor output.
