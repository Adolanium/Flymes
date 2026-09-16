import json
import time

import numpy as np
import pytest
from scipy import sparse

from flymes.data import Connectome
from flymes.native_controller import NativeController
from flymes.neural import Simulator


@pytest.fixture
def controller(tmp_path):
    graph = Connectome(sparse.csr_matrix(np.eye(12)), np.arange(12), {}, {'mode': 'TEST FIXTURE'})
    ctrl = NativeController(tmp_path, tmp_path, lambda: Simulator(graph, seed=7))
    ctrl.handle({'command': 'enable', 'session_id': 'chat', 'workspace': str(tmp_path)})
    return ctrl


def call(ctrl, command, **kwargs):
    return ctrl.handle(dict(command=command, session_id='chat', **kwargs))


def propose(ctrl, **kwargs):
    return call(ctrl, 'propose', candidates=[
        {'action': 'INSPECT', 'tool': 'terminal', 'args': {'command': 'ls', 'nested': {'b': 2, 'a': 1}}, 'reason': 'Read files'},
        {'action': 'TEST', 'tool': 'terminal', 'args': {'command': 'pytest'}, 'reason': 'Run tests'},
    ], **kwargs)


def test_native_records_live_outside_source_tree(tmp_path):
    source, state = tmp_path / 'source', tmp_path / 'state'
    source.mkdir()
    graph = Connectome(sparse.eye(12, format='csr'), np.arange(12), {}, {})
    ctrl = NativeController(source, tmp_path, lambda: Simulator(graph), state_root=state)
    ctrl.handle({'command': 'enable', 'session_id': 'chat', 'workspace': str(source)})
    propose(ctrl)
    assert ctrl.run_path.is_relative_to(state)
    assert (ctrl.run_path / 'decision-0001.json').is_file()
    assert not (source / '.flymes').exists()


def test_exact_one_shot_authorization_and_truthful_observation(controller):
    ctrl = controller
    choice = propose(ctrl, mode='HERMES', preferred_index=0)
    assert choice['args'] == {'command': 'ls', 'nested': {'b': 2, 'a': 1}}
    assert not choice['decision']['neural_choice']
    assert not call(ctrl, 'authorize', tool='terminal', args={'command': 'pytest'})['allowed']
    authorization = call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'], tool_call_id='host-1')
    assert authorization['allowed']
    assert not call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'])['allowed']
    with pytest.raises(ValueError, match='tool_call_id'):
        call(ctrl, 'result', decision_id=choice['decision_id'], tool_call_id='wrong')
    result = call(ctrl, 'result', decision_id=choice['decision_id'], tool_call_id='host-1', exit_code=0,
                  tests_passed=100, verified=True, output='secret token')
    assert result['observation'] == {'elapsed_steps': 1, 'repeated_actions': 0, 'last_exit_code': 0}
    with pytest.raises(ValueError, match='No authorized'):
        call(ctrl, 'result', decision_id=choice['decision_id'])
    log = (ctrl.run_path / 'events.jsonl').read_text()
    assert 'secret token' not in log and 'tests_passed' not in log
    saved = json.loads((ctrl.run_path / 'decision-0001.json').read_text())
    assert saved['candidates'][0]['args'] == choice['args']


def test_session_isolation_pause_release(controller):
    ctrl = controller
    choice = propose(ctrl)
    assert ctrl.handle({'command': 'authorize', 'session_id': 'other'}) == {'allowed': True, 'gated': False}
    with pytest.raises(ValueError, match='Session'):
        ctrl.handle({'command': 'release', 'session_id': 'other'})
    call(ctrl, 'pause')
    assert not call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'])['allowed']
    with pytest.raises(ValueError, match='paused'):
        propose(ctrl)
    call(ctrl, 'resume')
    assert call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'])['allowed']
    call(ctrl, 'release')
    assert call(ctrl, 'authorize', tool='anything', args={}) == {'allowed': True, 'gated': False}


