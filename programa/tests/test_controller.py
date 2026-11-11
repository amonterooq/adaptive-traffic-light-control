import random
import pytest
from its.config import Timing
from its.controller import Controller, Observation
from its.demand import generate


def test_fixed_cycle_and_interlocks():
    c=Controller('fijo')
    states=[c.update(t) for t in range(141)]
    assert states[:30]==['GrGr']*30
    assert states[30:33]==['yryr']*3
    assert states[33:35]==['rrrr']*2
    assert states[35:65]==['rGrG']*30
    assert states[65:68]==['ryry']*3
    assert states[68:70]==['rrrr']*2
    assert states[70:140]==states[:70]


def test_minimum_and_maximum_green():
    c=Controller()
    for t in range(11):
        c.observe(Observation(t,(0,30,0,30)),t)
        state=c.update(t)
        assert state==('GrGr' if t<10 else 'yryr')
    c=Controller()
    for t in range(51):
        c.observe(Observation(t,(30,0,30,0)),t)
        state=c.update(t)
    assert state=='yryr'


def test_random_queue_invariants():
    c=Controller();rng=random.Random(82);last_stage='green';start=0
    sequence=[]
    for t in range(5000):
        c.observe(Observation(t,tuple(rng.randrange(40) for _ in range(4))),t)
        state=c.update(t)
        assert state in ['GrGr','rGrG','yryr','ryry','rrrr']
        if c.stage!=last_stage:
            duration=t-start
            if last_stage=='green':assert 10<=duration<=50
            if last_stage=='yellow':assert duration==3
            if last_stage=='red':assert duration==2
            sequence.append(c.stage);last_stage=c.stage;start=t
    assert sequence[:6]==['yellow','red','green','yellow','red','green']


def test_stale_fallback_and_recovery():
    c=Controller();c.observe(Observation(0,(10,1,10,1)),0)
    for t in range(31):
        c.update(t)
        assert c.fallback==(t>5)
    assert c.stage=='yellow'
    c.observe(Observation(31,(0,5,0,5)),31);c.update(31)
    assert not c.fallback and c.stage=='yellow'


@pytest.mark.parametrize('obs',[Observation(1,(1,1,1,1)),Observation(-1,(0,0,0,0)),Observation(0,(-1,0,0,0)),Observation(0,(True,0,0,0)),Observation(0,(1,2,3)),Observation(0,(1.0,0,0,0))])
def test_reject_bad_observation(obs):
    with pytest.raises(ValueError):Controller().observe(obs,0)


def test_duplicate_and_reordered_observations():
    c=Controller();c.observe(Observation(2,(0,0,0,0)),2)
    for stamp in [2,1]:
        with pytest.raises(ValueError):c.observe(Observation(stamp,(0,0,0,0)),3)


def test_nonconsecutive_time_rejected():
    c=Controller('fijo');c.update(0)
    with pytest.raises(ValueError):c.update(2)


def test_invalid_timing():
    with pytest.raises(ValueError):Timing(min_green=30,max_green=20)
    with pytest.raises(ValueError):Timing(yellow=0)


def test_paired_demand_reproducible():
    a=generate('dinamico',101);b=generate('dinamico',101)
    assert a==b and a!=generate('dinamico',102)
    assert all(0<=v['scheduled']<1800 for v in a)
    assert len({v['id'] for v in a})==len(a)


def test_zero_demand_horizon():
    assert generate('medio',101,0)==[]
