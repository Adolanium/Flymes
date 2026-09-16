"""Optional built-in demo transport, registered by the Flymes plugin."""
import json
import sys
from dataclasses import asdict


def register(ctx):
    def complete(args):
        request = json.loads(sys.stdin.buffer.read(131073))
        allowed = {'instructions', 'input', 'json_schema', 'max_tokens', 'temperature', 'timeout', 'purpose'}
        if not isinstance(request, dict) or set(request) - allowed:
            raise ValueError('Unsupported Flymes completion fields')
        request['max_tokens'] = min(int(request.get('max_tokens', 1800)), 1800)
        request['timeout'] = min(float(request.get('timeout', 90)), 180)
        request['purpose'] = 'flymes.bounded_action'
        result = ctx.llm.complete_structured(**request)
        print('FLYMES_RESULT=' + json.dumps(asdict(result), ensure_ascii=False))

    ctx.register_cli_command(
        name='flymes-complete', help='Read one bounded Flymes completion request from stdin',
        setup_fn=lambda parser: None, handler_fn=complete,
    )
