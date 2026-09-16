# Native integration validation

A live run used the configured Hermes model and the full retained MaleCNS graph
against a disposable Python project containing `return a - b` in an `add`
function. The bridge ran through Hermes's actual agent and native tool handlers.

| Step | Hermes's proposed preference | Flymes selected | Native execution |
| --- | --- | --- | --- |
| 1 | INSPECT | TEST | Ran the example and observed `-1` |
| 2 | INSPECT | IMPLEMENT | Patched subtraction to addition |
| 3 | TEST | TEST | Verified `add(2, 3) == 5` |

The run made nine model API calls. Its selected calls and results are recorded in
`artifacts/native-task-smoke.json`. This is one small integration test, not
evidence that the connectome outperforms Hermes or simpler policies generally.
Hermes supplied the alternatives and action labels; the circuit selected among
them. A schema-discovery call was initially blocked. Native schema discovery is
now exempt, with a regression test. A cleanup response was reset after the
release was accepted; a subsequent state request confirmed release.

The automated suite passes 52 Python tests and four plugin tests. It covers
session isolation, one-shot exact arguments, same-state comparison and applying
an intervention, correlated and idempotent result reporting, offline release,
compression-child blocking, and bounded telemetry. The opt-in legacy live test
is skipped in the default suite; the native live run above was executed separately.

The browser harness rendered the new native panel with the recorded state, no
JavaScript errors, and no horizontal overflow at 360 pixels. The installed native
agent bridge was exercised by the live run. The updated panel and gateway files
require a Hermes restart to load into the already-running Desktop process.
