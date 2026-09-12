# Third-party work

MaleCNS connectivity and annotation data are distributed under CC BY 4.0.
Credit FlyEM / HHMI Janelia, Cambridge, MRC LMB and Google Research. Source
URLs, version, hashes, filtering and exclusions are in `docs/data.md` and each
prepared dataset's `metadata.json`. The software license does not replace the
dataset license.

Hermes Agent is MIT licensed. Flymes integrates with its Desktop SDK and native
plugin LLM/CLI interfaces. The tested source commit is
`ad03f20dd61919ca2135d6904e787a94284aacaf`.

The doomfly repository was evaluated as a simulation reference. No doomfly
source code was copied. See `docs/modeling.md` for the choice of a small fixed
rate kernel and its differences from that project.

Python dependencies and their exact versions are in `uv.lock`. Frontend React
and react-dom are MIT licensed. The development bundle includes these libraries;
esbuild preserves their bundled license notices. The native plugin imports
React from the Hermes host instead of bundling a second copy.
