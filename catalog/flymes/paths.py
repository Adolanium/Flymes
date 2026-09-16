"""Keep downloaded data and experiment records outside the installed plugin."""
import os
from pathlib import Path


def hermes_home():
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser().resolve()


def state_root():
    path = Path(os.environ.get("FLYMES_STATE_DIR", hermes_home() / "flymes")).expanduser()
    if not path.is_absolute():
        raise ValueError("FLYMES_STATE_DIR must be an absolute path")
    path = path.resolve()
    installed = hermes_home() / 'plugins' / 'flymes'
    if path.is_relative_to(installed):
        raise ValueError("FLYMES_STATE_DIR must be outside the installed plugin directory")
    return path
