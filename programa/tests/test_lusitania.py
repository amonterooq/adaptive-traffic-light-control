import csv
import hashlib
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.config import ARMS
from its.locations import lusitania, network_directory, project
from its.runner import run
from its.scene import geometry


def test_street_geometry_preserves_osm_axes_and_directions():
    source=lusitania()
    assert source['osm_node']=='445056976'
    assert source['center']==[-6.3370584,38.910752]
    for enabled in (False,True):
        result=geometry(enabled,'lusitania')
        xml=ET.parse(network_directory('lusitania',enabled)/'red.edg.xml').getroot()
        assert len([l for l in result['lanes'] if l['kind']=='road'])==12
        assert len([l for l in result['lanes'] if l['kind']=='crossing'])==4*enabled
        for arm in ARMS:
            incoming=xml.find(f"edge[@id='{arm}_in']")
            outgoing=xml.find(f"edge[@id='{arm}_out']")
            ins=[tuple(map(float,p.split(','))) for p in incoming.get('shape').split()]
            outs=[tuple(map(float,p.split(','))) for p in outgoing.get('shape').split()]
            assert ins==list(reversed(outs))
            for actual,coordinate in zip(outs,source['arms'][arm]['centerline']):
                assert actual==pytest.approx(project(coordinate),abs=.0001)
            assert len(incoming.findall('lane'))==(2 if arm in 'EW' else 1)+enabled
        assert project(source['arms']['N']['centerline'][-1])[1]>0
        assert project(source['arms']['S']['centerline'][-1])[1]<0
        assert len(result['context'])>100


@pytest.mark.integration
@pytest.mark.parametrize('mode,profile',[('fijo','frecuente'),('adaptativo','frecuente'),('adaptativo','lento'),('adaptativo','desactivado')])
def test_geographic_runs_turns_conservation_and_crossing_safety(tmp_path,mode,profile):
    frames=[]
    result=run('medio',mode,101,tmp_path,horizon=180,warmup=30,max_drain=900,
        pedestrian_profile=profile,location='lusitania',on_frame=frames.append)
    assert result['completed'] and not result['cancelled']
    assert result['collisions']==result['teleports']==0
    assert result['generated']==result['arrived']
    routes=list(csv.DictReader((tmp_path/'giros.csv').open()))
    assert {r['turn'] for r in routes}=={'left','right','straight'}
    assert all(r['arm']!=r['destination'] for r in routes)
    trips=ET.parse(tmp_path/'tripinfo.xml').getroot().findall('tripinfo')
    by_id={r['id']:r for r in routes}
    for trip in trips:assert trip.get('arrivalLane').startswith(by_id[trip.get('id')]['destination']+'_out_')
    assert hashlib.sha256((tmp_path/'giros.csv').read_bytes()).hexdigest()==result['turns_sha256']
    assert any('g' in f['sample']['tls_state'] for f in frames)
    for frame in frames:
        assert frame['sample']['location']=='lusitania'
        assert len([a for a in frame['agents'] if a['kind']=='vehicle'])==frame['sample']['in_network']
        if any(a['kind']=='person' and a['road'].startswith(':J1_c') for a in frame['agents']):
            assert frame['sample']['state']=='rrrr'
    if profile!='desactivado':
        assert result['ped_generated']==result['ped_arrived']==result['ped_crossed']>0
        assert result['ped_conflicts']==0
    assert not frames[-1]['agents']


def test_location_api_validation_and_persistence(tmp_path):
    seen={}
    def fake(*args,location,**kwargs):
        seen['location']=location
        return {'completed':True,'cancelled':False,'location':location}
    app=create_app(tmp_path/'test.db',fake)
    with TestClient(app) as client:
        assert len(client.get('/api/config').json()['locations'])==3
        assert client.get('/api/scene/network?location=lusitania').json()['name'].startswith('Lusitania')
        assert len(client.get('/api/map?location=lusitania').json()['features'])>100
        assert client.post('/api/runs',json={'location':'unknown'}).status_code==422
        assert client.get('/api/scene/network?location=unknown').status_code==422
        for retirada in ('mirandilla','panaderos'):
            assert client.post('/api/runs',json={'location':retirada}).status_code==422
            assert client.get('/api/scene/network?location='+retirada).status_code==422
            assert client.get('/api/map?location='+retirada).status_code==422
        client.post('/api/runs',json={'location':'lusitania'})
        app.state.manager.thread.join(5)
        assert seen['location']=='lusitania'
        assert client.get('/api/runs').json()[0]['config']['location']=='lusitania'
        assert client.get('/api/scene').json()['location']=='lusitania'
