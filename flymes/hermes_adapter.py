"""Bounded macro-actions through Hermes' configured plugin completion facade."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import time

from .boundary import BoundaryError, WorkspaceBoundary

SCHEMA = {'type': 'object', 'properties': {
    'operation': {'type': 'string', 'enum': ['search', 'read', 'replace', 'review', 'done']},
    'path': {'type': 'string'}, 'query': {'type': 'string'},
    'content': {'type': 'string'}, 'expected_sha256': {'type': 'string'},
    'summary': {'type': 'string'}},
    'required': ['operation', 'path', 'query', 'content', 'expected_sha256', 'summary'], 'additionalProperties': False}


class HermesAdapter:
    def __init__(self, workspace, editable_files=('app.py',), verifier=None,
                 hermes_python=None, hermes_root=None, llm=None, max_calls=3, timeout=90):
        self.boundary = WorkspaceBoundary(Path(workspace), editable_files)
        self.verifier = verifier
        self.llm = llm
        default_root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'hermes' / 'hermes-agent'
        self.hermes_root = Path(hermes_root or os.environ.get('FLYMES_HERMES_ROOT', default_root))
        self.hermes_python = str(hermes_python or os.environ.get('FLYMES_HERMES_PYTHON', self.hermes_root / '.venv/Scripts/python.exe'))
        self.max_calls, self.timeout = max_calls, timeout
        self._lock = asyncio.Lock()
        self._cancelled = False
        self._process = None
        self._results = {}
        self._session_run = None

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.returncode is None:
            self._process.kill()

    async def _complete(self, prompt: str):
        kwargs = dict(instructions=prompt, input=[{'type': 'text', 'text': 'Perform one allowed operation.'}],
                      json_schema=SCHEMA, max_tokens=1800, temperature=0, timeout=self.timeout,
                      purpose='flymes.bounded_action')
        if self.llm is not None:
            result = self.llm(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        if not Path(self.hermes_python).is_file():
            raise RuntimeError('Hermes Python missing. Set FLYMES_HERMES_PYTHON to the installed Hermes interpreter.')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1]) + os.pathsep + str(self.hermes_root)
        env.setdefault('HERMES_HOME', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'hermes'))
        self._process = await asyncio.create_subprocess_exec(
            self.hermes_python, '-m', 'hermes_cli.main', 'flymes-complete',
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=env, cwd=str(self.hermes_root))
        try:
            out, err = await asyncio.wait_for(self._process.communicate(json.dumps(kwargs).encode()), timeout=self.timeout)
            if self._cancelled:
                raise asyncio.CancelledError()
            if self._process.returncode:
                # Raw provider exceptions can contain credentials. Do not export stderr.
                raise RuntimeError('Hermes completion failed. Run doctor and check the configured provider.')
            lines = out.decode('utf-8').splitlines()
            payload = next((line[len('FLYMES_RESULT='):] for line in reversed(lines) if line.startswith('FLYMES_RESULT=')), None)
            if payload is None:
                raise RuntimeError('Hermes completion returned no result')
            return json.loads(payload)
        finally:
            if self._process and self._process.returncode is None:
                self._process.kill()
                await self._process.wait()
            self._process = None

    async def execute(self, action, task, run_id, step_id, session_id='flymes', evidence=None):
        action = getattr(action, 'value', action)
        if action not in {'SEARCH', 'INSPECT', 'IMPLEMENT', 'TEST', 'REVIEW', 'FINISH'}:
            raise BoundaryError('Unknown action')
        key = (session_id, run_id, step_id)
        if self._session_run is not None and self._session_run != (session_id, run_id):
            raise BoundaryError('Adapter belongs to a different session/run')
        self._session_run = (session_id, run_id)
        if key in self._results:
            if self._results[key]['action'] != action:
                raise BoundaryError('Duplicate step has conflicting action')
            return self._results[key]
        if self._lock.locked():
            raise BoundaryError('One action is already in flight')
        async with self._lock:
            self._cancelled = False
            started = time.monotonic()
            result = {'action': action, 'run_id': run_id, 'step_id': step_id, 'session_id': session_id,
                      'adapter': 'injected-test-llm' if self.llm is not None else 'hermes-native-cli-plugin',
                      'status': 'ok', 'operations': [], 'model_calls': 0, 'provider': None, 'model': None,
                      'usage': {}, 'verified': False}
            try:
                async with asyncio.timeout(self.timeout):
                    if action in {'TEST', 'FINISH'}:
                        self.boundary.validate_current()
                        if self.verifier is None:
                            raise BoundaryError('No independent verifier configured')
                        checked = await asyncio.to_thread(self.verifier, self.boundary.root)
                        if self._cancelled:
                            raise asyncio.CancelledError()
                        result.update(checked)
                        result['operations'].append({'operation': 'approved_test', 'result': checked})
                    else:
                        await self._reason(action, task, evidence, result)
            except (asyncio.CancelledError, TimeoutError) as exc:
                self.cancel()
                result.update(status='cancelled' if isinstance(exc, asyncio.CancelledError) else 'timeout', safety_override=True)
            except (BoundaryError, ValueError, RuntimeError) as exc:
                result.update(status='error', error=str(exc), safety_override=True)
            result['duration_s'] = time.monotonic() - started
            result['diff'] = self.boundary.diff()
            self._results[key] = result
            return result

    async def _reason(self, action, task, evidence, result):
        allowed = {'SEARCH': {'search', 'done'}, 'INSPECT': {'read', 'done'},
                   'IMPLEMENT': {'read', 'replace', 'done'}, 'REVIEW': {'review', 'read', 'done'}}[action]
        context = {'task': task, 'action': action, 'allowed_operations': sorted(allowed),
                   'files': self.boundary.files(), 'evidence': evidence,
                   'policy': 'Only app.py is accessible. IMPLEMENT may replace visible_items(items, query) with one return list comprehension, using only items/query/item and zero-argument lower/casefold/strip string methods. No imports, assignments, other functions, shell, or tools. Read first for expected_sha256. The replace content field must contain the entire plain Python file, with real newline characters, without Markdown fences. Only an optional module docstring followed by the function is allowed. All schema fields are required; use empty strings for unused fields. Put code in content, never in summary. Keep summary under 20 words. Return one JSON operation. Never select a different macro-action.'}
        if action == 'REVIEW':
            context['diff'] = self.boundary.diff()
        for _ in range(self.max_calls):
            if self._cancelled:
                raise asyncio.CancelledError()
            response = await self._complete(json.dumps(context, ensure_ascii=False))
            result['model_calls'] += 1
            if is_dataclass(response):
                response = asdict(response)
            operation = response.get('parsed')
            if operation is None:
                operation = json.loads(response.get('text', '{}'))
            if not isinstance(operation, dict) or operation.get('operation') not in allowed:
                raise BoundaryError('Model requested an operation outside the selected action')
            if set(operation) - set(SCHEMA['properties']):
                raise BoundaryError('Unknown operation fields')
            result['provider'], result['model'] = response.get('provider'), response.get('model')
            for k, v in response.get('usage', {}).items():
                if isinstance(v, (int, float)):
                    result['usage'][k] = result['usage'].get(k, 0) + v
            if self._cancelled:
                raise asyncio.CancelledError()
            op = operation['operation']
            if op == 'done':
                result['summary'] = operation.get('summary', '')[:4000]
                break
            if op in {'read', 'replace'} and operation.get('path') not in self.boundary.files():
                raise BoundaryError('File outside permitted set')
            if op == 'read':
                text = self.boundary.read(operation['path'])
                output = {'path': operation['path'], 'content': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}
            elif op == 'search':
                query = operation.get('query', '')
                if not isinstance(query, str) or len(query) > 256:
                    raise BoundaryError('Invalid search query')
                output = {'matches': [{'path': name, 'line': i, 'text': line[:500]} for name in self.boundary.files()
                                      for i, line in enumerate(self.boundary.read(name).splitlines(), 1) if query.casefold() in line.casefold()][:100]}
            elif op == 'review':
                output = {'diff': self.boundary.diff(), 'evidence': evidence}
            else:
                try:
                    output = self.boundary.replace(operation['path'], operation.get('content', ''), operation.get('expected_sha256', ''))
                except BoundaryError as exc:
                    result['operations'].append({'operation': op, 'request': operation, 'rejected': str(exc)})
                    context['history'] = result['operations']
                    continue
            result['operations'].append({'operation': op, 'request': operation, 'result': output})
            context['history'] = result['operations']
            if op == 'replace' or action in {'SEARCH', 'INSPECT', 'REVIEW'}:
                break  # One read-only operation or one bounded edit per action.
        else:
            result['budget_exhausted'] = True
            result['safety_override'] = 'model_call_limit'
