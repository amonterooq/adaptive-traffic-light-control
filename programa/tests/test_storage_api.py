import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.storage import Store


def fake_run(*args,on_step,should_stop,**kwargs):
    on_step({'t':0,'q_N':1,'q_E':2,'q_S':3,'q_W':4,'state':'GrGr','fallback':False,'arrived':0,'in_network':10})
    return {'cancelled':False,'completed':True,'mean_wait_s':12.5}


def test_api_roundtrip_and_export(tmp_path):
    app=create_app(tmp_path/'test.db',fake_run)
    with TestClient(app) as c:
        assert c.get('/api/health').json()['traffic']=='simulado'
        assert c.get('/').status_code==200
        result=c.post('/api/runs',json={'scenario':'medio','mode':'adaptativo','seed':101})
        assert result.status_code==201
        app.state.manager.thread.join(5)
        assert c.get('/api/state').json()['status']=='complete'
        id=result.json()['id']
        assert len(c.get(f'/api/runs/{id}/samples').json())==1
        assert 'q_n' in c.get(f'/api/runs/{id}/export').text
        assert c.get('/api/runs').json()[0]['summary']['mean_wait_s']==12.5
        assert c.get('/api/runs/does-not-exist/export').status_code==404
    with TestClient(create_app(tmp_path/'test.db',fake_run)) as c:
        assert len(c.get('/api/runs').json())==1


@pytest.mark.parametrize('body',[{'seed':-1},{'seed':True},{'seed':'101'},{'scenario':'inventado'},{'timing':{'min_green':30,'max_green':20}},{'horizon':0},{'speed':1000},{'unknown':'x'}])
def test_request_validation(tmp_path,body):
    with TestClient(create_app(tmp_path/'test.db',fake_run)) as c:
        assert c.post('/api/runs',json=body).status_code==422


def test_cross_origin_write_rejected(tmp_path):
    with TestClient(create_app(tmp_path/'test.db',fake_run)) as c:
        assert c.post('/api/runs',json={},headers={'Origin':'https://example.org'}).status_code==403


def test_concurrent_run_and_stop(tmp_path):
    def blocked(*args,should_stop,**kwargs):
        while not should_stop():time.sleep(.01)
        return {'cancelled':True,'completed':False}
    app=create_app(tmp_path/'test.db',blocked)
    with TestClient(app) as c:
        assert c.post('/api/runs',json={}).status_code==201
        assert c.post('/api/runs',json={}).status_code==409
        assert c.post('/api/stop').status_code==200
        app.state.manager.thread.join(5)
        assert c.get('/api/state').json()['status']=='cancelled'


def test_interrupted_run_recovered(tmp_path):
    store=Store(tmp_path/'test.db');store.start('a',{'scenario':'medio','mode':'fijo','seed':101})
    app=create_app(tmp_path/'test.db',fake_run)
    assert app.state.manager.store.runs()[0]['status']=='failed'


def test_database_rejects_orphan_sample(tmp_path):
    store=Store(tmp_path/'test.db')
    with pytest.raises(sqlite3.IntegrityError):
        store.sample('missing',{'t':0,'q_N':0,'q_E':0,'q_S':0,'q_W':0,'state':'GrGr','fallback':False,'arrived':0,'in_network':0})


def test_version_one_migrates_and_persists_pedestrian_samples(tmp_path):
    path=tmp_path/'test.db'
    store=Store(path)
    with store.connect() as db:
        db.execute('DROP TABLE pedestrian_samples')
        db.execute('PRAGMA user_version=1')
    store=Store(path)
    store.start('a',{'scenario':'medio','mode':'adaptativo','seed':101})
    sample={'t':0,'q_N':1,'q_E':0,'q_S':0,'q_W':0,'state':'rrrr','fallback':False,'arrived':0,'in_network':1,
            'ped_signal':'G','ped_waiting':2,'ped_crossing':1,'ped_stage':'walk'}
    store.sample('a',sample)
    restored=Store(path).samples('a')[0]
    assert restored['ped_signal']=='G' and restored['ped_crossing']==1
    with store.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==4
        db.execute("DELETE FROM runs WHERE id='a'")
        assert db.execute('SELECT COUNT(*) FROM pedestrian_samples').fetchone()[0]==0
