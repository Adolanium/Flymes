# Fly Mode in a real Hermes conversation

Restart Hermes after installing the updated plugin. The companion must be
running (`scripts/launch.ps1`). The native bridge registers `flymes_choose` and
hooks around normal Hermes tool calls. It does not replace Hermes's tools.

## Start a task

1. Open a Hermes conversation and send a first message so it has a stored session.
2. In Flymes, select **Hermes task**. Enter the absolute repository directory.
3. Keep controller **REAL**, then click **Enable Fly Mode**. Graph loading may
   take several seconds. Wait for ACTIVE before sending the actual task.
4. Send your coding task in that conversation, such as “Fix the failing login
   test, then run the targeted test.”
5. Hermes proposes two to six concrete alternatives through `flymes_choose`.
   The selected tool call and its result appear in the normal conversation.
6. Use **Return control to Hermes** to remove the gate. **Pause selection** blocks
   new calls, but does not cancel a tool already running. Resume and tell Hermes
   to continue if its turn has already ended.

Fly Mode is attached to the stored conversation ID, not whichever chat happens
to be visible. Other conversations remain unchanged. If session compression
creates a new stored ID, the bridge detects its stored parent lineage and blocks
further tools with an explicit message. Return control and enable the new session
explicitly. It does not silently resume unrestricted execution after compression.

The task directory guides Hermes; it is not a filesystem sandbox. Hermes's
existing tool permissions and approval rules still apply. Tool discovery is
allowed without selection. Task operations require the exact selected tool and
arguments, once. Batched and delegated tool proposals are rejected.

## Change the circuit before execution

Enable **Pause before each selected tool** when starting a run. A proposal then
holds before execution. Open **Compare the same decision** and click **Compare
readouts**. REAL, SHUFFLED, SILENCED, 30% LESIONED and the HERMES preferred choice
use the same proposals, observation and saved neural state. Comparisons do not
execute alternative repository changes.

While paused, **Use LESIONED** or another controller replaces the pending
selection. Resume selection, then tell Hermes to continue. It fetches the current
selection before executing. This lets you observe an intervention's effect on
the chosen next call. It is not an automated benchmark of full alternative task
trajectories; use separate clean repository copies for those experiments.

## What is measured

The circuit uses real connectivity and simplified rate dynamics. Input mappings,
action labels and readout pools are engineered. Hermes supplies candidate labels,
arguments, reasons and its preferred candidate. Native results supply exit codes
when present; missing test counts and verification remain unknown. HERMES mode
uses the supplied preferred index without claiming a neural choice.

The avatar illustrates actions. It does not depict biological motor output.

Each decision saves its proposals and neural checkpoint under
`$FLYMES_STATE_DIR/.flymes/native-runs/<run-id>/`. The state directory defaults to
`$HERMES_HOME/flymes`. Actual tool results are saved separately, with
compact events and hashes. Treat these local records like a conversation trace:
tool arguments and outputs can contain private project information.

## Recovery and limits

Only one native Fly Mode session is active at a time. The default budget is 100
selections or 30 minutes. Budget expiry stops new authorizations; it never
silently returns control. The gate persists if the companion restarts. The panel
offers Return control even when the companion is offline.

The bridge uses Hermes's supported plugin hooks. Earlier plugins that explicitly
approve a tool can short-circuit later hooks in this Hermes version. This is an
experimental controller, not an adversarial security boundary. A model may also
end its response without completing the task; Flymes gates tool execution, not
the final-answer channel.

Proposals are limited to 64 KiB total and 32 KiB of arguments per candidate.
Large edits should use smaller patches. The simulator's sampled panel data and
comparison responses are bounded; full checkpoints remain on disk.
