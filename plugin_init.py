"""Bridge native Hermes calls to the session-scoped Flymes controller."""
import json
import os
import sqlite3
from pathlib import Path
from threading import Lock
import urllib.request

ACTIONS = ['SEARCH', 'INSPECT', 'IMPLEMENT', 'TEST', 'REVIEW', 'FINISH']


def _directory():
    return Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes')) / 'plugins/flymes'


def _gate(session_id):
    try:
        data = json.loads((_directory() / 'native-gate.json').read_text(encoding='utf-8-sig'))
        if session_id and data.get('session_id') == session_id:
            return data
        if not session_id:
            return None
        # Hermes publishes a compression child before rotating its stored ID.
        # Follow durable lineage read-only, so a rollover cannot silently ungate.
        db = _directory().parents[1] / 'state.db'
        if db.is_file():
            with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=1) as connection:
                current, seen = session_id, set()
                while current and current not in seen and len(seen) < 128:
                    seen.add(current)
                    row = connection.execute('SELECT parent_session_id FROM sessions WHERE id = ?', (current,)).fetchone()
                    current = row[0] if row else None
                    if current == data.get('session_id'):
                        return {**data, 'continuation': True}
        return None
    except (OSError, ValueError, sqlite3.Error):
        return None


def _rpc(body, timeout):
    config = json.loads((_directory() / 'service.json').read_text(encoding='utf-8-sig'))
    port = int(config['port'])
    if not 1024 <= port <= 65535:
        raise ValueError('Invalid companion port')
    request = urllib.request.Request(f'http://127.0.0.1:{port}/native',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + config['token'], 'Content-Type': 'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as response:
        return json.load(response)


def _hidden(name):
    return (not isinstance(name, str) or not name.strip() or name == 'flymes_choose'
            or any(word in name.lower() for word in ('delegate', 'batch', 'parallel', 'spawn_agent'))
            or name in ('execute_tool', 'run_tool'))


def register(ctx):
    permits, unreported, lock = {}, {}, Lock()

    def choose(args, session_id=None, **kwargs):
        try:
            marker = _gate(session_id)
            if not marker:
                raise ValueError('Enable Flymes for this session in the panel first')
            if marker.get('continuation'):
                raise ValueError('Hermes changed the session ID. Return control in the panel, then enable Fly Mode for this continuation.')
            with lock:
                pending = [(key, body) for key, body in unreported.items() if key[0] == session_id]
            for key, body in pending:
                try:
                    acknowledgement = _rpc(body, 3)
                    if not isinstance(acknowledgement, dict) or acknowledgement.get('error'):
                        raise ValueError('Result was not acknowledged')
                except Exception as exc:
                    raise ValueError('Reconnect to Flymes before selecting another tool; the last result is unreported') from exc
                with lock:
                    unreported.pop(key, None)
            command = args.get('command', 'propose')
            if command == 'current':
                return json.dumps(_rpc({'command': 'selection', 'session_id': session_id}, 3), ensure_ascii=False)
            if command != 'propose':
                raise ValueError('Unknown command')
            candidates, index = args.get('candidates'), args.get('preferred_index')
            if not isinstance(candidates, list) or not 2 <= len(candidates) <= 6:
                raise ValueError('Supply 2..6 candidates')
            seen = set()
            for candidate in candidates:
                if (not isinstance(candidate, dict) or candidate.get('action') not in ACTIONS
                        or candidate['action'] in seen or _hidden(candidate.get('tool'))
                        or not isinstance(candidate.get('args'), dict)
                        or not isinstance(candidate.get('reason'), str)):
                    raise ValueError('Use distinct valid actions with normal tools, object args, and reasons')
                seen.add(candidate['action'])
                try:
                    from tools.registry import registry
                except ImportError:
                    registry = None
                if registry is not None and registry.get_entry(candidate['tool']) is None:
                    raise ValueError('Unknown native tool: ' + candidate['tool'])
            if type(index) is not int or not 0 <= index < len(candidates):
                raise ValueError('preferred_index must identify a candidate')
            if len(json.dumps(candidates).encode('utf-8')) > 65536:
                raise ValueError('Candidates exceed 64 KiB')
            return json.dumps(_rpc({'command': 'propose', 'session_id': session_id,
                'candidates': candidates, 'preferred_index': index}, 120), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({'error': str(exc), 'instruction': 'No tool authorized. The panel can Return control.'})

    def pre_tool_call(tool_name=None, args=None, session_id=None, tool_call_id=None, **kwargs):
        marker = _gate(session_id)
        if marker and marker.get('continuation'):
            return {'action': 'block', 'message': 'Hermes changed the session ID. Return control in the panel and re-enable Fly Mode for this continuation.'}
        # These native catalog tools expose schemas; they execute no task operation.
        if not marker or tool_name in ('flymes_choose', 'tool_describe', 'tool_search'):
            return None
        try:
            if _hidden(tool_name):
                raise ValueError('Batch and delegated calls are unavailable')
            reply = _rpc({'command': 'authorize', 'session_id': session_id,
                'tool': tool_name, 'args': args, 'tool_call_id': tool_call_id}, 3)
            if reply.get('allowed') is True and reply.get('gated') is True:
                if reply.get('decision_id'):
                    with lock:
                        permits[(session_id, tool_call_id)] = reply['decision_id']
                return None
            message = reply.get('reason', 'Use flymes_choose before the selected tool')
        except Exception:
            message = 'Flymes could not authorize this call. Reconnect or use Return control in the panel.'
        return {'action': 'block', 'message': message}

    def post_tool_call(tool_name=None, args=None, session_id=None, tool_call_id=None, result=None, status=None, **kwargs):
        if not _gate(session_id) or tool_name == 'flymes_choose':
            return None
        with lock:
            decision_id = permits.pop((session_id, tool_call_id), None)
        if not decision_id:
            return None
        body = {'command': 'result', 'session_id': session_id, 'tool': tool_name,
            'args': args, 'tool_call_id': tool_call_id, 'decision_id': decision_id,
            'status': status,
            'result': (result if isinstance(result, str) else json.dumps(result, default=str))[:16000]}
        structured_result = result
        if isinstance(result, str):
            try:
                structured_result = json.loads(result)
            except ValueError:
                structured_result = None
        if status == 'blocked':
            body['result'] = 'Blocked by native Hermes permissions. ' + body['result']
        elif isinstance(structured_result, dict) and type(structured_result.get('exit_code')) is int:
            body['exit_code'] = structured_result['exit_code']
        key = (session_id, tool_call_id)
        with lock:
            unreported[key] = body
        try:
            acknowledgement = _rpc(body, 3)
            if isinstance(acknowledgement, dict) and not acknowledgement.get('error'):
                with lock:
                    unreported.pop(key, None)
        except Exception:
            pass
        return None

    def pre_llm_call(session_id=None, **kwargs):
        marker = _gate(session_id)
        if not marker:
            return None
        if marker.get('continuation'):
            return {'context': 'Flymes detected a new session ID after compression. Do not execute tools. Ask the user to Return control in the panel and re-enable Fly Mode for this continuation.'}
        return {'context': 'Flymes native control is enabled. Task directory: '
            + str(marker.get('workspace', '')) + '. Before each tool call use flymes_choose to propose '
            '2..6 concrete alternatives with distinct action categories and preferred_index. Execute the exact '
            'selected normal tool and arguments once. Do not batch or delegate. Native Hermes permissions '
            'and approvals apply. After pause/resume use flymes_choose command current to retrieve the current exact selection. '
            'Do not claim tests passed without results. The user can Return control in the panel.'}

    ctx.register_tool(name='flymes_choose', toolset='flymes', handler=choose, schema={
        'description': 'Propose native tool alternatives for Flymes selection. Does not execute tools.',
        'parameters': {'type': 'object', 'properties': {
            'command': {'type': 'string', 'enum': ['propose', 'current'], 'default': 'propose'},
            'candidates': {'type': 'array', 'minItems': 2, 'maxItems': 6, 'items': {'type': 'object',
                'properties': {'action': {'type': 'string', 'enum': ACTIONS}, 'tool': {'type': 'string'},
                    'args': {'type': 'object'}, 'reason': {'type': 'string'}},
                'required': ['action', 'tool', 'args', 'reason'], 'additionalProperties': False}},
            'preferred_index': {'type': 'integer', 'minimum': 0, 'maximum': 5}},
            'additionalProperties': False}})
    ctx.register_hook('pre_llm_call', pre_llm_call)
    ctx.register_hook('pre_tool_call', pre_tool_call)
    ctx.register_hook('post_tool_call', post_tool_call)
