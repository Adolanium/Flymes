# Animated fly verification

`fly-movement.mp4` records the actual panel in its browser harness. Every shown
movement is explicitly labeled MOTION PREVIEW. No model calls or live decisions
were generated for the video.

The browser check in `desktop/inspect-motion.mjs` verifies changing canvas frames
for all six actions, identical frames after pausing motion, identical frames
under reduced-motion preferences, and no horizontal overflow at 320 pixels.
Four plugin tests and eight proxy/boundary tests pass.

The proxy regression reproduces the Windows ConnectionResetError from the Hermes
desktop log. It now returns 503 instead of an uncaught 500; this handles the
interruption but does not guarantee that the underlying connection never resets.
The panel retries state polling and exposes diagnostic details in a disclosure.
Control operations are not retried automatically.

Review corrections require running state for automatic avatar motion and expose
reduced-motion preferences in the toolbar and accessible canvas description.
The native plugin and proxy files have been installed. The running Hermes process
must reload to use the new code.
