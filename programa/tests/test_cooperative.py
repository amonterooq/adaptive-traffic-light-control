import csv
import sqlite3
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.cooperative import CooperativeSensing,SensingConfig,VehicleReport
from its.controller import Controller,Observation
from its.locations import catalog,geographic
from its.runner import run
from its.scene import geometry
from its.storage import Store


def test_latency_eta_and_expiration():
    sensor=CooperativeSensing(SensingConfig(mode='hybrid',penetration=100,latency_s=1),101)
    message=VehicleReport('car','N',0,60,10)
    counts,values=sensor.observe(0,[message],set())
    assert values['v2x_fresh']==0 and sum(counts)==0
    counts,values=sensor.observe(1,[],set())
    assert counts==(1,0,0,0) and values['v2x_eta_min']==5 and values['v2x_age_max']==1
    _,values=sensor.observe(4,[],set())
    assert values['v2x_fresh']==0 and values['v2x_eta_min'] is None


def test_stopped_car_is_not_double_counted_and_slow_eta_is_unknown():
    sensor=CooperativeSensing(SensingConfig(mode='hybrid',penetration=100,latency_s=0),101)
    reports=[VehicleReport('queued','E',0,20,5),VehicleReport('slow','N',0,10,.5),VehicleReport('arriving','S',0,30,5)]
    counts,data=sensor.observe(0,reports,{'queued'})
    assert counts==(0,0,1,0) and data['v2x_eta_min']==6
    assert data['v2x_fresh']==3
    assert Observation(0,(0,1,0,0),counts).demand==(0,1,1,0)


@pytest.mark.parametrize('parameters',[{'penetration':0},{'loss_percent':100},{'latency_s':5},{'range_m':20}])
def test_unavailable_reports_do_not_create_demand(parameters):
    config={'mode':'hybrid','penetration':100,'latency_s':0,**parameters}
    sensor=CooperativeSensing(SensingConfig(**config),101)
    for t in range(10):
        counts,values=sensor.observe(t,[VehicleReport('v','E',t,30,5)],set())
        assert not sum(counts) and values['v2x_fresh']==0


def test_equipment_and_loss_are_repeatable_and_independent_of_iteration_order():
    first=CooperativeSensing(SensingConfig(mode='hybrid',penetration=50,loss_percent=30,latency_s=0),7)
    second=CooperativeSensing(first.config,7)
    reports=[VehicleReport(str(i),'N',0,30,5) for i in range(100)]
    assert first.observe(0,reports,set())==second.observe(0,list(reversed(reports)),set())
    assert 20<len(first.fresh_ids)<50
    assert 0<first.lost<first.sent


def test_anticipation_changes_decision_without_skipping_clearance():
    sensor_only=Controller();hybrid=Controller()
    states=[]
    for t in range(16):
        sensor_only.observe(Observation(t,(1,2,0,0)),t)
        hybrid.observe(Observation(t,(1,2,0,0),(0,4,0,0)),t)
        sensor_only.update(t);states.append(hybrid.update(t))
    assert sensor_only.stage=='green'
    assert states[:10]==['GrGr']*10 and states[10:13]==['yryr']*3
    assert states[13:15]==['rrrr']*2 and states[15]=='rGrG'


