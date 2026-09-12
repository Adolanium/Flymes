# Specimen panel verification

The screenshots named `specimen-*` show the actual panel component in the browser
harness. Replay screenshots use the recorded first decision from
`artifacts/replay.json`; the empty screenshot contains no invented observations.

- Desktop and narrow presentation captures show the full fly illustration,
  selected action, test outcome and controls without horizontal overflow.
- Opening the readout disclosure renders 320 measured samples with the schematic
  layout label. The specimen illustration remains separate from this graph.
- The image decodes successfully both in the harness and the installed Hermes
  Desktop plugin. The native panel returned IDLE and kept Stop enabled.
- All three existing plugin tests pass. The design detector reported no findings.
- Review identified an unsupported “Not run yet” fallback for missing test data.
  It now reads “Unavailable.”

The native plugin was copied into the existing installation and its file hash
matches the repository version. No provider calls were needed for these checks.
