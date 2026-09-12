# Modeling

Flymes uses a fixed recurrent rate model. It is an experimental supervisory policy, with no learning and no claim of biological fidelity or coding understanding. Hermes handles language and tool execution. The selected action comes from the numerical activity readout before dispatch.

For each neuron, every 5 simulated milliseconds:

```text
W[post, pre] = contact_count[post, pre] * sign[pre] / max(1, total_incoming_contacts[post])
target = clip(external_drive + 0.8 * W @ activity, 0, 1)
activity += 0.25 * (target - activity)
```

The update is an Euler low-pass rate approximation with a 20ms time constant and rectification/saturation at zero/one. It has no membrane voltage, spike threshold, spike delay or refractory state. The model avoids a claim that every fly neuron spikes. The normalized incoming absolute row sum is at most one, so the recurrent gain of 0.8 bounds amplification. All retained weak, self and recurrent connections participate. No dense neuron-by-neuron array is allocated.

Synaptic contact counts are not measured physiological strengths. Normalization, gain, timestep, activation function and signs are modeling assumptions. GABA, glutamate and histamine consensus predictions receive negative signs; all other labels, including unknown and neuromodulators, receive positive signs. Receptors and compartment-specific effects are unavailable. These assignments can be biologically wrong and should not be interpreted as recovered physiology.

Each decision advances twenty ticks, exactly 100ms of simulated time. Simulation pauses while Hermes works. Wall-clock decision latency is measured independently. Silent and saturated population fractions are reported. A silent state still has a deterministic valid-action tie-break and an explicit health warning; silence does not trigger a replacement controller.

## Encoder and decoder

`encode()` exposes the measured inputs, scales, normalized values and separate missingness channels. Null measurements are never filled with an invented measurement. Values use `clip(abs(value) / scale, 0, 1)`.

| Channel | Scale |
| --- | ---: |
| tests_passed, tests_failed | 10 |
| last_exit_code | 1 |
| repeated_actions | 5 |
| changed_files | 10 |
| diff_lines | 200 |
| elapsed_steps | 20 |
| verified | 1 |
| remaining_budget | 20 |

A seeded generator assigns each retained neuron one of eighteen input channels: nine values and nine missingness flags. Each cell receives `0.45 * channel * uniform(0.6, 1.0)`. Seeds freeze this engineering interface. Body IDs identify the cells; the assignment has no anatomical support and no group is a natural coding circuit. This broad assignment establishes an inspectable first controller, not an optimized policy. Missingness itself stimulates the declared missingness channels.

A seeded permutation distributes neurons into six disjoint readout pools. Each action score is the mean activity of its pool. The maximum score among the supplied valid actions wins. Ties follow SEARCH, INSPECT, IMPLEMENT, TEST, REVIEW, FINISH order. The mask and whether more than one choice existed are logged. There is no scheduled sequence or LLM action selector in REAL mode. FINISH requires an independent verifier in the execution layer.

Telemetry contains real state samples, body IDs and actual directed connections induced by the sample. Positions are schematic. Sampling affects rendering only.

## Controls

REAL uses the original retained wiring. LESIONED uses the same wiring and clamps the selected neurons to zero before and after every tick. Random lesions are seeded; named lesions match exact source `type` or `superclass` strings. Percentages apply to the eligible population. Clearing the mask is reversible, but restoring earlier activity requires checkpoint restore. REAL ignores the saved lesion mask. Lesions activate on the next LESIONED decision.

SHUFFLED permutes the presynaptic endpoint stubs across the CSR edges with a fixed seed. Target row pointers and signed weights stay fixed. This is actual rewiring, not relabeling. It preserves directed incoming and outgoing edge multiplicities, each target's signed incoming weights and normalization, and the global weight multiset. Parallel connections and new self-connections can occur, so unique-neighbor degrees need not stay fixed. It does not preserve motifs, source outgoing strength or source neurotransmitter consistency. The comparison changes several structural properties and cannot isolate a single biological mechanism.

SILENCED sets the recurrent term to zero. External encoder drive and low-pass state persistence remain. HEURISTIC chooses FINISH when independently verified, TEST after edits, IMPLEMENT when failures persist after the first step, INSPECT for initial failures, otherwise SEARCH. Unavailable top actions fall through the same fixed tie-break. Its neural activity is displayed only as a reference and does not determine its scores.

Checkpoints include all neural activity, tick count, lesion mask, seed and graph fingerprint. A different graph or seed is rejected. Mode is supplied to each decision by the run controller. Replaying from a checkpoint with identical observations reproduces scores exactly within the same dependency versions. Cross-platform floating-point differences may matter when scores are close.

## Executed measurement

`full-data-benchmark.json` contains real full-graph telemetry for five modes starting at the same initial checkpoint and measured observation values supplied as an open-loop experiment. It contains no Hermes execution. REAL selected INSPECT; a seeded 30% lesion selected IMPLEMENT. No changed action was forced. This demonstrates sensitivity, not task-solving quality.

On Windows 11, Python 3.12.13, NumPy 2.2.6 and SciPy 1.15.3, import took 0.566s, graph load 1.050s and simulator initialization 1.369s. One REAL decision took 767ms for 100ms simulated time. The first SHUFFLED decision took 2279ms including rewiring. A separate process loading the full graph and running SHUFFLED peaked at 929,161,216 bytes of working set. These are individual measurements, not throughput guarantees.

## Existing implementation evaluated

[DOOMFLY](https://github.com/nftechie/doomfly/tree/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33), commit `71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33`, was inspected on 2026-09-11. Its original code is MIT licensed, with separate third-party and dataset terms. Its documented baseline uses a C++ event-driven LIF kernel, Python 3.11, and a build helper whose documented native output is a Linux shared library. It also contains Doom-specific visual encoding and later plasticity experiments. It was not executed or certified on Windows here. Flymes does not copy its kernel; this smaller sparse rate implementation uses available Windows wheels and exposes a different task interface. The data-retention policy independently matches the documented nonempty-superclass exclusion of glia. DOOMFLY's published numbers are not used as runtime counts.