def test_comparisons_same_checkpoint_and_restore(controller):
    ctrl = controller
    choice = propose(ctrl, preferred_index=1)
    after = ctrl.simulator.checkpoint()
    comparison = call(ctrl, 'compare', lesion_percent=100)['comparisons']
    assert ctrl.simulator.checkpoint() == after
    assert {d['mode'] for d in comparison} == {'REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'HERMES'}
    assert len({d['checkpoint_before_hash'] for d in comparison if d['mode'] != 'HERMES'}) == 1
    assert comparison[0]['state_hash'] == choice['decision']['state_hash']
    assert comparison[-1]['action'] == 'TEST' and not comparison[-1]['neural_choice']
    assert all(not d['repository_executed'] for d in comparison)
    assert ctrl.pending and ctrl.selected['args'] == choice['args']


def test_validation_caps_and_timeouts_fail_closed(controller):
    ctrl = controller
    with pytest.raises(ValueError, match='preferred_index'):
        propose(ctrl, mode='HERMES')
    ctrl.max_steps = 0
    with pytest.raises(ValueError, match='cap'):
        propose(ctrl)
    ctrl.max_steps = 10
    choice = propose(ctrl)
    ctrl.started = time.monotonic() - 100000
    assert not call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'])['allowed']
    assert call(ctrl, 'status')['status'] == 'active'
    call(ctrl, 'release')
    assert call(ctrl, 'authorize')['allowed']


def test_paused_review_comparison_apply_and_resume(controller):
    ctrl = controller
    call(ctrl, 'release')
    call(ctrl, 'enable', workspace=str(ctrl.root), review_each=True)
    choice = propose(ctrl, preferred_index=1)
    assert choice['status'] == 'paused'
    after = ctrl.simulator.checkpoint()
    comparisons = call(ctrl, 'compare')['comparisons']
    assert ctrl.simulator.checkpoint() == after
    assert all('sample' not in d and 'encoder' not in d for d in comparisons)
    applied = call(ctrl, 'apply_comparison', mode='HERMES')
    assert applied['status'] == 'paused' and applied['step'] == choice['step']
    assert applied['args'] == {'command': 'pytest'}
    assert applied['decision_id'] == choice['decision_id']
    assert ctrl.simulator.checkpoint() == ctrl.pending['checkpoint']
    assert call(ctrl, 'selection')['args'] == applied['args']
    assert not call(ctrl, 'authorize', tool=applied['tool'], args=applied['args'])['allowed']
    call(ctrl, 'resume')
    assert call(ctrl, 'authorize', tool=applied['tool'], args=applied['args'])['allowed']
    assert not call(ctrl, 'authorize', tool=applied['tool'], args=applied['args'])['allowed']
    call(ctrl, 'result', decision_id=applied['decision_id'], status='blocked', result={'error': 'host denied execution'})
    saved = json.loads((ctrl.run_path / 'result-0001.json').read_text())
    assert saved['status'] == 'blocked' and saved['tool'] == 'terminal'
    assert saved['result'] == {'error': 'host denied execution'}
    assert ctrl.history[-1]['status'] == 'blocked'
    assert 'last_exit_code' not in ctrl.observation


def test_status_bounded_and_relative_workspace_rejected(controller):
    ctrl = controller
    call(ctrl, 'release')
    with pytest.raises(ValueError, match='absolute'):
        call(ctrl, 'enable', workspace='.')
    call(ctrl, 'enable', workspace=str(ctrl.root))
    with pytest.raises(ValueError, match='32 KiB'):
        call(ctrl, 'propose', preferred_index=0, candidates=[
            {'action': 'INSPECT', 'tool': 'terminal', 'args': {'command': 'x' * 33000}, 'reason': 'Read'},
            {'action': 'TEST', 'tool': 'terminal', 'args': {}, 'reason': 'Test'}])
    huge = {'command': 'x' * 31000}
    choice = call(ctrl, 'propose', mode='HERMES', preferred_index=0, candidates=[
        {'action': 'INSPECT', 'tool': 'terminal', 'args': huge, 'reason': 'Read'},
        {'action': 'TEST', 'tool': 'terminal', 'args': {}, 'reason': 'Test'}])
    assert choice['args'] == huge
    snapshot = call(ctrl, 'status')
    assert len(json.dumps(snapshot).encode()) < 60000
    assert 'args' not in snapshot['selected'] and snapshot['selected']['args_truncated']


def test_primary_measured_graph_retained_in_bounded_status(tmp_path):
    rows = np.repeat(np.arange(320), 4)
    cols = (rows + np.tile(np.arange(4), 320)) % 320
    graph = Connectome(sparse.csr_matrix((np.ones(1280), (rows, cols)), shape=(320, 320)),
                       np.arange(10000000000000000, 10000000000000320), {}, {'mode': 'TEST FIXTURE'})
    ctrl = NativeController(tmp_path, tmp_path, lambda: Simulator(graph, seed=7))
    call(ctrl, 'enable', workspace=str(tmp_path))
    propose(ctrl, preferred_index=0)
    status = call(ctrl, 'compare')
    assert len(status['decision']['sample']) == 320
    assert len(status['decision']['sample_edges']) == 1200
    assert status['decision']['sample'] == ctrl.decision['sample']
    assert all('sample' not in comparison for comparison in status['comparisons'])
    assert len(json.dumps(status).encode()) < 60000


def test_result_retry_is_idempotent_and_rejects_changed_payload(controller):
    ctrl = controller
    choice = propose(ctrl)
    call(ctrl, 'authorize', tool=choice['tool'], args=choice['args'], tool_call_id='call-1')
    result = dict(decision_id=choice['decision_id'], tool_call_id='call-1', status='completed',
                  exit_code=0, result={'output': 'done'})
    first = call(ctrl, 'result', **result)
    persisted = (ctrl.run_path / 'events.jsonl').read_bytes()
    duplicate = call(ctrl, 'result', **result)
    assert duplicate == first
    assert duplicate['observation']['elapsed_steps'] == 1
    assert (ctrl.run_path / 'events.jsonl').read_bytes() == persisted
    with pytest.raises(ValueError, match='different payload'):
        call(ctrl, 'result', **dict(result, exit_code=1))
