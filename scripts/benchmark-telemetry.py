"""Measure real local snapshot transport without dispatching work."""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flymes.cli import rpc
from flymes.runner import atomic_json

latencies = []
for _ in range(10):
    start = time.perf_counter()
    state = rpc('state')
    latencies.append((time.perf_counter()-start)*1000)
size = len(json.dumps(state, separators=(',', ':')).encode())
report = {'requests':10, 'status':state['status'], 'step':state['step'],
          'snapshot_bytes_compact_json':size, 'polling_interval_seconds':1,
          'median_transport_and_decode_ms':statistics.median(latencies),
          'max_transport_and_decode_ms':max(latencies),
          'render_samples':len(state.get('decision',{}).get('sample',[])),
          'note':'Local companion HTTP plus JSON decode; excludes Hermes proxy and renderer. This polling does not advance neural time.'}
atomic_json(ROOT/'artifacts/telemetry-benchmark.json',report)
print(json.dumps(report,indent=2))
