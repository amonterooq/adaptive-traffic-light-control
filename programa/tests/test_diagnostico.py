import json
import pytest
from fastapi.testclient import TestClient
from its.api import create_app
from its.storage import Store


@pytest.mark.parametrize('status,summary,tipos', [
    ('complete', {'completed':True}, set()),
    ('cancelled', {'completed':False,'generated':10,'arrived':4}, {'cancelacion','viajes_pendientes'}),
    ('failed', {'completed':False,'collisions':4,'teleports':2,'ped_conflicts':1},
     {'colisiones','teletransportes','conflictos_peatonales'}),
    ('failed', {'completed':False,'ped_generated':8,'ped_arrived':6}, {'viajes_pendientes'}),
    ('failed', {'completed':False}, {'incompleta'}),
])
def test_informe_identifica_motivos_y_se_puede_descargar(tmp_path,status,summary,tipos):
    path=tmp_path/'historial.sqlite3'
    store=Store(path)
    config={'scenario':'escolar','mode':'adaptativo','seed':101,'location':'santa_eulalia'}
    store.start('ensayo',config)
    store.finish('ensayo',status,summary)
    with TestClient(create_app(path)) as client:
        response=client.get('/api/runs/ensayo/diagnostico?descargar=true')
        assert response.status_code==200
        assert response.headers['Content-Disposition'].startswith('attachment;')
        report=response.json()
        assert {r['tipo'] for r in report['incidencias']}==tipos
        assert report['config']==config
        assert report['apto_comparacion']==(status=='complete')
        assert client.get('/api/runs/desconocido/diagnostico').status_code==404


def test_fallo_del_simulador_no_expone_rutas_ni_traceback(tmp_path):
    privado=r'C:\Users\nombre\carpeta_privada\ejecucion.sumocfg'
    def roto(*args,**kwargs):
        raise FileNotFoundError(privado)
    app=create_app(tmp_path/'historial.sqlite3',roto)
    with TestClient(app) as client:
        id=client.post('/api/runs',json={}).json()['id']
        app.state.manager.thread.join(5)
        state=client.get('/api/state').json()
        assert state['status']=='failed'
        assert state['summary']['error_code']=='instalacion'
        for url in ('/api/state','/api/runs',f'/api/runs/{id}/diagnostico'):
            response=client.get(url)
            assert 'carpeta_privada' not in response.text
            assert 'Traceback' not in response.text
        assert client.get(f'/api/runs/{id}/diagnostico').json()['incidencias'][0]['tipo']=='instalacion'


def test_historial_retirado_se_conserva_pero_no_se_ofrece_como_punto(tmp_path):
    path=tmp_path/'historial.sqlite3'
    store=Store(path)
    config={'scenario':'medio','mode':'fijo','seed':101,'location':'panaderos'}
    store.start('antiguo',config)
    store.finish('antiguo','failed',{'error':r'No se abre C:\Users\nombre\privado.xml'})
    with TestClient(create_app(path)) as client:
        history=client.get('/api/runs').json()
        assert history[0]['config']==config
        assert 'privado' not in json.dumps(history)
        report=client.get('/api/runs/antiguo/diagnostico').json()
        assert report['config']==config and not report['apto_comparacion']
        assert 'privado' not in json.dumps(report)
        assert {p['id'] for p in client.get('/api/config').json()['locations']}=={
            'laboratorio','lusitania','santa_eulalia'}
        assert client.post('/api/runs',json=config).status_code==422
    assert json.loads(store.get_run('antiguo')['summary_json'])['error'].endswith('privado.xml')


def test_cierre_anterior_aparece_como_interrupcion(tmp_path):
    path=tmp_path/'historial.sqlite3'
    Store(path).start('abierto',{'scenario':'medio','mode':'fijo','seed':101})
    with TestClient(create_app(path)) as client:
        report=client.get('/api/runs/abierto/diagnostico').json()
        assert report['incidencias'][0]['tipo']=='interrumpida'
        assert not report['apto_comparacion']
