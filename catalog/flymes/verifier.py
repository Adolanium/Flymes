"""Independent checks held outside the editable task directory.

The worker may only edit app.py. Verification executes untrusted task Python in
a child process. This is a bounded local demo, not an OS security sandbox.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import time

CHECK = r'''
import importlib.util, json, sys
s = importlib.util.spec_from_file_location("fixture", sys.argv[1])
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
cases = [(["Apple", "banana", "APRICOT"], "ap", ["Apple", "APRICOT"]),
         (["Apple", "banana"], "BAN", ["banana"]),
         (["Apple", "banana"], "", ["Apple", "banana"]),
         ([], "a", []), (["Pear"], "x", [])]
failed = []
for i, (items, query, expected) in enumerate(cases):
    original = list(items)
    try:
        actual = m.visible_items(items, query)
        assert actual == expected, f"expected {expected!r}, got {actual!r}"
        assert items == original, "input mutated"
    except Exception as e:
        failed.append({"case": i, "error": str(e)})
print(json.dumps({"passed": len(cases)-len(failed), "failed": len(failed), "failures": failed}))
sys.exit(bool(failed))
'''


def verify(workspace: Path, timeout: float = 15) -> dict:
    """Run immutable host checks, ignoring the worker's completion claim."""
    import json
    from flymes.boundary import validate_demo_code, BoundaryError
    start = time.monotonic()
    try:
        validate_demo_code((workspace / "app.py").read_text(encoding="utf-8"))
    except (BoundaryError, OSError) as exc:
        return {"passed": 0, "failed": 1, "verified": False, "exit_code": 1,
                "failures": [{"error": str(exc)}], "boundary_rejected": True}
    try:
        result = subprocess.run([sys.executable, "-I", "-c", CHECK,
                                 str(workspace.resolve() / "app.py")],
                                cwd=workspace, capture_output=True, text=True,
                                timeout=timeout, encoding="utf-8", errors="replace")
        try:
            measured = json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            measured = {"passed": 0, "failed": 1, "failures": [{"error": result.stderr[-2000:]}]}
        return {**measured, "exit_code": result.returncode,
                "verified": result.returncode == 0 and measured.get("failed") == 0,
                "duration_s": time.monotonic()-start,
                "verifier_sha256": hashlib.sha256(CHECK.encode()).hexdigest()}
    except subprocess.TimeoutExpired:
        return {"passed": None, "failed": None, "verified": False,
                "exit_code": None, "timeout": True, "duration_s": time.monotonic()-start}
