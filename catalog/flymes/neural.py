"""Fixed sparse recurrent rate dynamics and explicit engineered task interface."""
from __future__ import annotations
import hashlib
import json
import time
import numpy as np
from scipy import sparse
from .data import Connectome

ACTIONS = ('SEARCH', 'INSPECT', 'IMPLEMENT', 'TEST', 'REVIEW', 'FINISH')
MODES = ('REAL', 'SHUFFLED', 'SILENCED', 'HEURISTIC', 'LESIONED')
FEATURES = ('tests_passed', 'tests_failed', 'last_exit_code', 'repeated_actions', 'changed_files', 'diff_lines', 'elapsed_steps', 'verified', 'remaining_budget')
SCALES = (10, 10, 1, 5, 10, 200, 20, 1, 20)

def encode(observation: dict) -> dict:
    values, missing = [], []
    for key, scale in zip(FEATURES, SCALES):
        value = observation.get(key)
        if value is None:
            values.append(0.0); missing.append(1.0)
        elif not isinstance(value, (int, float, bool)) or not np.isfinite(value):
            raise ValueError('Observation must be finite numbers or null: ' + key)
        else:
            values.append(float(np.clip(abs(value) / scale, 0, 1))); missing.append(0.0)
    return {'names': list(FEATURES), 'values': values, 'missing': missing, 'scales': list(SCALES), 'version': 1}

