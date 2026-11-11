import csv
import pytest
from its.controller import Observation
from its.pedestrians import PedestrianController, generate, WALK_SECONDS, CLEAR_SECONDS
from its.runner import run


def tick(c,t,waiting=0,occupied=0,vehicles=0,queues=(8,0,8,0)):
    c.observe(Observation(t,queues),t)
    c.pedestrians(t,waiting,occupied,vehicles)
    return c.update(t)


def test_call_latched_and_vehicle_clearance_interlock():
    c=PedestrianController()
    for t in range(60):
        tick(c,t,waiting=int(t==1),vehicles=int(t>=50))
    assert c.stage=='red' and c.request_since==1
    tick(c,60)
    assert c.stage=='walk' and c.state()=='rrrr'
    assert c.snapshot(60)['ped_signal']=='G'


def test_walk_and_clearance_cannot_be_truncated_by_new_calls():
    c=PedestrianController()
    start=None
    for t in range(200):
        tick(c,t,waiting=1,occupied=int(start is not None and t>=start+WALK_SECONDS),queues=(0,0,0,0))
        if c.stage=='walk' and start is None:start=t
        if start is not None and t>=start+WALK_SECONDS:
            assert c.stage=='ped_clear' and c.state()=='rrrr'
    assert c.since==start+WALK_SECONDS
    tick(c,200,waiting=1,occupied=0)
    assert c.stage=='green' and c.axis==1


def test_empty_fixed_reserves_ped_phase_but_adaptive_skips_it():
    stages={}
    for mode in ('fijo','adaptativo'):
        c=PedestrianController(mode)
        stages[mode]=[]
        for t in range(200):
            tick(c,t)
            stages[mode].append(c.stage)
    assert 'walk' in stages['fijo'] and 'walk' not in stages['adaptativo']
    assert stages['fijo'][70:70+WALK_SECONDS]==['walk']*WALK_SECONDS
    assert stages['fijo'][80:80+CLEAR_SECONDS]==['ped_clear']*CLEAR_SECONDS


def test_independent_pedestrian_generation_and_slow_profile():
    normal=generate('frecuente',101,1800)
    slow=generate('lento',101,1800)
    assert [(p['arm'],p['scheduled']) for p in normal]==[(p['arm'],p['scheduled']) for p in slow]
    assert all(p['speed']==.8 for p in slow)
    assert generate('sin',101,1800)==[]


@pytest.mark.parametrize('mode',['fijo','adaptativo'])
@pytest.mark.parametrize('profile',['frecuente','lento'])
@pytest.mark.integration
def test_real_pedestrian_crossings_complete_and_never_conflict(tmp_path,mode,profile):
    result=run('medio',mode,101,tmp_path,horizon=180,warmup=30,max_drain=600,pedestrian_profile=profile)
    assert result['completed'] and result['ped_generated']>0
    assert result['ped_generated']==result['ped_arrived']==result['ped_crossed']
    assert result['ped_conflicts']==result['collisions']==result['teleports']==0
    rows=list(csv.DictReader((tmp_path/'serie.csv').open()))
    assert any(r['ped_signal']=='G' for r in rows)
    for r in rows:
        if r['ped_signal']=='G':
            assert r['state']=='rrrr' and int(r['vehicles_crossing'])==0
        if int(r['ped_crossing']):
            assert r['state']=='rrrr'


@pytest.mark.integration
def test_pedestrians_survive_vehicle_sample_outage(tmp_path):
    result=run('medio','adaptativo',102,tmp_path,horizon=120,warmup=20,max_drain=600,
               pedestrian_profile='lento',blackout=(40,70))
    assert result['completed'] and result['fallback_seconds']==25
    assert result['ped_conflicts']==0
