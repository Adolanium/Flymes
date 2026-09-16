import asyncio
from collections import deque
import json
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import sparse

from flymes.arena import ACTIONS, Arena, Circuit, World, baseline
from flymes.data import Connectome
from flymes.server import ArenaCommand, create_app


def graph():
    return Connectome(sparse.eye(24, format='csr'), np.arange(24), {},
                      {'mode': 'TEST FIXTURE', 'neurons': 24})


def test_seeded_maps_are_connected_and_repeatable():
    for seed in range(20):
        world = World(seed)
        assert world.geometry() == World(seed).geometry()
        queue, seen = deque([(5, 5)]), {(5, 5)}
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                pos = (x + dx, y + dy)
                if pos not in world.walls and pos not in seen:
                    seen.add(pos)
                    queue.append(pos)
        assert all(food in seen for food in world.food)
        assert len(set(world.food)) == 7
        assert world.observation() == World(seed).observation()


def test_food_cannot_be_collected_twice_and_energy_ends_run():
    world = World(7)
    world.x, world.y = world.food[0]
    world.energy = 10
    world.advance('EAT')
    assert world.energy == 21 and len(world.eaten) == 1
    assert 'EAT' not in world.valid_actions()
    world.advance('EAT')
    assert world.energy == 20 and len(world.eaten) == 1
    while not world.finished:
        world.advance('WAIT')
    assert world.energy == 0
    with pytest.raises(ValueError, match='finished'):
        world.advance('WAIT')


def test_policies_use_the_same_mask_and_seed():
    world = World(7)
    first, second = np.random.default_rng(20), np.random.default_rng(20)
    for mode in ('RANDOM', 'GREEDY'):
        for _ in range(10):
            action, _ = baseline(world.observation(), world.valid_actions(), mode, first)
            repeated, _ = baseline(world.observation(), world.valid_actions(), mode, second)
            assert action == repeated and action in world.valid_actions()
    circuit = Circuit(graph())
    circuit.reset(100)
    action, scores = circuit.choose(world.observation(), world.valid_actions(), 'LESIONED')
    assert action in world.valid_actions()
    assert all(value == 0 for value in scores.values())


def test_comparison_pairs_worlds_resets_state_and_persists_evidence(tmp_path):
    async def run():
        arena = Arena(tmp_path / 'data', tmp_path / 'records', graph_factory=graph)
        args = ArenaCommand(command='compare', modes=['REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'GREEDY', 'RANDOM'], seeds=2, max_steps=10)
        await arena.control(args)
        await arena.task
        assert arena.state['status'] == 'completed'
        rows = arena.report['rows']
        assert len(rows) == 12
        for seed in (7, 8):
            assert len({r['world_sha256'] for r in rows if r['seed'] == seed}) == 1
        first = [{k: v for k, v in row.items() if k != 'wall_seconds'} for row in rows]
        await arena.control(args)
        await arena.task
        second = [{k: v for k, v in row.items() if k != 'wall_seconds'} for row in arena.report['rows']]
        assert first == second
        record = json.loads((tmp_path / 'records' / arena.state['run_id'] / '7-REAL.json').read_text())
        assert len(record['frames']) == 11
        assert set(record['frames'][1]['sensors']) == set(arena.report['protocol']['sensors'])
        assert record['frames'][1]['action'] in record['frames'][1]['valid_actions']
        assert arena.report['graph_sha256']
    asyncio.run(run())


def test_missing_graph_never_substitutes_a_neural_run(tmp_path):
    async def run():
        arena = Arena(tmp_path, tmp_path / 'records')
        with pytest.raises(ValueError, match='Prepare'):
            await arena.control(ArenaCommand(command='run', mode='REAL'))
        assert arena.task is None
        await arena.control(ArenaCommand(command='compare', seeds=1, max_steps=10))
        await arena.task
        assert arena.state['status'] == 'completed'
        assert arena.report['graph_sha256'] is None
    asyncio.run(run())


def test_pause_stop_and_disconnect_do_not_fake_completion(tmp_path):
    async def run():
        arena = Arena(tmp_path, tmp_path / 'records')
        await arena.control(ArenaCommand(command='run'))
        await asyncio.sleep(.03)
        await arena.control(ArenaCommand(command='pause'))
        step = arena.state['frame']['step']
        await asyncio.sleep(.25)
        assert arena.state['frame']['step'] == step
        with pytest.raises(ValueError, match='Stop'):
            await arena.control(ArenaCommand(command='run'))
        await arena.control(ArenaCommand(command='stop'))
        await arena.task
        assert arena.state['status'] == 'stopped'
        assert arena.report['rows'][0]['outcome'] == 'stopped'
        await arena.control(ArenaCommand(command='run'))
        arena.lease = time.monotonic() - 31
        await arena.task
        assert arena.state['status'] == 'stopped'
        assert arena.report['rows'][0]['steps'] == 0
    asyncio.run(run())


def test_arena_api_auth_validation_export_and_session_exclusion(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'home'))
    app = create_app(tmp_path, tmp_path / 'missing', 'x' * 48, state_root=tmp_path / 'state')
    headers = {'Authorization': 'Bearer ' + 'x' * 48}
    with TestClient(app) as client:
        assert client.get('/arena/state').status_code == 401
        assert client.get('/arena/state', headers={**headers, 'Origin': 'https://example.com'}).status_code == 403
        assert client.post('/arena', headers=headers, json={'command': 'compare', 'seeds': 1000}).status_code == 422
        assert client.post('/arena', headers=headers, json={'command': 'run', 'seed': True}).status_code == 422
        assert client.post('/arena', headers=headers, json={'command': 'run', 'mode': 'REAL'}).status_code == 409
        app.state.native.status = 'active'
        assert client.post('/arena', headers=headers, json={'command': 'run'}).status_code == 409
        app.state.native.status = 'disabled'
        assert client.post('/arena', headers=headers, json={'command': 'compare', 'seeds': 1, 'max_steps': 10}).status_code == 200
        for _ in range(100):
            state = client.get('/arena/state', headers=headers).json()
            if state['status'] == 'completed':
                break
            time.sleep(.01)
        assert state['status'] == 'completed'
        report = client.get('/arena/report', headers=headers).json()
        assert len(report['rows']) == 2
        replay = client.get('/arena/replay/7/GREEDY', headers=headers).json()
        assert replay['kind'] == 'arena-replay'
        assert replay['frames'][-1]['step'] == 10
        assert 'sensors' not in replay['frames'][-1]
        assert client.get('/arena/replay/999/GREEDY', headers=headers).status_code == 404
        assert (tmp_path / 'state/.flymes/arena' / state['run_id'] / 'report.json').is_file()
