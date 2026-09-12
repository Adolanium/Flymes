import numpy as np
import pytest
from scipy import sparse
from flymes.data import Connectome,index_edges

def test_filters_unknown_preserving_direction_and_weak_edges():
    pre,post,count,keep=index_edges(np.array([1,3,8]),np.array([1,3,9,8]),np.array([3,8,1,8]),np.array([1,5,3,2]))
    assert pre.tolist()==[0,1,2]
    assert post.tolist()==[1,2,2]
    assert count.tolist()==[1,5,2]
    assert keep.tolist()==[True,True,False,True]

@pytest.mark.parametrize('counts',[[0],[float('nan')],[1.5]])
def test_bad_count_rejected(counts):
    with pytest.raises(ValueError): index_edges(np.array([1]),np.array([1]),np.array([1]),counts)

def test_float_id_rejected():
    with pytest.raises(ValueError): index_edges(np.array([1]),np.array([1.]),np.array([1]),[1])

def test_counts_computed_not_promotional():
    graph=Connectome(sparse.csr_matrix([[0,2],[3,0]]),np.array([1,2]),{}, {'neurons':100000})
    assert graph.metadata['neurons']==2
    assert graph.metadata['connections']==2
    assert graph.metadata['synapses']==5

def test_resumable_download_checks_source_and_cache(tmp_path,monkeypatch):
    import base64,hashlib
    from flymes.data import download
    payload=b'real bytes for transport fixture'
    path=tmp_path/'neurons.feather'
    part=path.with_suffix('.feather.partial');part.write_bytes(payload[:5])
    part.with_suffix('.partial.etag').write_text('version1')
    class Response:
        status_code=206
        headers={'Content-Length':str(len(payload)),'ETag':'version1','x-goog-hash':'md5='+base64.b64encode(hashlib.md5(payload).digest()).decode(),'Content-Range':f'bytes 5-{len(payload)-1}/{len(payload)}'}
        def raise_for_status(self): pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,*args):yield payload[5:]
    monkeypatch.setattr('flymes.data.requests.head',lambda *a,**k:Response())
    def get(*args,**kwargs):
        assert kwargs['headers']['Range']=='bytes=5-'
        return Response()
    monkeypatch.setattr('flymes.data.requests.get',get)
    record=download('https://example.test/file',path)
    assert path.read_bytes()==payload
    assert record['sha256']==hashlib.sha256(payload).hexdigest()
    assert download('https://example.test/file',path)==record
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='failed validation'):download('https://example.test/file',path)
