# Catalog preparation

Flymes is prepared for review but has not been submitted by this work. The
candidate is a Windows community Desktop plugin requiring a local companion.
Its research status and measured limitations are part of the listing description
and README. Admission requires a maintainer's review.

`catalog/` is a generated, self-contained package. It includes the standard
`__init__.py` entry point, manifest, Desktop panel, authenticated gateway proxy,
companion source, locked Python dependencies, fixture, setup scripts, and docs.
Development recordings and the browser development bundle stay in the source
repository. The package does not download or replace its own code.

## Build and validate locally

```powershell
uv sync --frozen --extra test
uv run pytest -q -m "not live and not full"
node --test desktop/plugin.test.mjs
python scripts/build_catalog.py
python scripts/build_catalog.py --check
hermes plugins validate .\catalog
```

Run `scripts/check_hermes.py` with a Hermes interpreter and `--hermes-root` pointing
at a Hermes source checkout for an isolated package scan, capability probe, load,
and setup test. It creates a temporary home, does not call a model, and leaves the
user's active installation alone.

The declared Agent capabilities are `flymes_choose` and the three hooks
`pre_llm_call`, `pre_tool_call`, and `post_tool_call`. There is no middleware or
required provider credential variable. `FLYMES_HERMES_ROOT` and
`FLYMES_HERMES_PYTHON` configure the companion's optional demo subprocess;
`FLYMES_STATE_DIR` overrides storage. The package also registers the user-invoked
`flymes-complete` CLI command. The current catalog capability schema does not have
a CLI-command field.

## Release handoff

`catalog-entry.yaml.in` is a draft, not an installable catalog entry. After the
reviewed changes are committed and published by the maintainer, replace
`RELEASE_COMMIT_SHA` with that exact 40-character commit and validate it with
Hermes's `scripts/validate_plugin_catalog.py`. Do not use the old commit, which
lacks this package. No commit, tag, push, release, or submission is performed by
the build and check scripts.

The results and limits of the current preparation pass are in
[local catalog validation](catalog-validation.md).

The [current admission policy](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md)
requires an exact commit pin and prohibits self-updating code. The older local
snapshot's two-week waiting rule is absent from the policy checked on 2026-09-16.
Recheck policy and run the scanner against the actual release commit before
submission. A local test is not catalog approval.
