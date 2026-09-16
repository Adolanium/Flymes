"""Seeded foraging experiments. Policies emit actions; no model or tool calls."""
from __future__ import annotations

import asyncio
from collections import deque
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import uuid

import numpy as np

from .data import Connectome
from .neural import Simulator
from .runner import atomic_json

ACTIONS = ('NORTH', 'EAST', 'SOUTH', 'WEST', 'EAT', 'WAIT')
DELTAS = ((0, -1), (1, 0), (0, 1), (-1, 0))
MODES = ('REAL', 'SHUFFLED', 'SILENCED', 'LESIONED', 'GREEDY', 'RANDOM')
NEURAL = MODES[:4]
SENSORS = ('scent_north', 'scent_east', 'scent_south', 'scent_west',
           'blocked_north', 'blocked_east', 'blocked_south', 'blocked_west',
           'food_here', 'energy')


class World:
    """An 11 by 11 connected map, seven food sites, and a limited energy supply."""

    def __init__(self, seed, max_steps=60):
        self.seed, self.max_steps = seed, max_steps
        self.size, self.x, self.y = 11, 5, 5
        rng = np.random.default_rng(seed)
        self.walls = {(x, y) for x in range(11) for y in range(11)
                      if x in (0, 10) or y in (0, 10)}
        cells = [(x, y) for y in range(1, 10) for x in range(1, 10) if (x, y) != (5, 5)]
        for index in rng.permutation(len(cells))[:16]:
            candidate = cells[int(index)]
            self.walls.add(candidate)
            seen, queue = {(5, 5)}, deque([(5, 5)])
            while queue:
                x, y = queue.popleft()
                for dx, dy in DELTAS:
                    pos = (x + dx, y + dy)
                    if pos not in self.walls and pos not in seen:
                        seen.add(pos)
                        queue.append(pos)
            if len(seen) != 121 - len(self.walls):
                self.walls.remove(candidate)
        available = [pos for pos in cells if pos not in self.walls]
        self.food = [available[int(i)] for i in rng.choice(len(available), 7, replace=False)]
        self.eaten = set()
        self.energy, self.step, self.collisions = 32, 0, 0
        self.visited = {(self.x, self.y)}

    def geometry(self):
        return {'size': self.size, 'walls': sorted(map(list, self.walls)),
                'food': list(map(list, self.food)), 'seed': self.seed}

    def observation(self):
        remaining = [food for i, food in enumerate(self.food) if i not in self.eaten]
        neighbors = [(self.x + dx, self.y + dy) for dx, dy in DELTAS]
        scent = [max((1 / (1 + abs(x - fx) + abs(y - fy)) for fx, fy in remaining), default=0)
                 for x, y in neighbors]
        blocked = [float(pos in self.walls) for pos in neighbors]
        here = float((self.x, self.y) in remaining)
        return dict(zip(SENSORS, scent + blocked + [here, self.energy / 32]))

    def valid_actions(self):
        observation = self.observation()
        valid = [action for i, action in enumerate(ACTIONS[:4]) if not observation[SENSORS[i + 4]]]
        if observation['food_here']:
            valid.append('EAT')
        return valid + ['WAIT']

    @property
    def finished(self):
        return self.step >= self.max_steps or self.energy <= 0 or len(self.eaten) == len(self.food)

    def frame(self, action=None, scores=None):
        return {'step': self.step, 'x': self.x, 'y': self.y, 'energy': self.energy,
                'eaten': sorted(self.eaten), 'visited': len(self.visited),
                'action': action, 'scores': scores or {}, 'collisions': self.collisions}

    def advance(self, action):
        if self.finished:
            raise ValueError('Episode has finished')
        if action not in ACTIONS:
            raise ValueError('Unknown arena action')
        self.energy -= 1
        self.step += 1
        if action in ACTIONS[:4]:
            dx, dy = DELTAS[ACTIONS.index(action)]
            target = (self.x + dx, self.y + dy)
            if target in self.walls:
                self.collisions += 1
            else:
                self.x, self.y = target
                self.visited.add(target)
        elif action == 'EAT':
            for index, pos in enumerate(self.food):
                if pos == (self.x, self.y) and index not in self.eaten:
                    self.eaten.add(index)
                    self.energy = min(32, self.energy + 12)
                    break


