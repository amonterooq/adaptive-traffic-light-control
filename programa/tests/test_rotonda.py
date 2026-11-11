import xml.etree.ElementTree as ET
import pytest
from its.estudios import mixto
from its.locations import network_directory
from its.rotonda import prioridades_vehiculares
from its.runner import run


@pytest.mark.parametrize('peatones', [False,True])
def test_prioridades_respetan_los_conflictos_de_convergencia(peatones):
    path=network_directory('santa_eulalia',peatones)
    root=ET.parse(path/'red.net.xml').getroot()
    conexiones=sorted([c for c in root.findall('connection') if c.get('tl')=='J1'],
                      key=lambda c:int(c.get('linkIndex')))
    links=[[(c.get('from')+'_'+c.get('fromLane'),c.get('to')+'_'+c.get('toLane'),c.get('via'))]
           for c in conexiones]
    prioridad=prioridades_vehiculares(path,links)
    indices={c.get('via'):int(c.get('linkIndex')) for c in conexiones}
    cesiones=0
    for junction in root.findall('junction'):
        if not junction.get('id').startswith('G_'):
            continue
        carriles=junction.get('intLanes').split()
        for request in junction.findall('request'):
            i=int(request.get('index'))
            if carriles[i] not in indices:
                continue
            destino=indices[carriles[i]]
            for j,debe_ceder in enumerate(reversed(request.get('response'))):
                if debe_ceder!='1' or carriles[j] not in indices:
                    continue
                otro=indices[carriles[j]]
                if prioridad[destino]!='r' and prioridad[otro]!='r':
                    assert prioridad[destino]=='g'
                    assert prioridad[otro]=='G'
                    cesiones+=1
    assert cesiones==2


@pytest.mark.integration
@pytest.mark.parametrize('seed', [101,102,103])
@pytest.mark.parametrize('mode', ['fijo','adaptativo'])
def test_rotonda_escolar_treinta_minutos_sin_incidentes(tmp_path,seed,mode):
    config=mixto('santa_eulalia','escolar',seed,mode).model_copy(update={'horizon':1800})
    result=run(config.scenario,config.mode,config.seed,tmp_path,**config.run_kwargs())
    assert result['completed']
    assert result['generated']==result['arrived']
    assert result['ped_generated']==result['ped_arrived']==result['ped_crossed']
    assert result['collisions']==result['teleports']==result['ped_conflicts']==0
    assert result['collision_events']==[]
    assert result['co2_mean_g']>0
