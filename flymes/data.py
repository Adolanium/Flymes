"""Versioned MaleCNS data preparation. No synthetic live fallback."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import requests
from scipy import sparse

BASE = 'https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/'
FILES = {
    'annotations': 'body-annotations-male-cns-v1.0-minconf-0.5.feather',
    'neurotransmitters': 'body-neurotransmitters-male-cns-v1.0.feather',
    'weights': 'connectome-weights-male-cns-v1.0-minconf-0.5.feather',
}

def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def download(url: str, path: Path) -> dict:
    """Resume immutable GCS objects using Range and ETag; validate source MD5."""
    path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = path.with_suffix(path.suffix + '.source.json')
    head = requests.head(url, timeout=60)
    head.raise_for_status()
    size = int(head.headers['Content-Length'])
    etag = head.headers.get('ETag')
    hashes = dict(x.strip().split('=', 1) for x in head.headers.get('x-goog-hash', '').split(',') if '=' in x)
    if path.exists() and meta_path.exists():
        old = json.loads(meta_path.read_text())
        if old.get('etag') != etag:
            raise ValueError('Immutable source changed; use a fresh cache: ' + url)
        if path.stat().st_size == size and digest(path) == old['sha256']:
            return old
        raise ValueError('Cached source failed validation: ' + str(path))
    part = path.with_suffix(path.suffix + '.partial')
    marker = part.with_suffix(part.suffix + '.etag')
    if part.exists() and (not marker.exists() or marker.read_text() != (etag or '')):
        part.unlink()
    marker.write_text(etag or '')
    offset = part.stat().st_size if part.exists() else 0
    if offset > size:
        raise ValueError('Partial download exceeds source length')
    if offset < size:
        headers = {'Range': f'bytes={offset}-', 'If-Range': etag} if offset and etag else {}
        with requests.get(url, headers=headers, stream=True, timeout=(30, 120)) as response:
            response.raise_for_status()
            append = offset > 0 and response.status_code == 206
            if append and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise ValueError('Server returned an invalid resume range')
            with part.open('ab' if append else 'wb') as f:
                for chunk in response.iter_content(8 * 1024 * 1024):
                    f.write(chunk)
    if part.stat().st_size != size:
        raise ValueError('Incomplete download; rerun to resume')
    if hashes.get('md5'):
        with part.open('rb') as f:
            md5 = base64.b64encode(hashlib.file_digest(f, 'md5').digest()).decode()
        if md5 != hashes['md5']:
            part.unlink()
            raise ValueError('Source MD5 mismatch; corrupted partial removed')
    part.replace(path)
    record = {'url': url, 'bytes': size, 'etag': etag, 'source_hashes': hashes, 'sha256': digest(path)}
    meta_path.write_text(json.dumps(record, indent=2))
    return record


def index_edges(ids, pre, post, weights):
    ids = np.asarray(ids)
    pre, post, weights = np.asarray(pre), np.asarray(post), np.asarray(weights)
    if not len(ids) or np.any(ids[1:] <= ids[:-1]):
        raise ValueError('IDs must be sorted and unique')
    if ids.dtype.kind not in 'iu' or pre.dtype.kind not in 'iu' or post.dtype.kind not in 'iu':
        raise ValueError('IDs must be exact integers')
    if len(pre) != len(post) or len(pre) != len(weights):
        raise ValueError('Edge column length mismatch')
    if np.any(~np.isfinite(weights)) or np.any(weights < 1) or np.any(weights != np.floor(weights)):
        raise ValueError('Invalid synaptic contact counts')
    i, j = np.searchsorted(ids, pre), np.searchsorted(ids, post)
    keep = (i < len(ids)) & (j < len(ids))
    keep &= ids[np.minimum(i, len(ids)-1)] == pre
    keep &= ids[np.minimum(j, len(ids)-1)] == post
    return i[keep].astype(np.int32), j[keep].astype(np.int32), weights[keep].astype(np.float32), keep

@dataclass
class Connectome:
    matrix: sparse.csr_matrix
    ids: np.ndarray
    annotations: dict
    metadata: dict

    def __post_init__(self):
        self.ids = np.asarray(self.ids)
        if self.ids.dtype.kind not in 'iu' or np.any(self.ids < 0):
            raise ValueError('Neuron IDs must be nonnegative exact integers')
        if any(len(value) != len(self.ids) for value in self.annotations.values()):
            raise ValueError('Annotation lengths do not match neurons')
        self.matrix = sparse.csr_matrix(self.matrix, dtype=np.float32)
        if self.matrix.shape != (len(self.ids), len(self.ids)) or not len(self.ids):
            raise ValueError('Graph size does not match neuron IDs')
        if len(np.unique(self.ids)) != len(self.ids):
            raise ValueError('Duplicate neuron IDs')
        if not np.all(np.isfinite(self.matrix.data)) or np.any(self.matrix.data <= 0):
            raise ValueError('Connection counts must be finite and positive')
        self.metadata = dict(self.metadata, neurons=len(self.ids), connections=self.matrix.nnz,
                             synapses=int(self.matrix.sum(dtype=np.float64)))

    @classmethod
    def load(cls, path):
        path = Path(path)
        meta = json.loads((path / 'metadata.json').read_text())
        for name, expected in meta.get('prepared_hashes', {}).items():
            if digest(path / name) != expected:
                raise ValueError('Prepared data hash mismatch: ' + name)
        return cls(sparse.load_npz(path / 'connections.npz'), np.load(path / 'ids.npy', allow_pickle=False),
                   json.loads((path / 'annotations.json').read_text()), meta)


def prepare_data(cache, max_neurons=None) -> Path:
    import pyarrow as pa
    import pyarrow.feather as feather
    import pyarrow.ipc as ipc
    cache = Path(cache)
    if max_neurons is not None and max_neurons < 6:
        raise ValueError('Development subset requires at least six neurons')
    provenance = {key: download(BASE + filename, cache / filename) for key, filename in FILES.items()}
    table = feather.read_table(cache / FILES['annotations'])
    columns = table.to_pydict()
    required = {'bodyId', 'superclass', 'status', 'type'}
    if not required.issubset(columns):
        raise ValueError('Unexpected MaleCNS annotation schema')
    all_ids = np.asarray(columns['bodyId'], dtype=np.uint64)
    if len(np.unique(all_ids)) != len(all_ids):
        raise ValueError('Duplicate annotation body IDs')
    retained = [i for i, value in enumerate(columns['superclass']) if value and columns['status'][i] != 'Glia']
    retained.sort(key=lambda i: int(all_ids[i]))
    full_count = len(retained)
    if max_neurons:
        retained = retained[:max_neurons]
    ids = all_ids[retained]
    nt = feather.read_table(cache / FILES['neurotransmitters'], columns=['body', 'consensus_nt']).to_pydict()
    nt_map = dict(zip(nt['body'], nt['consensus_nt']))
    annotations = {key: [columns[key][i] or '' for i in retained] for key in ['superclass', 'type']}
    annotations['neurotransmitter'] = [nt_map.get(int(i)) or 'unknown' for i in ids]
    rows, cols, vals = [], [], []
    source_rows = source_synapses = retained_synapses = 0
    with pa.memory_map(str(cache / FILES['weights']), 'r') as source:
        reader = ipc.open_file(source)
        for batch_number in range(reader.num_record_batches):
            batch = reader.get_batch(batch_number)
            arrays = [batch.column(batch.schema.get_field_index(name)).to_numpy(zero_copy_only=False) for name in ['body_pre', 'body_post', 'weight']]
            i, j, count, keep = index_edges(ids, *arrays)
            cols.append(i); rows.append(j); vals.append(count)
            source_rows += len(keep)
            source_synapses += int(arrays[2].sum(dtype=np.uint64))
            retained_synapses += int(count.sum(dtype=np.float64))
    graph = sparse.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ids), len(ids))).tocsr()
    graph.sum_duplicates()
    output = cache / ('prepared-full' if max_neurons is None else f'prepared-subset-{max_neurons}')
    output.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(output / 'connections.npz', graph)
    np.save(output / 'ids.npy', ids)
    (output / 'annotations.json').write_text(json.dumps(annotations))
    meta = {'dataset': 'male-cns:v1.0', 'mode': 'FULL RETAINED' if max_neurons is None else 'DEVELOPMENT SUBSET',
        'neurons': len(ids), 'connections': graph.nnz, 'synapses': retained_synapses,
        'source_annotation_rows': len(all_ids), 'full_retained_neurons': full_count,
        'excluded_annotation_rows': len(all_ids)-len(ids), 'source_connection_rows': source_rows,
        'excluded_connection_rows': source_rows-sum(map(len, vals)), 'source_synapses': source_synapses,
        'excluded_synapses': source_synapses-retained_synapses,
        'missing_type': sum(not x for x in annotations['type']),
        'missing_neurotransmitter': annotations['neurotransmitter'].count('unknown'),
        'filter': 'Nonempty superclass; exclude status Glia; retain all edges between retained IDs including self and weight-one edges. Subset selects lowest body IDs.',
        'license': 'CC-BY-4.0', 'credit': 'MaleCNS: FlyEM / HHMI Janelia, Cambridge, MRC LMB, Google Research',
        'source': provenance, 'prepared_hashes': {name: digest(output/name) for name in ['connections.npz','ids.npy','annotations.json']}}
    (output / 'metadata.json').write_text(json.dumps(meta, indent=2))
    return output