class Circuit:
    """Engineered ten-channel input and six-action readout on the existing rate model."""

    def __init__(self, graph, seed=7):
        self.sim = Simulator(graph, seed=seed)
        rng = np.random.default_rng(seed + 4099)
        self.channels = rng.integers(0, len(SENSORS), len(graph.ids))
        self.seed = seed

    def reset(self, lesion_percent):
        self.sim.state.fill(0)
        self.sim.steps = 0
        self.sim.clear_lesions()
        self.sim.lesion(lesion_percent, seed=self.seed)

    def choose(self, observation, valid, mode):
        inputs = np.array([observation[name] for name in SENSORS], dtype=np.float32)
        drive = .45 * inputs[self.channels] * self.sim.input_gain
        self.sim.advance(drive, mode=mode, ticks=4)
        values = np.bincount(self.sim.output_pool, weights=self.sim.state, minlength=6) / self.sim.pool_sizes
        scores = dict(zip(ACTIONS, map(float, values)))
        return max((action for action in ACTIONS if action in valid), key=scores.get), scores


def baseline(observation, valid, mode, rng):
    if mode == 'RANDOM':
        return str(rng.choice(valid)), {}
    if 'EAT' in valid:
        return 'EAT', {}
    moves = [action for action in ACTIONS[:4] if action in valid]
    if not moves:
        return 'WAIT', {}
    scores = {action: observation[SENSORS[ACTIONS.index(action)]] for action in moves}
    best = max(scores.values())
    return str(rng.choice([action for action in moves if scores[action] == best])), scores


