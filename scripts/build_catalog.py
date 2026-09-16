"""Build the self-contained catalog package; --check rejects stale output."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_files():
    names = {
        '__init__.py', 'plugin_init.py', 'plugin_worker.py', 'plugin.yaml',
        'pyproject.toml', 'uv.lock', 'README.md', 'LICENSE', 'THIRD_PARTY.md',
        'dashboard/manifest.json', 'dashboard/plugin_api.py', 'desktop/plugin.js',
        'demo/fixture/app.py', 'demo/fixture/README.md',
    }
    for pattern in ('flymes/*.py', 'scripts/*.ps1', 'docs/*.md', 'docs/*.json',
                    'docs/assets/*.png', 'artifacts/*.json'):
        names.update(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern))
    return sorted(names)


def build(check=False):
    target_root = ROOT / 'catalog'
    stale = []
    names = package_files()
    existing = {path.relative_to(target_root).as_posix() for path in target_root.rglob('*')
                if path.is_file() and '__pycache__' not in path.parts}
    extra = existing - set(names)
    if extra:
        raise SystemExit('Unexpected package files; review and remove: ' + ', '.join(sorted(extra)))
    for name in names:
        source, target = ROOT / name, target_root / name
        content = source.read_bytes()
        if check:
            if not target.is_file() or target.read_bytes() != content:
                stale.append(name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    if stale:
        raise SystemExit('Run python scripts/build_catalog.py; stale files: ' + ', '.join(stale))
    print('Catalog package verified' if check else 'Catalog package built')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
