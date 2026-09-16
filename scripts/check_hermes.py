"""Check the prepared package with Hermes in a temporary, isolated home."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-root', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / 'catalog'
    hermes = args.hermes_root.resolve()
    with tempfile.TemporaryDirectory(prefix='flymes-catalog-check-') as scratch:
        home = Path(scratch) / 'home'
        target = home / 'plugins/flymes'
        shutil.copytree(source, target)
        # Set the home before importing any Hermes modules.
        os.environ['HERMES_HOME'] = str(home)
        os.environ['PYTHONPATH'] = str(hermes)
        os.environ['FLYMES_HERMES_PYTHON'] = sys.executable
        os.environ['FLYMES_HERMES_ROOT'] = str(hermes)
        sys.path.insert(0, str(hermes))
        from hermes_cli.plugin_validate import validate_plugin_dir
        from hermes_cli.plugins import PluginManager
        from hermes_cli.plugins_manifest import parse_manifest_file
        from tools.plugin_guard import scan_plugin, format_scan_report

        scan = scan_plugin(target, source='local Flymes catalog candidate')
        print(format_scan_report(scan))
        if scan.verdict == 'dangerous':
            raise SystemExit('Plugin scan blocked the candidate')
        report = validate_plugin_dir(target)
        print(json.dumps(report.to_dict(), indent=2))
        if not report.ok:
            raise SystemExit('Hermes validation failed')
        config = home / 'config.yaml'
        original = b'# keep this comment\nplugins:\n  enabled: [unrelated]\n  disabled: [flymes]\n'
        config.write_bytes(original)
        setup = [sys.executable, '-m', 'flymes.cli', 'install']
        subprocess.run(setup, cwd=target, check=True)
        subprocess.run(setup, cwd=target, check=True)
        import yaml
        settings = yaml.safe_load(config.read_text(encoding='utf-8'))
        assert settings['plugins']['enabled'] == ['unrelated', 'flymes']
        assert 'flymes' not in settings['plugins']['disabled']
        assert config.read_text(encoding='utf-8').startswith('# keep this comment')
        assert (home / 'config.yaml.flymes-backup').read_bytes() == original
        assert not (home / 'plugins/flymes-worker').exists()
        manager = PluginManager(str(home))
        manager._load_plugin(parse_manifest_file(target / 'plugin.yaml', target, 'user', ''))
        state = next(p for p in manager.list_plugins() if p['name'] == 'flymes')
        assert state['enabled'] and not state['error'], state
        assert (target / 'desktop/plugin.js').read_bytes() == (source / 'desktop/plugin.js').read_bytes()
        print('PASS: package scan, capability probe, Agent load, Desktop bytes, and repeat setup in a temporary home')


if __name__ == '__main__':
    main()
