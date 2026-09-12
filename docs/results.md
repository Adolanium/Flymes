# Executed results

The neural controller affected real execution, but did not solve the fixture in
the six-step comparison. The heuristic solved it. These are exploratory runs
with one seed and one task, not evidence of a general performance difference.

Every run started from the same intentionally faulty fixture and had a six-step,
900-second budget. The worker interface, verifier and configured Hermes provider
were the same. Calls that needed a model reported `nous` and
`deepseek/deepseek-v4.1-flash`. LESIONED chose only TEST and made no model calls.
Concurrent runs and provider delays make the wall times unsuitable as a clean
speed comparison.

| Mode | Actual action sequence | Independent outcome | Wall seconds |
| --- | --- | --- | ---: |
| REAL | INSPECT, FINISH, TEST ×4 | 3 passed, 2 failed; budget stop | 34.98 |
| HEURISTIC | INSPECT, IMPLEMENT, TEST, FINISH | 5 passed, 0 failed; completed | 111.84 |
| SHUFFLED | INSPECT ×3, FINISH, TEST ×2 | 3 passed, 2 failed; budget stop | 60.84 |
| SILENCED | INSPECT, FINISH, TEST ×4 | 3 passed, 2 failed; budget stop | 22.53 |
| LESIONED, seeded 30% | TEST ×6 | 3 passed, 2 failed; budget stop | 7.06 |

Machine-readable results, IDs, model usage and safety stops are in
`artifacts/closed-loop-results.json`. Sanitized per-mode replay files are next to
it. Raw checkpoints and operation evidence remain in `.flymes/runs/`. Earlier
timeout and rejected-edit runs were retained. No calibration was used to select
a more flattering controller seed. These exploratory settings were documented
after execution; they are not a preregistered evaluation.

Separate adapter testing proved that a permitted Hermes IMPLEMENT can fix the
fixture and that the independent verifier accepts it. That is not attributed to
the neural controller. `docs/adapter-live-result.json` records the native CLI
plugin route, including a 23.703-second IMPLEMENT and 2,703 reported tokens.

## Neural measurements

Full retained connectivity contains 166,700 neurons, 25,582,938 directed weighted
connections and 124,177,617 synapses. The tested sparse model advanced 100ms of
simulated time in 767ms. The separate full graph plus rewiring benchmark peaked
at 929,161,216 bytes of working set. The source checksums, exact retained counts,
versioned dependency measurements and five real neural readouts are in
`docs/full-data-benchmark.json`.

In the matched benchmark observation, a seeded 30% lesion changed INSPECT to
IMPLEMENT. In the fixture's separate baseline observation, the 20% lesion used
by `run-controls` changed INSPECT to TEST. Different observations and lesion
sizes can give different results. Both are open-loop sensitivity experiments;
neither means the task was solved. The closed-loop LESIONED run selected TEST
from its first observation, demonstrating that the intervention changed the
executed action, not merely the visualization.

## Validation

The standard Python suite passed 29 tests. The opt-in full-data live-provider
smoke test passed separately in 25.37 seconds and required an actual model call.
Three Desktop component tests passed. Hermes Plugin Doctor validated native
worker manifest discovery and CLI registration. The real browser replay viewer
rendered without page errors or horizontal overflow at desktop and narrow sizes.

The native Hermes Desktop pane also rendered and completed a full-data step
through its authenticated backend proxy. It then paused with 320 measured
samples. The final state with compact comparisons was 30,049 bytes. Ten local
companion requests took 27.29ms median and 47.45ms maximum including JSON decoding. This
measurement excludes the Hermes proxy and renderer, and does not measure screen
frame rate. See `artifacts/telemetry-benchmark.json` and the native screenshots
under `desktop/review/`.

Native checkpoint, 30% lesion, comparison and Stop reached the companion.
For that post-INSPECT checkpoint the lesion reduced mean activity from 0.06020
to 0.04040 but kept INSPECT selected. Desktop then reported intermittent backend
timeouts, although the comparison and Stop were logged successfully. Its final
capture from that first attempt, `native-timeout-before-fix.png`, deliberately
shows the frozen disconnected state. Investigation
found a reproducible transport stall: the 169,080-byte state response
stopped after 65,387 body bytes. HTTP telemetry now retains only current samples,
eight compact history rows and compact comparison scores. A complete recorded
18-result comparison is 33,849 bytes and passes a real loopback response test.
The underlying Windows transport behavior is not explained. Long-operation
request timeouts are also 60 seconds. The final native retest acknowledged
INSPECT, checkpoint, 30% lesion, comparison and Stop without a timeout.
`desktop/review/native-presentation.png` shows that successful retest, with
320 samples and the stopped state. The temporary debugging app and port were closed.

Setup, doctor, launch, stop, full data preparation, demo execution, controls and
sanitized export were executed on Windows. Uninstall's paths and allow-list
cleanup are implemented but have not been applied to this installed environment.
The worker does not support arbitrary repositories or ordinary Hermes
conversation tool turns. See the integration and Desktop notes for their exact
verification scope.
