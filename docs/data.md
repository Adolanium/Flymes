# Dataset

The source is [MaleCNS v1.0](https://male-cns.janelia.org/download/), released by FlyEM at HHMI Janelia with the University of Cambridge, MRC Laboratory of Molecular Biology and Google Research. Data are [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Flymes retains attributed source URLs and hashes and creates a filtered sparse derivative. No endorsement is implied.

`prepare_data(cache, max_neurons=None)` downloads only the official neuron annotations, consensus neurotransmitter annotations and segment-to-segment connectivity Feather files. It does not download image volumes, skeletons or individual synapse locations. The files total 1,109,008,094 bytes in this release. GCS MD5 checksums are verified; CRC32C values and ETags are preserved alongside local SHA-256 digests. Existing cached files are SHA-256 checked. Interrupted transfers use byte ranges and an ETag sidecar. Changed ETags require a fresh cache. Source and processed data stay outside Git.

The loader reads edges in Arrow record batches. It retains annotated entries with a nonempty `superclass`, excludes explicit `status == Glia`, and retains every directed connection whose endpoints survive. No contact-count threshold is added. Self connections and weight-one connections survive. Duplicate pairs, if present, aggregate by summation. Rows refer to postsynaptic neurons and columns to presynaptic neurons. IDs stay unsigned integers on disk and decimal strings in telemetry.

Actual full import on 2026-09-11:

| Quantity | Count |
| --- | ---: |
| Annotation entries | 211,577 |
| Retained neurons | 166,700 |
| Excluded annotation entries | 44,877 |
| Retained directed weighted connections | 25,582,938 |
| Retained synaptic contacts | 124,177,617 |
| Source connection rows, including unresolved segments | 151,856,684 |
| Excluded connection rows | 126,273,746 |
| Source synaptic contacts | 311,833,243 |
| Excluded synaptic contacts | 187,655,626 |
| Retained neurons missing type | 2,194 |
| Retained neurons missing consensus neurotransmitter | 178 |

Neuron count, weighted-connection count and contact count refer to different quantities. A weighted connection may contain multiple contacts. Retention means assigned neuronal superclass, not a guarantee of complete physiological characterization. The official filenames include `minconf-0.5`, an upstream confidence filter. Unresolved segments and glia are excluded by the stated annotation policy. The importer does not silently substitute a synthetic graph.

An optional `max_neurons` selects the lowest retained body IDs and the induced edges. It writes a distinct `prepared-subset-N` directory with a prominent DEVELOPMENT SUBSET label. The default writes `prepared-full` and simulates all retained neurons. A subset is a development convenience with no claim of representative anatomy.

Every prepared folder contains `metadata.json`, `ids.npy`, `connections.npz` and `annotations.json`. Prepared file digests are validated on load. The checked-in `full-data-benchmark.json` records the source and processed hashes and computed counts. Raw metadata remains available in the source cache. Keep the cache if preparing again; each input is validated rather than needlessly downloaded.

The implementation needs room for the 1.11GB source plus sparse outputs and temporary processing arrays. Memory use depends on the retained graph and comparison modes. The recorded full simulator measurement peaked at about 929MB after preparation; preparation itself was not instrumented for peak memory. No CUDA, Docker, WSL or administrator access is required.
