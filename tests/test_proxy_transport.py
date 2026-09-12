import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from dashboard.plugin_api import _forward


def test_reset_connection_becomes_service_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    config = tmp_path / 'plugins/flymes/service.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'port': 8742, 'token': 'test-token'}), encoding='utf-8')
    with patch('dashboard.plugin_api.urllib.request.build_opener') as opener:
        opener.return_value.open.side_effect = ConnectionResetError(10054, 'Connection reset')
        with pytest.raises(HTTPException) as error:
            _forward('state')
    assert error.value.status_code == 503
    assert 'disconnected' in error.value.detail
