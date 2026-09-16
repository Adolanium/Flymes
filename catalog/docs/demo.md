# Recording Flymes

This guide describes the **Built-in demo** and its separate worker trace.
For native conversation mode, use [native-mode.md](native-mode.md).

The fixture deliberately contains a case-sensitive search bug. Its baseline is
three passing and two failing checks. The fixed verifier is outside the editable
directory. The worker cannot alter its tests, execute imports or call arbitrary
functions. Record the measured outcome even when the controller stalls.

## A 40-second recording

Use the panel's **Presentation** button for the opening shot. The animated fly,
selected action, step number and last test result stay visible. The fly walks for
SEARCH, probes for INSPECT, works its front legs for IMPLEMENT, hovers for TEST,
grooms for REVIEW, and folds its wings for FINISH. These movements illustrate
software actions, not motor output from the connectome. Paused or disconnected
runs freeze the motion, and reduced-motion preferences are respected.

Open **Try the movements** to preview any behavior without a model call. The
stage explicitly says MOTION PREVIEW until you select **Follow run**. This
preview does not change the actual decision, scores, or run. **Pause motion**
controls animation only; use **Stop** to stop the run. Exit presentation and open
**How this action was selected** to show measured readouts.

1. At 0–5 seconds, show the real Hermes window and Flymes pane. Say: "I let a
   fruit fly connectome choose what a bounded Hermes worker does next."
2. At 5–12 seconds, show the full retained counts, a selected action and its
   competing scores. Keep the schematic rendering and sampling label visible.
3. At 12–23 seconds, show the recorded operation and the regression counts.
   Provider waits may be cut with an explicit time jump. Do not accelerate
   telemetry while labeling it live.
4. At 23–33 seconds, pause, checkpoint, silence 30%, then compare the same
   observation. Show the actual scores whether or not the action changes.
5. At 33–40 seconds, show the independent outcome. Say: "Hermes handles
   language and tools. The simulation selects the next macro-action."

The plugin completion facade does not create native conversation tool turns.
Describe the operation list as Flymes' bounded worker trace. Do not record a
stock transcript as if these operations appeared there.

## Replay fallback

Build the browser harness as described in [Desktop development](desktop.md),
open `desktop/harness.html`, and choose `artifacts/replay.json`. Move the frame
slider through recorded steps. This viewer disables execution controls and
labels every frame REPLAY. The browser harness is not evidence that the native
Desktop plugin rendered successfully. Screenshots of it must retain that label.

For a Windows screen recording, open Snipping Tool, select Record, frame Hermes
Desktop and the pane, and start recording. Turn on presentation mode first.
Inspect the resulting video for private paths and transcript text before sharing.
No social post or branch is published by Flymes.

## Draft X post

I wired a real fruit fly connectome into a bounded Hermes coding experiment.
166,700 retained neurons select the next macro-action. Hermes handles the
language and validated tools. Silencing neurons can change the selected action.
This is an engineered controller, not a fly that understands code.

## Technical follow-up

The recurrent graph comes from MaleCNS v1.0. Fixed rate dynamics turn normalized
task measurements into activity; a fixed readout selects actions. Each decision
logs its observation, checkpoint, scores, dispatch and result. The sensory
mapping and action pools are engineered. Rewiring, recurrent silencing and
lesions are explicit controls. Open-loop differences do not establish better
task performance or learning. Read the recorded outcome before making claims
about success.

## Real, modeled and engineered

| Kind | What Flymes uses |
| --- | --- |
| Real data | Published neuron annotations and directed synapse-count connectivity |
| Real execution | Configured Hermes provider completions, restricted file operations and independent checks |
| Modeled | Rate dynamics, neurotransmitter sign assignments and normalized weights |
| Engineered | Feature scaling, seeded input mappings, readout pools and software actions |
| Not established | Coding understanding, learning, physiological accuracy or advantage over a heuristic |
