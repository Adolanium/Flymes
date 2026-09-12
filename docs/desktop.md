# Desktop panel

`desktop/plugin.js` is an uncompiled ESM Desktop plugin. It imports only host React and `@hermes/plugin-sdk`. No CDN, bundling, remote assets, or third-party visualization runtime is needed to install it. The plugin is initially disabled and registers a 440px right pane when enabled in Hermes Capabilities > Plugins.

The verified upstream interfaces are `HermesPlugin.register`, `ctx.register`, `ctx.rest`, and `ctx.onDispose` in `apps/desktop/src/contrib/plugin.ts`; REST options in `src/api/plugins.ts`; and the pane contribution in the [official Desktop SDK documentation](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk). This is the Desktop contract, not the dashboard JavaScript SDK.

## Telemetry and controls

The panel requests `/state` once a second with a five-second request timeout. It never overlaps polling requests. Failed or stale telemetry freezes and dims the last neural frame. A ResizeObserver redraws on resizing and is disconnected on unmount. No animation timer creates neuron activity.

Controls post `{command, ...arguments}` to `/control`. Closing the panel or disabling the plugin requests stop. Backend lease expiry provides a second stop path when the renderer cannot send cleanup. The dedicated task workspace is configured in the backend and is read-only in the panel.

Neurons occupy a deterministic schematic projection unless the backend supplies normalized anatomical coordinates and explicitly marks its layout `anatomical`. Display sampling never changes the simulation. Edge lines come from measured graph sample edges. Color reflects supplied activity, clamped to the display range. Action bars scale against the largest supplied score and are not probabilities. Missing scores and observations remain unavailable.

Presentation mode hides workspace, model, run IDs, raw observations and decision logs. Its visible status distinguishes active LIVE execution, REPLAY, paused, and disconnected states. It is intended for recording the neural decision and controls without revealing task paths.

## Browser replay harness

The harness is a development aid, not a replacement for Hermes Desktop. It uses the exact panel component and contains no fabricated sample run.

```powershell
cd desktop
npm install
npm run build:harness
python -m http.server 8790 --bind 127.0.0.1
```

Open `http://127.0.0.1:8790/harness.html`, load an exported JSON state or JSONL decision log, and select a frame. The harness refuses execution controls. For environments with an existing dependency installation, `FLYMES_NODE_MODULES` can point to that `node_modules` directory while running the build script.

```powershell
node --test desktop/plugin.test.mjs
node --check desktop/plugin.js
```

The renderer tests cover missing scores, sample bounds, the actual contribution contract, and unload stop dispatch. They do not prove a live Hermes run or native transcript visibility.

## Validation scope

The browser harness rendered the exported real eight-step run, including 320 recorded neuron samples. Desktop and 420px captures had no horizontal overflow or browser errors. A separate review accepted the browser panel after checking Stop availability and per-frame replay timing. Screenshots are in `desktop/review/`. The mechanical design detector ran with its regex fallback because parser modules were unavailable; that result is not a full accessibility audit.

The installed packaged Hermes Desktop was also launched and inspected. Flymes was enabled through Capabilities > Plugins, beside a blank new-session view with the existing session sidebar hidden. The native panel successfully prepared the full dataset, dispatched one real INSPECT action, returned to paused, checkpointed, and applied a 30% seeded lesion. The native run was `fda21a83f2ff4a6d8538623b82b48c36`. This verifies the real renderer and backend path; it does not establish that worker messages appear in the stock transcript.

The first native comparison exposed a transport failure: the large authenticated state response stalled after roughly 64KB and Hermes reported a timeout. The panel froze its last measured frame and displayed DISCONNECTED. The companion now sends compact telemetry with eight recent history entries and compact comparison results; full records remain on disk. The panel displays the backend's history-limitation note.

The final native retest passed after that fix: prepare, real INSPECT step, pause, checkpoint, 30% lesion with seed 7, compare acknowledgement, and Stop acknowledgement. All neural comparison modes selected INSPECT for this observation; HEURISTIC selected IMPLEMENT. The final safe screenshot is `desktop/review/native-presentation.png`, showing STOPPED with current telemetry, 320 real samples, and no error. The earlier failure screenshot remains `native-timeout-before-fix.png` for diagnosis. On the second launch, the host initially omitted all disk plugins; its supported Reload desktop plugins command restored them.

Both diagnostic Desktop instances were closed and the debugging listener removed. Captures temporarily used 100% zoom to avoid an Electron screenshot clipping issue, then restored the user's zoom. No user conversation content is included. Long prepare and comparison requests allow 60 seconds; polling still reports stale telemetry after five seconds.
