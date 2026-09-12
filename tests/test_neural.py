import numpy as np
import pytest
from scipy import sparse
from flymes.data import Connectome
from flymes.neural import Simulator, encode, ACTIONS

def graph():
    return Connectome(sparse.csr_matrix(([3., 2., 1., 4., 2., 1.], ([1,2,3,4,5,0],[0,1,2,3,4,5])), shape=(6,6)), np.arange(1,7), {}, {'mode':'TEST FIXTURE'})

def test_orientation_and_update():
    sim=Simulator(graph()); sim.state[0]=1
    sim.advance(np.zeros(6),ticks=1)
    assert sim.state[1] == pytest.approx(.2)
    assert sim.state[0] == pytest.approx(.75)
    assert sim.state[2] == 0

def test_checkpoint_exact_replay_and_mask():
    sim=Simulator(graph()); cp=sim.checkpoint()
    first=sim.decide({'tests_failed':2},['TEST','INSPECT'])
    sim.restore(cp)
    second=sim.decide({'tests_failed':2},['TEST','INSPECT'])
    assert first['scores']==second['scores']
    assert first['state_hash']==second['state_hash']
    assert first['action'] in ['TEST','INSPECT']
    assert sim.decide({},['REVIEW'])['action']=='REVIEW'
    with pytest.raises(ValueError): sim.decide({},[])

def test_missing_and_bounds():
    result=encode({'tests_failed':1000,'verified':None,'last_exit_code':-2})
    assert result['values'][1]==1
    assert result['values'][2]==1
    assert result['missing'][7]==1
    with pytest.raises(ValueError): encode({'diff_lines':float('nan')})

def test_lesion_changes_actual_decision_path():
    sim=Simulator(graph()); cp=sim.checkpoint()
    real=sim.decide({'tests_failed':4},list(ACTIONS))
    sim.restore(cp); sim.lesion(100)
    lesion=sim.decide({'tests_failed':4},list(ACTIONS),'LESIONED')
    assert lesion['activity']['mean']==0
    assert lesion['scores'] != real['scores']
    assert lesion['action']==ACTIONS[0]
    # Decoder is unchanged; no forced changed-action logic.
    assert lesion['health']=='silent'

def test_shuffle_preserves_stub_degrees_and_weight_multiset():
    sim=Simulator(graph()); sim.advance(np.zeros(6),'SHUFFLED',1)
    w,s=sim.weights,sim._shuffled
    assert np.array_equal(np.sort(w.data),np.sort(s.data))
    assert np.array_equal(np.sort(np.diff(w.indptr)),np.sort(np.diff(s.indptr)))
    assert np.array_equal(np.bincount(w.indices, minlength=6),np.bincount(s.indices, minlength=6))
    assert np.array_equal(w.indptr,s.indptr)

def test_silenced_removes_recurrence():
    sim=Simulator(graph()); sim.state[0]=1
    sim.advance(np.zeros(6),'SILENCED',1)
    assert sim.state[1]==0
    assert sim.state[0]==.75

def test_checkpoint_rejects_wrong_graph():
    sim=Simulator(graph()); cp=sim.checkpoint(); cp['graph']='bad'
    with pytest.raises(ValueError): sim.restore(cp)