class Simulator:
    def __init__(self, graph: Connectome, seed: int = 7):
        self.graph, self.seed = graph, int(seed)
        n = len(graph.ids)
        if n < len(ACTIONS):
            raise ValueError('Need at least six neurons for disjoint action pools')
        rng = np.random.default_rng(seed)
        self.state = np.zeros(n, np.float32)
        self.lesioned = np.zeros(n, bool)
        self.steps = 0
        # Normalize total incoming absolute count: conservative contraction bound.
        norm = np.maximum(np.asarray(graph.matrix.sum(axis=1)).ravel(), 1)
        nts = graph.annotations.get('neurotransmitter', ['unknown'] * n)
        signs = np.array([-1.0 if str(x).lower() in ('gaba', 'glutamate', 'histamine') else 1.0 for x in nts], np.float32)
        self.weights = sparse.diags((1 / norm).astype(np.float32)) @ graph.matrix @ sparse.diags(signs)
        self.weights = self.weights.tocsr()
        self._shuffled = None
        # Rewire source stubs, preserving in/out edge multiplicity degrees and row weights.
        self.shuffle_seed = seed + 1009
        self.input_channel = rng.integers(0, len(FEATURES)*2, n)
        self.input_gain = rng.uniform(.6, 1.0, n).astype(np.float32)
        self.output_pool = rng.permutation(n) % len(ACTIONS)
        self.pool_sizes = np.bincount(self.output_pool, minlength=len(ACTIONS))
        self.sample_indices = np.linspace(0, n-1, min(n, 320), dtype=int)
        sample_graph = graph.matrix[self.sample_indices, :][:, self.sample_indices].tocoo()
        self.sample_edges = [[int(pre), int(post)] for post, pre in zip(sample_graph.row[:1200], sample_graph.col[:1200])]
        self.fingerprint = hashlib.sha256(graph.ids.tobytes() + graph.matrix.indptr.tobytes() + graph.matrix.indices.tobytes() + graph.matrix.data.tobytes() + json.dumps(graph.annotations, sort_keys=True).encode()).hexdigest()

    def checkpoint(self):
        return {'version': 1, 'graph': self.fingerprint, 'seed': self.seed, 'steps': self.steps,
                'state': self.state.tolist(), 'lesioned': np.flatnonzero(self.lesioned).tolist()}

    def restore(self, checkpoint):
        if checkpoint.get('version') != 1 or checkpoint.get('graph') != self.fingerprint or checkpoint.get('seed') != self.seed:
            raise ValueError('Checkpoint model or graph mismatch')
        state = np.asarray(checkpoint['state'], dtype=np.float32)
        lesion = np.asarray(checkpoint['lesioned'], dtype=int)
        if state.shape != self.state.shape or np.any(~np.isfinite(state)) or np.any((state < 0) | (state > 1)):
            raise ValueError('Invalid checkpoint state')
        if np.any(lesion < 0) or np.any(lesion >= len(state)) or int(checkpoint['steps']) < 0:
            raise ValueError('Invalid checkpoint indices/time')
        self.state[:] = state
        self.steps = int(checkpoint['steps'])
        self.lesioned[:] = False
        self.lesioned[lesion] = True

    def lesion(self, percent: float, population=None, seed=7):
        if not np.isfinite(percent) or not 0 <= percent <= 100:
            raise ValueError('Lesion percent must be 0..100')
        candidates = np.arange(len(self.state))
        if population:
            types = np.asarray(self.graph.annotations.get('type', [''] * len(self.state)))
            classes = np.asarray(self.graph.annotations.get('superclass', [''] * len(self.state)))
            candidates = candidates[(types == population) | (classes == population)]
            if not len(candidates):
                raise ValueError('Unknown annotated population')
        self.lesioned[:] = False
        selected = np.random.default_rng(seed).choice(candidates, round(len(candidates)*percent/100), replace=False)
        self.lesioned[selected] = True
        return {'silenced': len(selected), 'eligible': len(candidates), 'percent': percent, 'population': population, 'seed': seed, 'application': 'on next LESIONED decision; REAL ignores lesion mask'}

    def clear_lesions(self):
        self.lesioned[:] = False

    def advance(self, drive, mode='REAL', ticks=20):
        if mode not in MODES:
            raise ValueError('Unknown mode')
        if mode == 'SHUFFLED' and self._shuffled is None:
            indices = self.weights.indices.copy()
            np.random.default_rng(self.shuffle_seed).shuffle(indices)
            self._shuffled = sparse.csr_matrix((self.weights.data.copy(), indices, self.weights.indptr.copy()), shape=self.weights.shape)
        weights = self._shuffled if mode == 'SHUFFLED' else self.weights
        mask = self.lesioned if mode == 'LESIONED' else np.zeros(len(self.state), bool)
        self.state[mask] = 0
        for _ in range(ticks):
            recurrent = 0 if mode in ('SILENCED', 'HEURISTIC') else weights @ self.state
            target = np.clip(drive + .8 * recurrent, 0, 1)
            self.state += np.float32(.25) * (target - self.state)
            self.state[mask] = 0
        self.steps += ticks
        if not np.all(np.isfinite(self.state)):
            raise FloatingPointError('Nonfinite neural state')

    def decide(self, observation, valid_actions, mode='REAL'):
        started = time.perf_counter()
        valid = list(valid_actions)
        if not valid or len(set(valid)) != len(valid) or any(a not in ACTIONS for a in valid):
            raise ValueError('Nonempty unique valid action list required')
        encoded = encode(observation)
        channels = np.asarray(encoded['values'] + encoded['missing'], np.float32)
        drive = .45 * channels[self.input_channel] * self.input_gain
        before = hashlib.sha256(self.state.tobytes()).hexdigest()
        self.advance(drive, mode)
        readout = np.bincount(self.output_pool, weights=self.state, minlength=len(ACTIONS)) / self.pool_sizes
        scores = dict(zip(ACTIONS, map(float, readout)))
        if mode == 'HEURISTIC':
            # Conventional control, visible and explicitly separate from neural modes.
            scores = dict.fromkeys(ACTIONS, 0.0)
            chosen = ('FINISH' if observation.get('verified') else 'TEST' if observation.get('changed_files', 0) else 'IMPLEMENT' if observation.get('tests_failed', 0) and observation.get('elapsed_steps', 0) > 0 else 'INSPECT' if observation.get('tests_failed', 0) else 'SEARCH')
            scores[chosen] = 1.0
        action = max((a for a in ACTIONS if a in valid), key=lambda a: scores[a])
        active = float(np.mean(self.state > .01))
        saturated = float(np.mean(self.state > .99))
        sample = [{'id': str(self.graph.ids[i]), 'activity': float(self.state[i]), 'silenced': bool(self.lesioned[i] and mode == 'LESIONED')} for i in self.sample_indices]
        return {'action': action, 'mode': mode, 'scores': scores, 'readout': dict(zip(ACTIONS, map(float, readout))),
            'valid_actions': valid, 'valid_action_mask': {a: a in valid for a in ACTIONS}, 'meaningful_choice': len(valid) > 1,
            'observation': observation, 'encoder': encoded, 'seed': self.seed, 'graph': self.fingerprint,
            'checkpoint_before_hash': before, 'state_hash': hashlib.sha256(self.state.tobytes()).hexdigest(),
            'simulated_ms': self.steps * 5, 'decision_ms': (time.perf_counter()-started)*1000,
            'activity': {'mean': float(self.state.mean()), 'max': float(self.state.max()), 'active_fraction': active, 'saturated_fraction': saturated},
            'health': 'silent' if active == 0 else 'saturated' if saturated > .95 else 'ok',
            'sample': sample, 'sample_edges': self.sample_edges, 'sample_layout': 'schematic; evenly sampled retained neuron indices',
            'dataset': self.graph.metadata}
