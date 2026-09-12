"""Opt-in real-data + real-provider smoke test. Never substitutes mock responses."""
import asyncio
import os
from pathlib import Path

import pytest


@pytest.mark.live
@pytest.mark.full
@pytest.mark.skipif(os.environ.get("FLYMES_LIVE_TEST") != "1", reason="Set FLYMES_LIVE_TEST=1 to spend configured Hermes model usage")
def test_real_controller_dispatch():
    from flymes.runner import Runner
    root = Path(__file__).parents[1]
    async def run():
        engine = Runner(root, root/"data/malecns-v1/prepared-full", max_steps=18)
        await engine.start()
        await engine.control("step")
        await engine.task
        assert engine.history, engine.state["error"]
        record = engine.history[0]
        assert record["result"]["action"] == record["decision"]["action"]
        assert record["result"]["status"] == "ok", record["result"]
        assert record["result"]["model_calls"] > 0
        assert record["decision"]["dataset"]["mode"] == "FULL RETAINED"
        await engine.stop()
    asyncio.run(run())
