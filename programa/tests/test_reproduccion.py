import json
import pytest
from fastapi.testclient import TestClient
from its.api import RunRequest, create_app
from its.estudios import catalogo_estudios, referencia, mixto
from its.runner import run
from its.trafico import TrafficConfig


def test_catalogo_cubre_las_336_ejecuciones_y_se_puede_cargar():
    estudios = catalogo_estudios()
    assert len(estudios) == 38
    assert sum(len(e['seeds']) * len(e['modes']) for e in estudios) == 336
    assert len({e['id'] for e in estudios}) == len(estudios)
    for estudio in estudios:
        peticion = RunRequest(**estudio['config'])
        assert peticion.traffic.emissions
        assert peticion.run_kwargs()['warmup'] == (300 if peticion.horizon == 1800 else 30)


@pytest.mark.integration
def test_medir_emisiones_no_cambia_la_flota_ni_la_circulacion(tmp_path):
    resultados = []
    for enabled in (False, True):
        path = tmp_path / str(enabled)
        resultados.append(run('medio', 'adaptativo', 101, path, horizon=120, warmup=20,
                              traffic=TrafficConfig(emissions=enabled)))
    for archivo in ('demanda.csv', 'demanda.rou.xml', 'flota.csv', 'serie.csv'):
        assert (tmp_path/'False'/archivo).read_bytes() == (tmp_path/'True'/archivo).read_bytes()
    for key in ('mean_wait_s', 'mean_travel_s', 'mean_queue', 'mean_stops', 'fleet_sha256'):
        assert resultados[0][key] == resultados[1][key]
    assert 'co2_mean_g' not in resultados[0] and resultados[1]['co2_mean_g'] > 0


@pytest.mark.integration
@pytest.mark.parametrize('specification', [referencia('medio', 'adaptativo', 101),
                                         mixto('laboratorio', 'velocidades', 101, 'adaptativo')])
def test_api_y_lote_producen_los_mismos_viajes_y_metricas(tmp_path, specification):
    lote = run(specification.scenario, specification.mode, specification.seed,
               tmp_path/'lote', **specification.run_kwargs())
    def rapido(*args, playback=None, **kwargs):
        return run(*args, **kwargs)
    app = create_app(tmp_path/'sesiones/historial.sqlite3', rapido)
    with TestClient(app) as client:
        response = client.post('/api/runs', json={**specification.model_dump(), 'speed': 100})
        assert response.status_code == 201
        app.state.manager.thread.join(180)
        state = client.get('/api/state').json()
        assert state['status'] == 'complete'
        interfaz = state['summary']
        assert {k:v for k,v in lote.items() if k != 'wall_seconds'} == {
            k:v for k,v in interfaz.items() if k != 'wall_seconds'}
        archivo = tmp_path/'sesiones/runs'/response.json()['id']/'resumen.json'
        assert json.loads(archivo.read_text(encoding='utf-8')) == interfaz