class Arena:
    def __init__(self, dataset: Path, output: Path, graph_factory=None):
        self.dataset, self.output = Path(dataset), Path(output)
        self.graph_factory = graph_factory
        self.circuit = None
        self.task = None
        self.lock = asyncio.Lock()
        self.stop_requested = False
        self.paused = False
        self.lease = time.monotonic()
        self.state = {'kind': 'arena', 'status': 'idle', 'frame': None, 'world': None,
                      'rows': [], 'error': None, 'progress': 0, 'total': 0}
        self.report = None
        self.last_replay = None
        self.config = {}

    def snapshot(self):
        ready = self.graph_factory is not None or (self.dataset / 'metadata.json').is_file()
        return {**deepcopy(self.state), 'dataset_available': ready,
                'available_modes': list(MODES if ready else MODES[4:]),
                'has_report': self.report is not None,
                'has_replay': self.last_replay is not None}

    @property
    def running(self):
        return self.task is not None and not self.task.done()

    async def control(self, body):
        command = body.command
        async with self.lock:
            self.lease = time.monotonic()
            if command == 'stop':
                self.stop_requested = True
                self.paused = False
                if self.running:
                    self.state['status'] = 'stopping'
                return self.snapshot()
            if command in ('pause', 'resume'):
                if not self.running or self.state.get('experiment') != 'single':
                    raise ValueError('Pause and resume apply to a running single episode')
                if self.stop_requested:
                    raise ValueError('Experiment is stopping')
                self.paused = command == 'pause'
                self.state['status'] = 'paused' if self.paused else 'running'
                return self.snapshot()
            if self.running:
                raise ValueError('Stop the current experiment before starting another')
            modes = list(body.modes) if command == 'compare' else [body.mode]
            if not modes or len(modes) != len(set(modes)):
                raise ValueError('Choose distinct controllers')
            if any(mode not in self.snapshot()['available_modes'] for mode in modes):
                raise ValueError('Prepare the MaleCNS dataset before choosing a neural controller. Baselines need no dataset.')
            if command == 'compare' and len(modes) < 2:
                raise ValueError('Choose at least two controllers to compare')
            self.config = {'seed': body.seed, 'seeds': body.seeds if command == 'compare' else 1,
                           'max_steps': body.max_steps, 'modes': modes,
                           'circuit_seed': body.circuit_seed, 'lesion_percent': body.lesion_percent}
            self.stop_requested = self.paused = False
            self.last_replay = None
            self.report = None
            self.state = {'kind': 'arena', 'status': 'preparing', 'frame': None, 'world': None,
                          'rows': [], 'error': None, 'progress': 0,
                          'total': len(modes) * self.config['seeds'],
                          'experiment': 'comparison' if command == 'compare' else 'single',
                          'config': deepcopy(self.config)}
            self.task = asyncio.create_task(self._run())
            return self.snapshot()

    def _load_circuit(self):
        if self.circuit is None or self.circuit.seed != self.config['circuit_seed']:
            graph = self.graph_factory() if self.graph_factory else Connectome.load(self.dataset)
            self.circuit = Circuit(graph, self.config['circuit_seed'])

    async def _episode(self, seed, mode):
        world = World(seed, self.config['max_steps'])
        rng = np.random.default_rng(seed + 65537)
        if mode in NEURAL:
            await asyncio.to_thread(self.circuit.reset, self.config['lesion_percent'])
        frames = [world.frame()]
        geometry = world.geometry()
        self.state.update(world=geometry, frame=frames[0], mode=mode, seed=seed, status='running')
        start = time.perf_counter()
        while not world.finished and not self.stop_requested:
            if time.monotonic() - self.lease > 30:
                self.stop_requested = True
                self.state['notice'] = 'Stopped because the panel disconnected.'
                break
            if self.paused:
                await asyncio.sleep(.1)
                continue
            observation, valid = world.observation(), world.valid_actions()
            if mode in NEURAL:
                action, scores = await asyncio.to_thread(self.circuit.choose, observation, valid, mode)
            else:
                action, scores = baseline(observation, valid, mode, rng)
            # Stop/pause arriving during a neural tick must not apply another move.
            if self.stop_requested:
                break
            while self.paused and not self.stop_requested:
                if time.monotonic() - self.lease > 30:
                    self.stop_requested = True
                    break
                await asyncio.sleep(.1)
            if self.stop_requested:
                break
            world.advance(action)
            frame = world.frame(action, scores)
            frame['sensors'] = observation
            frame['valid_actions'] = valid
            frames.append(frame)
            self.state['frame'] = frame
            await asyncio.sleep(.18 if self.state['experiment'] == 'single' else 0)
        outcome = ('stopped' if self.stop_requested else 'all_food' if len(world.eaten) == 7
                   else 'energy_exhausted' if world.energy <= 0 else 'step_limit')
        result = {'seed': seed, 'mode': mode, 'food': len(world.eaten), 'steps': world.step,
                  'energy': world.energy, 'visited': len(world.visited), 'outcome': outcome,
                  'wall_seconds': round(time.perf_counter() - start, 4),
                  'world_sha256': hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest()}
        return result, {'kind': 'arena-replay', 'version': 1, 'world': geometry,
                        'mode': mode, 'config': deepcopy(self.config), 'result': result, 'frames': frames}

    async def _run(self):
        run_id = uuid.uuid4().hex
        self.state['run_id'] = run_id
        episodes = []
        graph_fingerprint = None
        source_fingerprint = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                              for name in ('arena.py', 'neural.py')}
        try:
            if any(mode in NEURAL for mode in self.config['modes']):
                await asyncio.to_thread(self._load_circuit)
                graph_fingerprint = self.circuit.sim.fingerprint
                self.state['dataset'] = {key: self.circuit.sim.graph.metadata.get(key)
                                         for key in ('dataset', 'mode', 'neurons', 'connections')}
            for offset in range(self.config['seeds']):
                for mode in self.config['modes']:
                    if self.stop_requested:
                        break
                    result, replay = await self._episode(self.config['seed'] + offset, mode)
                    episodes.append(replay)
                    self.last_replay = replay
                    self.state['rows'].append(result)
                    self.state['progress'] = len(episodes)
                    # Each completed/partial episode is durable, even if a later one fails.
                    atomic_json(self.output / run_id / f'{result["seed"]}-{mode}.json', replay)
                if self.stop_requested:
                    break
            self.state['status'] = 'stopped' if self.stop_requested else 'completed'
        except asyncio.CancelledError:
            self.state['status'] = 'stopped'
            self.stop_requested = True
            raise
        except Exception as exc:
            self.state.update(status='error', error=str(exc))
        finally:
            self.report = {'kind': 'arena-experiment', 'version': 1, 'run_id': run_id,
                           'status': self.state['status'], 'error': self.state['error'],
                           'config': deepcopy(self.config), 'rows': deepcopy(self.state['rows']),
                           'protocol': {'sensors': list(SENSORS), 'actions': list(ACTIONS),
                                        'numpy_version': np.__version__,
                                        'initial_energy': 32, 'food_energy': 12, 'ticks_per_action': 4,
                                        'mapping': 'Seeded random input channels and action pools; no learning',
                                        'primary_metric': 'food collected out of seven',
                                        'stopped_episodes': 'Incomplete; excluded from summary averages'},
                           'graph_sha256': graph_fingerprint,
                           'dataset': deepcopy(self.state.get('dataset')),
                           'source_sha256': source_fingerprint}
            try:
                atomic_json(self.output / run_id / 'report.json', self.report)
            except OSError as exc:
                self.state.update(status='error', error='Could not save experiment: ' + str(exc))
                self.report.update(status='error', error=self.state['error'])

    async def close(self):
        self.stop_requested = True
        self.paused = False
        if self.running:
            await self.task
