"""Summarize explicit recorded runs; never infers success from an action label."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flymes.export import export_replay
from flymes.runner import atomic_json
from flymes.paths import state_root

ids = sys.argv[1:]
if not ids:
    raise SystemExit("Pass run IDs to summarize, keeping comparison budgets matched.")
rows = []
for run_id in ids:
    if len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
        raise SystemExit("Invalid run ID")
    source = state_root()/'.flymes/runs'/run_id/'replay.json'
    run = json.loads(source.read_text())
    results = [row['result'] for row in run['history']]
    events = [json.loads(line) for line in (source.parent/'events.jsonl').read_text().splitlines()]
    rows.append({
        'run_id': run_id, 'mode': run['mode'], 'status': run['status'],
        'actions': [row['selected_action'] for row in run['history']],
        'steps': run['step'], 'budget': run['limits'], 'model': run['model'],
        'passed': run['observation']['tests_passed'], 'failed': run['observation']['tests_failed'],
        'independently_completed': run['status'] == 'completed' and run['observation']['verified'],
        'model_calls': sum(result.get('model_calls',0) for result in results),
        'reported_tokens': sum(result.get('usage',{}).get('total_tokens',0) for result in results),
        'worker_seconds': sum(result.get('duration_s',0) for result in results),
        'wall_seconds': run['wall_time'],
        'safety_overrides': [event.get('reason') for event in events if event['kind']=='safety_override'] + [result['status'] for result in results if result.get('safety_override')],
    })
    export_replay(source, state_root()/'artifacts'/f"replay-{run['mode'].lower()}.json")
report = {'kind':'exploratory closed-loop comparisons, one run per mode; not a statistical evaluation',
          'seed':7, 'fixture':'case-insensitive shopping-list filter', 'lesioned_percent':30,
          'runs':rows}
atomic_json(state_root()/'artifacts/closed-loop-results.json',report)
print(json.dumps(report,indent=2))
