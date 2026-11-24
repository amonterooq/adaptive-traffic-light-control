import json
from statistics import mean
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.config import ROOT
from its.lusitania import PLAN
from its.rotonda import PLAN_ROTONDA


def read(name):
    return json.loads((ROOT/'datos/procesados'/name).read_text(encoding='utf-8'))


def test_solo_se_sustituyen_los_21_ensayos_urbanos():
    before=read('historico_v1_6/resumenes_336.json')
    after=read('resumenes_336.json')
    assert len(before)==len(after)==336
    laboratory=[r for r in before if r['summary'].get('location','laboratorio')=='laboratorio']
    assert len(laboratory)==315
    assert all(r in after for r in laboratory)
    urban=[r for r in after if r['summary'].get('location') in ('lusitania','santa_eulalia')]
    assert len(urban)==21
    for r in urban:
        assert r['summary']['signal_plan']=={'lusitania':PLAN,'santa_eulalia':PLAN_ROTONDA}[r['summary']['location']]
    for file in ('multicruce.json','mixto.json'):
        old={json.dumps(r['config'],sort_keys=True):r['summary'] for r in read('historico_v1_6/'+file)['results']}
        for r in read(file)['results']:
            previous=old[json.dumps(r['config'],sort_keys=True)]
            for key in ('demand_sha256','fleet_sha256','pedestrian_demand_sha256','turns_sha256'):
                assert previous.get(key)==r['summary'].get(key)


def test_medias_largas_se_calculan_solo_con_las_tres_semillas_largas():
    data=read('movimientos_30min.json')
    assert data['horizon']==1800 and data['warmup']==300 and data['runs']==len(data['results'])==12
    for row in data['comparisons']:
        for mode in ('fijo','adaptativo'):
            selected=[r for r in data['results'] if r['config']['location']==row['location'] and r['config']['mode']==mode]
            assert {r['config']['seed'] for r in selected}=={101,102,103}
            for r in selected:
                s=r['summary']
                assert s['completed'] and s['generated']==s['arrived']
                assert s['collisions']==s['teleports']==s['ped_conflicts']==0
                assert s['horizon']==1800 and s['warmup']==300
            for metric in ('mean_wait_s','ped_mean_wait_s','co2_mean_g'):
                assert row[mode+'_'+metric]==pytest.approx(mean(r['summary'][metric] for r in selected))


def test_api_ofrece_los_resultados_actuales_y_separa_duraciones(tmp_path):
    with TestClient(create_app(tmp_path/'test.db')) as client:
        mixed=client.get('/api/results/mixed').json()
        assert mixed['horizon']==180
        assert not any(r['legacy_signal_plan'] for r in mixed['comparisons'])
        long=client.get('/api/results/movements').json()
        assert long['horizon']==1800 and len(long['comparisons'])==2
        points=client.get('/api/locations/metrics').json()['points']
        for p in points:
            assert p['origin']=='example'
            if p['id']=='lusitania':assert p['example']['summary']['signal_plan']==PLAN
            if p['id']=='santa_eulalia':assert p['example']['summary']['signal_plan']==PLAN_ROTONDA
