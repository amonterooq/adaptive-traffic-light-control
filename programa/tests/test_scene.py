import csv
import threading
import time
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.scene import geometry
from its.runner import run


def test_geometry_follows_both_sumo_networks():
    for enabled in (True,False):
        net=geometry(enabled)
        assert net['center']==[300,300]
        assert len([l for l in net['lanes'] if l['kind']=='crossing'])==(4 if enabled else 0)
        assert len([l for l in net['lanes'] if l['kind']=='road'])==8
        assert all(len(l['shape'])>=2 and l['width']>0 for l in net['lanes'])


@pytest.mark.integration
def test_live_positions_match_population_and_do_not_change_experiment(tmp_path):
    frames=[]
    args=dict(horizon=120,warmup=20,max_drain=300,pedestrian_profile='frecuente')
    baseline=run('medio','adaptativo',101,tmp_path/'baseline',**args)
    live=run('medio','adaptativo',101,tmp_path/'live',on_frame=frames.append,**args)
    assert live['completed']
    assert {k:v for k,v in live.items() if k!='wall_seconds'}=={k:v for k,v in baseline.items() if k!='wall_seconds'}
    assert (tmp_path/'live/serie.csv').read_bytes()==(tmp_path/'baseline/serie.csv').read_bytes()
    assert [f['time'] for f in frames]==list(range(1,len(frames)+1))
    known={row['id'] for row in csv.DictReader((tmp_path/'live/demanda.csv').open())}
    people={row['id'] for row in csv.DictReader((tmp_path/'live/demanda_peatones.csv').open())}
    seen_cars=set();seen_people=set();crossings=0
    for frame in frames:
        cars=[a for a in frame['agents'] if a['kind']=='vehicle']
        pedestrians=[a for a in frame['agents'] if a['kind']=='person']
        assert len(cars)==frame['sample']['in_network']
        assert len({a['id'] for a in frame['agents']})==len(frame['agents'])
        seen_cars.update(a['id'] for a in cars);seen_people.update(a['id'] for a in pedestrians)
        for agent in frame['agents']:
            assert -5<=agent['x']<=605 and -5<=agent['y']<=605
            assert agent['speed']>=0 and 0<=agent['angle']<=360
        if any(a['road'].startswith(':J1_c') for a in pedestrians):
            crossings+=1
            assert frame['sample']['state']=='rrrr'
    assert seen_cars==known and seen_people==people and crossings>0
    assert not frames[-1]['agents']


def test_scene_cursor_pause_speed_stop_and_new_run(tmp_path):
    ready=threading.Event()
    def ticking(*args,on_frame,playback,should_stop,**kwargs):
        for t in range(300):
            playback()
            if should_stop():break
            on_frame({'time':t+1,'agents':[],'sample':{}});ready.set()
        return {'cancelled':should_stop(),'completed':not should_stop()}
    app=create_app(tmp_path/'test.db',ticking)
    with TestClient(app) as client:
        assert client.post('/api/playback',json={'paused':True}).status_code==409
        first=client.post('/api/runs',json={'speed':10}).json()['id'];assert ready.wait(5)
        assert client.get('/api/scene/network?pedestrians=false').json()['pedestrians'] is False
        assert client.post('/api/playback',json={'paused':True}).status_code==200
        time.sleep(.15)
        before=client.get('/api/scene').json();assert before['paused'] and before['reset']
        latest=before['frames'][-1]['time'];time.sleep(.15)
        assert client.get(f'/api/scene?after={latest}&run_id={first}').json()['frames']==[]
        assert client.post('/api/playback',json={'speed':20,'paused':False}).status_code==200
        time.sleep(.2)
        after=client.get(f'/api/scene?after={latest}&run_id={first}').json()
        assert after['speed']==20 and after['frames'] and not after['reset']
        assert client.post('/api/playback',json={'paused':True}).status_code==200
        client.post('/api/stop');app.state.manager.thread.join(5)
        assert not app.state.manager.thread.is_alive()
        assert client.get('/api/state').json()['status']=='cancelled'
        second=client.post('/api/runs',json={'speed':1}).json()['id']
        assert second!=first
        assert client.get(f'/api/scene?after=9999&run_id={first}').json()['reset']
        client.post('/api/stop');app.state.manager.thread.join(5)


@pytest.mark.parametrize('body',[{'speed':0},{'paused':'true'},{'speed':101},{'unknown':True}])
def test_playback_validation(tmp_path,body):
    with TestClient(create_app(tmp_path/'test.db')) as client:
        assert client.post('/api/playback',json=body).status_code==422
