import csv
import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from pydantic import ValidationError
from its.api import RunRequest
from its.camaras import Camaras, CameraConfig, Deteccion
from its.cooperative import CooperativeSensing, SensingConfig, VehicleReport
from its.demand import generate, save
from its.trafico import TrafficConfig, configurar_flota
from its.runner import run
from its.rotonda import ControlRotonda
from its.controller import Observation
from its.scene import geometry
from its.storage import Store


def test_camara_sin_v2i_y_clasificacion_desconocida():
    camara = Camaras(CameraConfig(enabled=True, unclassified_percent=100), 101)
    datos = [Deteccion('bici','N',40,5,'bicicleta'), Deteccion('fuera','E',90,10,'coche')]
    muestra = camara.observar(0, datos)
    proximos, telemetria = camara.fusionar(0, None, set())
    assert muestra['camera_detected'] == muestra['camera_desconocido'] == 1
    assert proximos == (1,0,0,0) and telemetria['fusion_eta_min'] == 8
    assert camara.fusionar(0, None, {'bici'})[0] == (0,0,0,0)


def test_fusion_no_duplica_y_usa_velocidad_actual():
    v2i = CooperativeSensing(SensingConfig(mode='hybrid', penetration=100, latency_s=0), 1)
    v2i.observe(0, [VehicleReport('a','N',0,50,10), VehicleReport('b','E',0,70,10)], set())
    camara = Camaras(CameraConfig(enabled=True), 1)
    camara.observar(1, [Deteccion('a','N',40,2,'coche')])
    proximos, _ = camara.fusionar(1, v2i, set())
    assert proximos == (0,1,0,0)  # La cámara ha observado que a ya está frenando.
    camara.observar(4, [])
    assert sum(camara.fusionar(4, v2i, set())[0]) == 0


def test_omisiones_totales_y_limites_api():
    camara = Camaras(CameraConfig(enabled=True, missed_percent=100), 1)
    assert camara.observar(0, [Deteccion('a','N',20,10,'moto')])['camera_detected'] == 0
    assert sum(camara.fusionar(0, None, set())[0]) == 0
    with pytest.raises(ValidationError):
        RunRequest(location='lusitania', traffic=TrafficConfig(speeds='exceso'))
    with pytest.raises(ValidationError):
        CameraConfig(missed_percent=101)


def test_flota_reproducible_sin_cambiar_llegadas(tmp_path):
    vehiculos = generate('medio', 101, 180)
    save(vehiculos, tmp_path)
    antes = (tmp_path/'demanda.csv').read_bytes()
    config = TrafficConfig(fleet='mixto', speeds='exceso')
    configurar_flota(tmp_path, config, 101, 'laboratorio')
    primero = (tmp_path/'flota.csv').read_bytes()
    configurar_flota(tmp_path, config, 101, 'laboratorio')
    assert primero == (tmp_path/'flota.csv').read_bytes()
    assert antes == (tmp_path/'demanda.csv').read_bytes()
    tipos = {v.get('type') for v in ET.parse(tmp_path/'demanda.rou.xml').getroot().findall('vehicle')}
    assert tipos == {'coche','moto','bicicleta','patinete'}


def test_rotonda_conserva_transiciones_y_despeje():
    control=ControlRotonda()
    estados=[]
    for t in range(46):
        control.observe(Observation(t,(1,0,0,0)),t)
        control.pedestrians(t,int(t<15),int(25<=t<42),0)
        estados.append(control.update(t))
    assert estados[:10]==['GGGG']*10
    assert estados[10:13]==['yyyy']*3
    assert estados[13:42]==['rrrr']*29
    assert estados[42]=='GGGG'


def test_rotonda_tiene_anillo_cuatro_pasos_y_salida_don_benito():
    red=geometry(True,'santa_eulalia')
    assert len([l for l in red['lanes'] if l['kind']=='crossing'])==4
    assert any(l['id']=='D_out_0' for l in red['lanes'])
    assert sum(l['id'].startswith('ring_') for l in red['lanes'])>20


def test_migracion_conserva_sesiones_y_permite_estado_rotonda(tmp_path):
    path=tmp_path/'historial.sqlite3'
    schema=Path(__file__).parents[1].joinpath('its/schema.sql').read_text(encoding='utf-8')
    schema=schema.replace(",'GGGG','yyyy'",'').replace('user_version = 4','user_version = 3')
    with sqlite3.connect(path) as db:
        db.executescript(schema)
        db.execute("INSERT INTO runs VALUES ('a','medio','fijo',101,'fecha','complete','{}','{}')")
        db.execute("INSERT INTO samples VALUES ('a',0,1,0,0,0,'GrGr',0,0,1)")
        db.execute("INSERT INTO pedestrian_samples VALUES ('a',0,'r',1,0,'green')")
        db.execute("INSERT INTO cooperative_samples VALUES ('a',0,'{\"v2x_fresh\":1}')")
    store=Store(path)
    assert store.samples('a')[0]['ped_waiting']==store.samples('a')[0]['v2x_fresh']==1
    store.sample('a',{'t':1,'q_N':0,'q_E':0,'q_S':0,'q_W':0,'state':'GGGG',
                      'fallback':False,'arrived':1,'in_network':0})
    with store.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==4
        assert not db.execute('PRAGMA foreign_key_check').fetchall()


@pytest.mark.integration
@pytest.mark.parametrize('location', ['laboratorio','lusitania','santa_eulalia'])
def test_trafico_mixto_escolar_se_completa_y_mide_co2(tmp_path, location):
    resultado = run('escolar','adaptativo',101,tmp_path,horizon=120,warmup=20,max_drain=900,
        location=location,pedestrian_profile='escolar',traffic=TrafficConfig(fleet='mixto',speeds='variable',emissions=True),
        camera=CameraConfig(enabled=True),sensing=SensingConfig(mode='hybrid',penetration=25))
    assert resultado['completed']
    assert resultado['collisions'] == resultado['teleports'] == resultado['ped_conflicts'] == 0
    assert resultado['co2_mean_g'] > 0
    assert resultado['co2_by_type_g']['bicicleta'] == resultado['co2_by_type_g']['patinete'] == 0
    filas = list(csv.DictReader((tmp_path/'serie.csv').open()))
    assert max(int(r['camera_detected']) for r in filas) > 0
    assert max(int(r['fusion_approaching']) for r in filas) > 0