@pytest.mark.parametrize('location',['lusitania'])
@pytest.mark.parametrize('profile',['frecuente','desactivado'])
@pytest.mark.parametrize('mode',['fijo','adaptativo'])
@pytest.mark.integration
def test_geographic_sensing_cooperates_and_completes(tmp_path,location,profile,mode):
    data=geographic(location)
    assert -6.37<data['center'][0]<-6.32 and 38.90<data['center'][1]<38.94
    for enabled in (False,True):
        geo=geometry(enabled,location)
        assert len([lane for lane in geo['lanes'] if lane['kind']=='road'])==12
        assert len([lane for lane in geo['lanes'] if lane['kind']=='crossing'])==4*enabled
        assert all(lane['id'].startswith(':J1_') for lane in geo['lanes'] if lane['kind']=='walkingarea')
    frames=[]
    result=run('medio',mode,101,tmp_path,horizon=180,warmup=30,max_drain=900,
        location=location,pedestrian_profile=profile,sensing=SensingConfig(mode='hybrid',penetration=50),on_frame=frames.append)
    assert result['completed'] and result['generated']==result['arrived']
    assert result['collisions']==result['teleports']==0
    assert result['v2x_received']>0
    assert any(f['sample']['v2x_approaching']>0 for f in frames)
    assert any(a.get('connected_vehicle') for f in frames for a in f['agents'])
    if profile!='desactivado':
        assert result['ped_generated']==result['ped_arrived'] and result['ped_conflicts']==0
        for f in frames:
            assert sum(f['sample']['ped_wait_'+a] for a in 'NESW')==f['sample']['ped_waiting']
            if f['sample']['ped_crossing']:assert f['sample']['state']=='rrrr'


@pytest.mark.integration
def test_total_v2x_loss_preserves_sensor_control(tmp_path):
    traces=[]
    for name,config in [('baseline',SensingConfig()),('lost',SensingConfig(mode='hybrid',penetration=100,loss_percent=100))]:
        target=tmp_path/name
        result=run('medio','adaptativo',101,target,horizon=100,warmup=10,location='lusitania',pedestrian_profile='lento',sensing=config)
        assert result['completed'] and not result['ped_conflicts']
        traces.append(list(csv.DictReader((target/'serie.csv').open())))
    for first,second in zip(*traces):
        assert first=={key:second[key] for key in first}
    assert len(traces[0])==len(traces[1])


def test_api_catalog_metrics_migration_and_cooperative_csv(tmp_path):
    path=tmp_path/'test.db';store=Store(path)
    with store.connect() as db:
        db.execute('DROP TABLE cooperative_samples');db.execute('PRAGMA user_version=2')
    store=Store(path)
    config={'scenario':'medio','mode':'adaptativo','seed':101,'location':'lusitania','horizon':120,'sensing':{'mode':'hybrid','penetration':50}}
    store.start('recent',config)
    sample={'t':0,'q_N':1,'q_E':0,'q_S':0,'q_W':0,'state':'GrGr','fallback':False,'arrived':0,'in_network':2,
            'sensing_mode':'hybrid','v2x_fresh':1,'v2x_approaching':1,'v2x_eta_min':4.2}
    store.sample('recent',sample);store.finish('recent','complete',{'completed':True,'mean_wait_s':12})
    store.start('cancelled',config);store.finish('cancelled','cancelled',{'completed':False})
    with TestClient(create_app(path)) as client:
        assert {p['id'] for p in client.get('/api/config').json()['locations']}=={p['id'] for p in catalog()}
        points=client.get('/api/locations/metrics').json()['points']
        current=next(p for p in points if p['id']=='lusitania')
        assert current['origin']=='session' and current['last_run']['id']=='recent' and not current['active']
        assert client.get('/api/runs/recent/samples').json()[0]['v2x_fresh']==1
        assert 'v2x_eta_min' in client.get('/api/runs/recent/export').text
        for bad in [{'penetration':101},{'latency_s':-1},{'mode':'real'},{'range_m':10000}]:
            assert client.post('/api/runs',json={'sensing':bad}).status_code==422
    with sqlite3.connect(path) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==4


@pytest.mark.integration
def test_short_arm_pedestrians_must_use_the_signalized_crossing(tmp_path):
    result=run('medio','adaptativo',103,tmp_path,horizon=180,warmup=30,max_drain=900,
               location='lusitania',pedestrian_profile='frecuente')
    assert result['completed']
    assert result['ped_generated']==result['ped_arrived']==result['ped_crossed']==34
    assert result['ped_conflicts']==result['collisions']==result['teleports']==0
