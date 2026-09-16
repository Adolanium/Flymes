# First arena pilot

An exploratory pilot used the full retained MaleCNS graph on world seeds 7, 8,
and 9, with circuit seed 7, a 40-action limit, and 30% seeded lesions. All six
controllers used the same maps and sensory interface. No language model, learning,
or parameter search was used. The primary measure was food collected out of seven.

| Controller | World 7 | World 8 | World 9 | Mean food |
| --- | ---: | ---: | ---: | ---: |
| Original connectome | 0 | 0 | 0 | 0.00 |
| Rewired | 0 | 0 | 0 | 0.00 |
| No recurrence | 0 | 0 | 0 | 0.00 |
| Lesioned, 30% | 0 | 0 | 0 | 0.00 |
| Greedy baseline | 5 | 5 | 2 | 4.00 |
| Random baseline | 0 | 0 | 1 | 0.33 |

Every neural episode exhausted its initial energy without collecting food.
These results show that this untrained sensory mapping and pooled readout did
not produce useful foraging behavior on the three tested worlds. They do not
establish that a connectome-constrained controller could never learn the task,
or that all neural conditions behave identically. Equal food counts can conceal
different action sequences; inspect the recordings.

The next experiment should improve or train the decoder while holding the sensory
interface and training budget constant across the original and rewired networks.
Evaluation needs unseen worlds and independent mapping seeds. Do not tune against
these three worlds and then report them as held-out evidence.

The [machine-readable report](../artifacts/arena-pilot-report.json) preserves all
18 episode results, graph identity, protocol, seeds, source hashes, and outcomes.
A [compact real-connectome replay](../artifacts/arena-connectome-replay.json) can
be loaded through **Arena > Open replay**, including while the companion is offline.
Full per-step sensory evidence remains in the local experiment records.

Reproduce with the command in [the arena protocol](arena.md). This is a small,
fixed-seed exploratory result, not a claim of biological fidelity or a performance
advantage. Wall times are machine-dependent.
