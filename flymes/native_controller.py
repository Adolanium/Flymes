"""Session-bound selection and one-shot authorization for Hermes tool calls."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from threading import RLock
import time
import uuid

from .data import Connectome
from .neural import ACTIONS, Simulator

MODES = ('REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'HERMES')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class NativeController:
    """Never executes a tool. Call handle from a worker thread."""

    def __init__(self, root: Path, dataset: Path, simulator_factory=None):
        self.root, self.dataset = Path(root), Path(dataset)
        self.factory = simulator_factory or (lambda: Simulator(Connectome.load(self.dataset), seed=7))
        self.lock = RLock()
        self.status = 'disabled'
        self.session_id = self.workspace = self.run_id = None
        self.simulator = None
        self.mode = 'REAL'
        self.step = 0
        self.observation = {}
        self.history = []
        self.pending = self.inflight = self.decision = self.selected = None
        self.comparisons = []
        self.max_steps, self.timeout_seconds = 100, 1800
        self.started = 0
        self.last_action = None
        self.review_each = False
        self.completed_results = {}

    @staticmethod
    def _compact(decision):
        if decision is None:
            return None
        return {key: value for key, value in decision.items()
                if key not in ('sample', 'sample_edges', 'dataset', 'encoder')}

    def _snapshot(self):
        selected = None
        if self.selected:
            args = canonical(self.selected['args'])
            selected = {'action': self.selected['action'], 'tool': self.selected['tool'][:256],
                        'reason': self.selected['reason'][:1024], 'args_preview': args[:4096],
                        'args_truncated': len(args) > 4096}
        decision = self._compact(self.decision)
        if decision is not None:
            decision['sample'] = self.decision.get('sample', [])[:320]
            decision['sample_edges'] = self.decision.get('sample_edges', [])[:1200]
        return deepcopy(dict(kind='native', status=self.status, enabled=self.status in ('active', 'paused'), session_id=self.session_id,
            workspace=self.workspace, run_id=self.run_id, mode=self.mode, step=self.step,
            decision=decision, selected=selected, last_selection=selected,
            observation=self.observation, history=self.history, comparisons=[self._compact(d) for d in self.comparisons],
            pending=bool(self.pending), inflight=bool(self.inflight), max_steps=self.max_steps,
            timeout_seconds=self.timeout_seconds, review_each=self.review_each))

    def _log(self, event):
        with (self.run_path / 'events.jsonl').open('a', encoding='utf-8') as out:
            out.write(canonical(event) + '\n')
        self.history.append(event)
        self.history = self.history[-8:]

    def _ready(self, allow_paused=False):
        if self.status not in (('active', 'paused') if allow_paused else ('active',)):
            raise ValueError('Controller is ' + self.status)
        if time.monotonic() - self.started > self.timeout_seconds:
            raise ValueError('Native run timeout; release explicitly to return control')

    @staticmethod
    def _session(body):
        value = body.get('session_id')
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ValueError('A nonempty session_id of at most 160 characters is required')
        return value

    def handle(self, body: dict) -> dict:
        with self.lock:
            if not isinstance(body, dict):
                raise ValueError('Command must be an object')
            command = body.get('command')
            if command == 'status':
                return self._snapshot()
            session = self._session(body)
            if command == 'enable':
                return self._enable(body, session)
            if command == 'authorize' and (session != self.session_id or self.status in ('disabled', 'released')):
                return {'allowed': True, 'gated': False}
            if session != self.session_id:
                raise ValueError('Session does not own this controller')
            if command == 'release':
                self._log({'event': 'release', 'step': self.step})
                self.status, self.pending, self.inflight = 'released', None, None
            elif command == 'pause':
                if self.status != 'active':
                    raise ValueError('Only active runs may pause')
                self.status = 'paused'
            elif command == 'resume':
                if self.status != 'paused':
                    raise ValueError('Only paused runs may resume')
                self.status = 'active'
            elif command == 'propose':
                return self._propose(body)
            elif command == 'selection':
                self._ready(allow_paused=True)
                if not self.pending:
                    raise ValueError('No pending selection')
                return dict(self._snapshot(), decision_id=self.pending['id'],
                            tool=self.selected['tool'], args=deepcopy(self.selected['args']))
            elif command == 'authorize':
                try:
                    self._ready()
                except ValueError as exc:
                    return {'allowed': False, 'gated': True, 'reason': str(exc)}
                if self.pending is None or self.inflight is not None:
                    return {'allowed': False, 'gated': True, 'reason': 'No unconsumed selection'}
                chosen = self.selected
                if body.get('tool') != chosen['tool'] or canonical(body.get('args')) != canonical(chosen['args']):
                    return {'allowed': False, 'gated': True, 'reason': 'Tool or arguments differ from selected proposal'}
                self.inflight, self.pending = self.pending, None
                self.inflight['tool_call_id'] = body.get('tool_call_id')
                return {'allowed': True, 'gated': True, 'decision_id': self.inflight['id']}
            elif command == 'result':
                return self._result(body)
            elif command == 'compare':
                return self._compare(body)
            elif command == 'apply_comparison':
                return self._apply_comparison(body)
            else:
                raise ValueError('Unknown native command')
            return self._snapshot()

    def _enable(self, body, session):
        if self.status in ('active', 'paused'):
            raise ValueError('Release the existing native run before enabling another')
        workspace = body.get('workspace')
        if not isinstance(workspace, str) or not workspace.strip():
            raise ValueError('An existing workspace directory is required')
        workspace = Path(workspace).expanduser()
        if not workspace.is_absolute():
            raise ValueError('Workspace must be an absolute directory path')
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError('Workspace directory does not exist')
        mode = body.get('mode', 'REAL')
        if mode not in MODES:
            raise ValueError('Unknown native mode')
        cap, timeout = body.get('max_steps', 100), body.get('timeout_seconds', 1800)
        if type(cap) is not int or not 1 <= cap <= 1000:
            raise ValueError('max_steps must be an integer in 1..1000')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 86400:
            raise ValueError('timeout_seconds must be in 1..86400')
        review_each = body.get('review_each', False)
        if type(review_each) is not bool:
            raise ValueError('review_each must be a boolean')
        simulator = self.factory()
        run_id = uuid.uuid4().hex
        run_path = self.root / '.flymes' / 'native-runs' / run_id
        run_path.mkdir(parents=True)
        self.simulator, self.run_id, self.run_path = simulator, run_id, run_path
        self.session_id, self.workspace, self.mode = session, str(workspace), mode
        self.max_steps, self.timeout_seconds = cap, timeout
        self.review_each = review_each
        self.started = time.monotonic()
        self.step, self.observation, self.history, self.comparisons = 0, {}, [], []
        self.completed_results = {}
        self.pending = self.inflight = self.decision = self.selected = self.last_action = None
        self.status = 'active'
        return self._snapshot()

    def _choose(self, operation, mode, lesion_percent=30):
        candidates = operation['candidates']
        if mode == 'HERMES':
            index = operation['preferred_index']
            if index is None:
                return {'mode': mode, 'available': False, 'reason': 'No Hermes preferred_index supplied', 'neural_choice': False}
            return {'mode': mode, 'action': candidates[index]['action'], 'neural_choice': False,
                    'selection_source': 'Hermes supplied preferred_index', 'selected_index': index}
        if mode == 'LESIONED':
            self.simulator.lesion(lesion_percent, seed=7)
        decision = self.simulator.decide(operation['observation'], [c['action'] for c in candidates], mode)
        decision['neural_choice'] = True
        return decision

    def _propose(self, body):
        self._ready()
        if self.pending or self.inflight:
            raise ValueError('Outstanding operation exists; use flymes_choose command current to retrieve its selection')
        if self.step >= self.max_steps:
            raise ValueError('Native step cap reached; release explicitly to return control')
        candidates = body.get('candidates')
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 6:
            raise ValueError('Supply 2..6 candidates')
        if len(canonical(candidates).encode('utf-8')) > 65536:
            raise ValueError('Candidates exceed 64 KiB')
        for candidate in candidates:
            if (not isinstance(candidate, dict) or candidate.get('action') not in ACTIONS
                or not isinstance(candidate.get('tool'), str) or not candidate['tool'].strip()
                or not isinstance(candidate.get('args'), dict) or not isinstance(candidate.get('reason'), str)):
                raise ValueError('Invalid candidate action, tool, args or reason')
            if len(canonical(candidate['args']).encode('utf-8')) > 32768:
                raise ValueError('Each proposed tool argument object must fit in 32 KiB')
        if len({c['action'] for c in candidates}) != len(candidates):
            raise ValueError('Candidates must have distinct actions')
        mode = body.get('mode', self.mode)
        if mode not in MODES:
            raise ValueError('Unknown native mode')
        preferred = body.get('preferred_index')
        if preferred is not None and (type(preferred) is not int or not 0 <= preferred < len(candidates)):
            raise ValueError('preferred_index is outside candidates')
        if mode == 'HERMES' and preferred is None:
            raise ValueError('HERMES mode requires preferred_index')
        operation = dict(id=uuid.uuid4().hex, candidates=deepcopy(candidates), preferred_index=preferred,
                         observation=deepcopy(self.observation), checkpoint=self.simulator.checkpoint())
        path = self.run_path / f'decision-{self.step + 1:04d}.json'
        path.write_text(canonical(operation), encoding='utf-8')
        try:
            decision = self._choose(operation, mode)
            self._ready()
            selected = deepcopy(next(c for c in candidates if c['action'] == decision['action']))
            self._log({'event': 'decision', 'step': self.step + 1, 'decision_id': operation['id'],
                       'mode': mode, 'action': decision['action'], 'observation': self.observation})
        except Exception:
            self.simulator.restore(operation['checkpoint'])
            raise
        self.mode, self.decision, self.selected, self.pending = mode, decision, selected, operation
        self.step += 1
        self.comparisons = []
        if self.review_each:
            self.status = 'paused'
        return dict(self._snapshot(), decision_id=operation['id'], tool=selected['tool'], args=deepcopy(selected['args']))

    def _result(self, body):
        result_key = canonical([body.get('decision_id'), body.get('tool_call_id')])
        result_digest = hashlib.sha256(canonical(body).encode('utf-8')).hexdigest()
        if result_key in self.completed_results:
            if self.completed_results[result_key] != result_digest:
                raise ValueError('Completed result was retried with a different payload')
            return self._snapshot()
        if self.inflight is None:
            raise ValueError('No authorized tool awaiting a result')
        if body.get('decision_id') != self.inflight['id']:
            raise ValueError('Result decision_id does not match authorized operation')
        if self.inflight.get('tool_call_id') is not None and body.get('tool_call_id') != self.inflight['tool_call_id']:
            raise ValueError('Result tool_call_id does not match authorized operation')
        observation = {'elapsed_steps': self.observation.get('elapsed_steps', 0) + 1,
                       'repeated_actions': self.observation.get('repeated_actions', 0) + 1 if self.last_action == self.selected['action'] else 0}
        code = body.get('exit_code')
        if type(code) in (int, float) and math.isfinite(code):
            observation['last_exit_code'] = code
        status = body.get('status', 'unknown')
        if not isinstance(status, str):
            raise ValueError('Result status must be a string')
        record = dict(body, tool=self.selected['tool'], tool_call_id=self.inflight.get('tool_call_id'))
        payload = canonical(record).encode('utf-8')
        if len(payload) > 128 * 1024:
            raise ValueError('Result exceeds 128 KiB')
        (self.run_path / f'result-{self.step:04d}.json').write_bytes(payload)
        self._log({'event': 'result', 'step': self.step, 'decision_id': self.inflight['id'],
                   'status': status[:80], 'result_sha256': hashlib.sha256(payload).hexdigest(), 'observation': observation})
        self.observation, self.last_action = observation, self.selected['action']
        self.inflight = None
        self.completed_results[result_key] = result_digest
        if len(self.completed_results) > 100:
            del self.completed_results[next(iter(self.completed_results))]
        return self._snapshot()

    def _compare(self, body):
        self._ready(allow_paused=True)
        if not self.pending:
            raise ValueError('Comparison requires a pending decision before authorization')
        percent = body.get('lesion_percent', 30)
        if type(percent) not in (int, float) or not math.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError('lesion_percent must be in 0..100')
        current = self.simulator.checkpoint()
        comparisons = []
        try:
            for mode in MODES:
                self.simulator.restore(self.pending['checkpoint'])
                decision = self._choose(self.pending, mode, percent)
                self._ready(allow_paused=True)
                comparisons.append(dict(decision, comparison_kind='open-loop', repository_executed=False,
                                        decision_id=self.pending['id']))
        finally:
            self.simulator.restore(current)
        self.comparisons = comparisons
        return self._snapshot()

    def _apply_comparison(self, body):
        self._ready(allow_paused=True)
        if self.status != 'paused' or not self.pending:
            raise ValueError('Applying a comparison requires a paused pending decision')
        mode = body.get('mode')
        if mode not in MODES:
            raise ValueError('Unknown native mode')
        percent = body.get('lesion_percent', 30)
        if type(percent) not in (int, float) or not math.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError('lesion_percent must be in 0..100')
        current = self.simulator.checkpoint()
        try:
            self.simulator.restore(self.pending['checkpoint'])
            decision = self._choose(self.pending, mode, percent)
            if decision.get('available') is False:
                raise ValueError(decision['reason'])
            self._ready(allow_paused=True)
            selected = deepcopy(next(c for c in self.pending['candidates'] if c['action'] == decision['action']))
            self._log({'event': 'intervention', 'step': self.step, 'decision_id': self.pending['id'],
                       'mode': mode, 'action': decision['action'], 'lesion_percent': percent})
        except Exception:
            self.simulator.restore(current)
            raise
        self.mode, self.decision, self.selected = mode, decision, selected
        return dict(self._snapshot(), decision_id=self.pending['id'], tool=selected['tool'], args=deepcopy(selected['args']))
