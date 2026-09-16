# Local catalog validation

## Arena development, version 0.3.0

The arena adds no Agent tools or hooks. Its authenticated companion routes use
the existing gateway proxy. The catalog package includes the arena runtime and
Desktop artifact; developer browser harnesses remain outside the package.

The updated regression suite passes 68 Python tests and six Desktop tests.
A browser test against an isolated real companion passes live run, pause/resume,
paired comparisons, report export, replay save/import, and 440/360-pixel layouts.
No provider is called. A separate 18-episode pilot used the full MaleCNS graph;
see [arena results](arena-results.md) for outcomes and limitations.
The rebuilt 0.3.0 package also passes Hermes capability validation, isolated Agent
loading, repeat setup, and the package scanner with a SAFE verdict. Medium scanner
notes remain for documented local HTTP and fixed subprocess operations.

## Earlier packaging validation, version 0.2.0

Validated on Windows on 2026-09-16 against Hermes 0.21.3 source at
`b4b554937e758209b703887d9b373ccae3aa2852`.
The reused interpreter's installed distribution metadata reports 0.21.1;
the imported source is the checkout above. No minimum Hermes version is declared
until a version boundary has been tested. The required interfaces are documented
in [setup](setup.md).

The package remains local and unsubmitted. The release commit placeholder in
`catalog-entry.yaml.in` must be replaced after the maintainer commits and publishes
the reviewed source.

| Check | Result |
| --- | --- |
| Python regression suite | 61 passed; one opt-in live test deselected |
| Desktop renderer tests | 4 passed |
| Generated package matches source | Passed |
| Hermes manifest and capability validation | Passed; no validation warnings |
| Agent plugin load | Passed in a temporary Hermes home |
| Repeated setup | Passed; unrelated plugins, config comments, and original backup preserved |
| Fresh companion environment | Frozen offline install, CLI startup, and server construction passed |
| Hermes package scanner | SAFE; no high or critical findings |

The scanner's medium findings describe local HTTP addresses, documented test
commands, and subprocess calls used for setup, source revision inspection, and
the fixed fixture verifier. The scanner allowed the package. This is a static
scan, not a security certification.

The Python suite reports one upstream Starlette/AnyIO deprecation warning.
No live provider call, full data preparation, or new Desktop interaction was
performed during packaging. Existing live evidence remains in
[native validation](native-validation.md); it describes the earlier run.

The new tests cover bare-interpreter plugin loading, complete source installation,
setup within the installed package, pin protection, external experiment storage,
and a failing doctor's exit status. Reproduce the host checks with
`scripts/check_hermes.py` as described in [catalog preparation](catalog.md).
