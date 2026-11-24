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
from its.storage import Store


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
    store=Store(tmp_path/'historial.db')
    store.start('ensayo',{'scenario':'medio','mode':mode,'seed':101,'location':'lusitania'})
    result=run('medio',mode,101,tmp_path,horizon=180,warmup=30,max_drain=900,
        pedestrian_profile=profile,location='lusitania',on_frame=frames.append,
        on_step=lambda sample:store.sample('ensayo',sample))
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
    assert result['signal_plan']=='lusitania_movimientos_v3'
    assert any('G' in f['sample']['tls_state'] for f in frames)
    root=ET.parse(network_directory('lusitania',profile!='desactivado')/'red.net.xml').getroot()
    crossing_arms={e.get('id'):e.get('crossingEdges').split()[0][0]
                   for e in root.findall('edge') if e.get('function')=='crossing'}
    for frame in frames:
        assert frame['sample']['state'].count('G')<=1
        turns=frame['sample']['movement_signals']
        assert not (turns['N']['r'] in 'Ggy' and turns['S']['r'] in 'Ggy')
        for arm in ('N','S'):
            if frame['sample']['state']=='rGrr' and turns[arm]['r'] in 'Gg':
                assert turns[arm]['s']==turns[arm]['l']=='r'
                assert all(v=='G' for v in turns['E'].values())
        assert frame['sample']['location']=='lusitania'
        assert len([a for a in frame['agents'] if a['kind']=='vehicle'])==frame['sample']['in_network']
        sample=frame['sample']
        protected={crossing_arms[a['road']] for a in frame['agents']
                   if a['kind']=='person' and a['road'] in crossing_arms}
        protected.update(crossing_arms[p] for p,s in sample['ped_signals'].items() if s=='G')
        for origin,turns in sample['movement_signals'].items():
            for turn,color in turns.items():
                if color not in 'Ggy':continue
                destination=ARMS[(ARMS.index(origin)+{'r':-1,'s':2,'l':1}[turn])%4]
                assert not {origin,destination}&protected
    if profile!='desactivado':
        assert result['ped_generated']==result['ped_arrived']==result['ped_crossed']>0
        assert result['ped_conflicts']==0
        assert any(f['sample']['ped_signal']=='G' and 'G' in f['sample']['state'] for f in frames)
    assert not frames[-1]['agents']
    restored=store.samples('ensayo')
    assert restored[-1]['movement_signals']==frames[-1]['sample']['movement_signals']
    if profile=='desactivado':assert all(s['ped_signal'] is None for s in restored)


@pytest.mark.parametrize('enabled',[False,True])
def test_giro_norte_cede_a_los_dos_carriles_rectos_del_este(enabled):
    root=ET.parse(network_directory('lusitania',enabled)/'red.net.xml').getroot()
    connections=[c for c in root.findall('connection') if c.get('tl')=='J1']
    right=next(c for c in connections if c.get('from')=='N_in' and c.get('dir')=='r')
    east=[c for c in connections if c.get('from')=='E_in' and c.get('dir')=='s']
    # En esta red J1 es un único nudo y conserva la numeración de netconvert.
    req=root.find("junction[@id='J1']").findall('request')[int(right.get('linkIndex'))]
    for c in east:assert req.get('response')[::-1][int(c.get('linkIndex'))]=='1'
    phase=next(p.get('state') for p in root.find('tlLogic').findall('phase')
               if p.get('state')[int(right.get('linkIndex'))]=='g')
    assert all(phase[int(c.get('linkIndex'))]=='G' for c in east)


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
