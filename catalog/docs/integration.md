# Built-in demo integration

This document describes the separate **Built-in demo** worker and its historical
validation. For tool calls in a real conversation, see [native mode](native-mode.md)
and [native validation](native-validation.md).

Flymes runs a bounded coding worker using Hermes' configured model and native plugin LLM facade. The connectome selects the macro-action before the worker receives any instruction. The worker can select a permitted operation within that macro-action. Python wrappers validate every operation before it runs.

## Verified source and contract

The original live validation used Hermes commit `ad03f20dd61919ca2135d6904e787a94284aacaf`. Set `FLYMES_HERMES_PYTHON` and `FLYMES_HERMES_ROOT` to your actual Hermes runtime, following [setup](setup.md). The original commit records test provenance; newer Hermes revisions are not automatically considered failures by the doctor.

The official [Plugin LLM Access guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access) documents `ctx.llm.complete_structured`. Source at the pinned commit:

* [`hermes_cli/plugins.py`](https://github.com/NousResearch/hermes-agent/blob/ad03f20dd61919ca2135d6904e787a94284aacaf/hermes_cli/plugins.py), `PluginContext.llm`, lines 375–382, binds the plugin identity.
* [`agent/plugin_llm.py`](https://github.com/NousResearch/hermes-agent/blob/ad03f20dd61919ca2135d6904e787a94284aacaf/agent/plugin_llm.py), `complete_structured`, lines 460–475, accepts structured input, JSON Schema, output-token and timeout limits. The facade delegates provider selection and authentication to Hermes.
* The same module's `_check_overrides` and `_check_task` reject unauthorized provider, model, profile and auxiliary-task overrides. Flymes passes none of those overrides.

`plugin_worker.py` registers `flymes-complete` through `ctx.register_cli_command`. Each completion child invokes `python -m hermes_cli.main flymes-complete`; Hermes discovers the enabled plugin, supplies its context, and the handler calls `ctx.llm.complete_structured`. Requests and results use stdin/stdout, with a tagged JSON result so unrelated host startup output cannot become a tool request. Flymes does not construct a private plugin context, edit Hermes source or instantiate `AIAgent`.

The command now registers as part of the single `flymes` package. Setup disables
the old separate `flymes-worker` registration if present. No permission to replace
built-in tools is needed. The initial proof used a direct context bootstrap; that
historical run remains labeled in `adapter-live-bootstrap-result.json`.

## Enforced action boundary

The facade performs one model completion and exposes no tools or autonomous agent loop. Its output is data. Flymes parses and validates the requested operation, then dispatches through `WorkspaceBoundary`.

| Selected action | Allowed worker operations | Mutation |
| --- | --- | --- |
| SEARCH | Literal text search over approved files | None |
| INSPECT | Read approved files with content hash | None |
| IMPLEMENT | Read, then replace one approved file | One edit, at most 16 KiB |
| REVIEW | Read approved files and inspect accumulated diff | None |
| TEST | Invoke the host's fixed verifier | No worker-chosen command |
| FINISH | Invoke the same independent verifier | Completion only if checks pass |

All reasoning actions also permit `done`, which ends that action without claiming task success. Attempts to use another action's operation fail. No generic shell, import tool, browser, network tool, subprocess tool, arbitrary Python, or path traversal reaches the model. Search is literal text, so regex runtime is not model-controlled. The wrapper rejects absolute paths, alternate data streams, traversal, symlinks, junctions and hard links. The worker sees only `app.py` in the dedicated demo workspace.

The executable demo grammar is intentionally narrow. `app.py` may contain a docstring and `visible_items(items, query)` with one return list comprehension. Its expressions may use only `items`, `query`, `item`, comparisons, boolean operations and zero-argument `lower`, `casefold`, or `strip` calls. Imports, global state, assignments, decorators, default expressions, annotations, reflection and calls to other functions are rejected. The verifier must validate this grammar again before importing the file. Trusted verifier inputs are lists of plain strings and plain string queries.

This is an enforceable boundary for this demonstration, **not a general Windows filesystem sandbox**. Expanding to arbitrary coding tasks requires a separately designed sandbox and verifier. Another local process changing files concurrently remains outside the threat model. Keep the demo directory exclusive to Flymes during runs.

## Budgets, isolation and stop

Each adapter is bound to one `(session_id, run_id)` pair. A lock rejects concurrent actions. `(session_id, run_id, step_id)` results are cached so retrying a completed step cannot repeat an edit. Conflicting duplicate action names fail. A replacement requires the inspected content's SHA-256, preventing stale edits. The default is at most three model calls per macro-action, 1,800 output tokens per call, and 90 seconds for the entire action. The parent runner supplies the total step and run budget.

Each live completion runs in a child process using the Hermes interpreter and profile environment. Cancellation terminates that child and late results cannot dispatch operations. Model-call exhaustion and timeout are recorded as safety overrides. Stopping an independent verifier prevents its result from being accepted; its fixed child process may finish within its own 15-second timeout. Verifier work has no edit capability under the accepted demo grammar. The adapter never retries a failed completion automatically.

Hermes handles authentication inside the child. Flymes does not store provider keys. Provider errors return a generic diagnostic rather than exporting raw stderr, which can contain credential material. The result records actual provider, model, token usage, requested operations and measured tool outputs.

## Desktop and transcript limitations

The companion uses the local Hermes home and provider selected when it is
launched. Its run/session IDs are private to Flymes and do not switch with an
unrelated Desktop conversation. This release supports a single local companion
and the included fixture. Cross-profile routing, remote gateways and concurrent
users are not validated. Do not treat the Desktop's current conversation as the
worker's session or its model selection as a live override of the companion.

The [Desktop SDK](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk) supplies native panels and pages, reactive state, gateway JSON-RPC, and profile-aware `host.openSession`. These are distinct from web-dashboard plugins. The Desktop implementation records its verified panel and backend contract in its source and installation instructions.

`ctx.llm` explicitly operates outside the ordinary agent conversation and has no session-message parameter. Flymes' macro-action trace is therefore its own recorded telemetry. It does **not** automatically appear as stock Hermes assistant/tool turns in the normal transcript. No supported transcript append API has been verified. Sending an ordinary chat message through a gateway would launch ordinary orchestration and would not preserve this boundary. The panel can sit beside the real Hermes conversation; the custom worker trace must remain visibly identified as Flymes execution.

This distinction applies to the built-in demo. The later native conversation
mode uses the normal transcript and has its own [integration evidence](native-validation.md).

## Execution evidence

Seven boundary tests were executed with the Hermes interpreter. They cover grammar escape rejection, path rejection, Windows paths with spaces and non-ASCII characters, read-only rejection, duplicate steps, session isolation, cancellation of late responses, timeout and independent FINISH verification.

A live INSPECT action executed with the configured `nous` provider and `deepseek/deepseek-v4.1-flash` model. It made two model calls, read the real fixture, consumed 2,085 reported tokens and took 58.719 seconds. Read-only actions now stop after their first operation, avoiding the second completion. The first successful edit proof changed the independent test outcome from three passing and two failing to five passing and zero failing. Its IMPLEMENT action consumed 2,388 reported tokens and took 16.469 seconds. The earlier rejected edits are preserved in `adapter-live-rejected-result.json` and `adapter-live-rejected-2-result.json`. These requests used the configured provider, not fixture responses.

`docs/adapter-live-result.json` contains the latest complete live check, edit and independent verification sequence. These adapter-focused checks dispatch explicit actions to test the execution boundary; they are not evidence of a connectome-selected action sequence. The main experiment runner records controller-selected runs separately.

The final native CLI plugin run completed IMPLEMENT in 23.703 seconds using 2,703 reported tokens, followed by all five independent checks passing in 0.156 seconds. The baseline had two failures. This confirms the supported CLI registration path reaches the configured provider and applies a validated code change.
