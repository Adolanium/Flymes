import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
import yaml

from flymes import cli
from flymes.paths import state_root

ROOT = Path(__file__).resolve().parents[1]


def test_entry_point_loads_without_companion_dependencies():
    code = """
import importlib.util, json, sys
from unittest.mock import Mock
root = sys.argv[1]
spec = importlib.util.spec_from_file_location('isolated_flymes', root + '/__init__.py', submodule_search_locations=[root])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
ctx = Mock()
module.register(ctx)
print(json.dumps({'tools': [c.kwargs['name'] for c in ctx.register_tool.call_args_list],
                  'hooks': [c.args[0] for c in ctx.register_hook.call_args_list],
                  'commands': [c.kwargs['name'] for c in ctx.register_cli_command.call_args_list]}))
"""
    result = subprocess.run([sys.executable, '-S', '-c', code, str(ROOT)], check=True, capture_output=True, text=True)
    actual = json.loads(result.stdout)
    manifest = yaml.safe_load((ROOT / 'plugin.yaml').read_text())
    assert actual['tools'] == manifest['provides_tools']
    assert actual['hooks'] == manifest['provides_hooks']
    assert actual['commands'] == ['flymes-complete']


def test_setup_checks_interpreter_before_writing(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'home'))
    monkeypatch.delenv('FLYMES_HERMES_PYTHON', raising=False)
    with pytest.raises(RuntimeError, match='interpreter'):
        cli.install()
    assert not (tmp_path / 'home').exists()


def test_setup_copy_has_complete_entry_point(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.setenv('FLYMES_HERMES_PYTHON', sys.executable)
    monkeypatch.setattr(cli.subprocess, 'run', Mock())
    cli.install()
    target = tmp_path / 'plugins/flymes'
    for name in ('__init__.py', 'plugin_init.py', 'plugin_worker.py', 'desktop/plugin.js', 'dashboard/plugin_api.py'):
        assert (target / name).read_bytes() == (ROOT / name).read_bytes()
    assert not (tmp_path / 'plugins/flymes-worker').exists()
    # A package installed at its final location must also support setup.
    monkeypatch.setattr(cli, 'ROOT', target)
    cli.install()


def test_setup_refuses_to_overwrite_catalog_source(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.setenv('FLYMES_HERMES_PYTHON', sys.executable)
    target = tmp_path / 'plugins/flymes'
    target.mkdir(parents=True)
    (target / '.hermes-catalog.json').write_text('{}')
    with pytest.raises(RuntimeError, match='installed catalog package'):
        cli.install()
    assert not (target / '__init__.py').exists()


def test_state_defaults_outside_plugin_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.delenv('FLYMES_STATE_DIR', raising=False)
    assert state_root() == tmp_path / 'flymes'
    monkeypatch.setenv('FLYMES_STATE_DIR', str(tmp_path / 'experiments'))
    assert state_root() == tmp_path / 'experiments'


def test_state_cannot_be_stored_in_replaceable_plugin(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.setenv('FLYMES_STATE_DIR', str(tmp_path / 'plugins/flymes/data'))
    with pytest.raises(ValueError, match='outside'):
        state_root()


def test_doctor_failure_has_nonzero_exit(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['flymes', 'doctor'])
    monkeypatch.setattr(cli, 'doctor', lambda _: {'failures': ['missing dataset']})
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
