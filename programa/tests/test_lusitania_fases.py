import pytest
from its.config import Timing
from its.controller import Observation
from its.lusitania import ControlLusitania


@pytest.mark.parametrize('mode', ['fijo', 'adaptativo'])
def test_cuatro_entradas_con_amarillo_y_rojo(mode):
    c=ControlLusitania(mode, Timing(fixed_green=10,min_green=5,max_green=10), peatones=False)
    estados=[]
    for t in range(60):
        c.observe(Observation(t,(2,2,2,2)),t)
        estados.append(c.update(t))
    assert [estados[t] for t in (0,15,30,45)]==['Grrr','rGrr','rrGr','rrrG']
    for start in (0,15,30,45):
        assert all(s.count('y')==1 for s in estados[start+10:start+13])
        assert estados[start+13:start+15]==['rrrr','rrrr']


@pytest.mark.parametrize('peatones', [False, True])
def test_espera_a_vehiculos_lentos_en_el_cruce(peatones):
    c=ControlLusitania('fijo', Timing(fixed_green=10), peatones=peatones)
    for t in range(25):
        c.pedestrians(t,0,0,int(13<=t<24))
        state=c.update(t)
        if 13<=t<24:assert state=='rrrr'
    assert state=='rGrr'


def test_peaton_lento_mantiene_cerrados_los_movimientos_incompatibles():
    c=ControlLusitania('adaptativo',Timing(min_green=5,max_green=10))
    c.compatibles={('E', 'paso_N'):{4}}
    entered=None
    for t in range(90):
        c.observe(Observation(t,(0,0,0,0)),t)
        c.detectar_pasos(t,{'paso_N':int(t<10)},{'paso_N':int(entered is not None and t<80)})
        c.update(t)
        if c.stage=='walk' and entered is None:entered=t
        if entered is not None and t<80:
            assert c.paso=='paso_N'
            assert c.axis==1
            assert c.stage in ('walk','ped_clear')
    assert entered is not None
    assert c.axis>0


def test_respaldo_sin_muestras_conserva_los_cuatro_turnos():
    c=ControlLusitania('adaptativo',Timing(fixed_green=10),peatones=False)
    states=[c.update(t) for t in range(60)]
    assert c.fallback
    assert {s for s in states if 'G' in s}=={'Grrr','rGrr','rrGr','rrrG'}


def test_derechas_sur_y_norte_se_abren_por_separado_con_este_verde():
    c=ControlLusitania('fijo',peatones=False)
    opened={'S':[],'N':[]}
    for t in range(70):
        c.update(t)
        color=c.senal_derecha()
        if color in 'Gg':
            assert c.state()=='rGrr'
            opened[c.derecha].append(t)
            assert color==('g' if c.derecha=='N' else 'G')
    assert len(opened['S'])==len(opened['N'])==6
    assert min(opened['N'])-max(opened['S'])>=6


def test_segunda_derecha_espera_a_la_primera_y_respeta_el_amarillo():
    c=ControlLusitania('fijo',peatones=False)
    for t in range(61):
        c.rutas_dentro={('S','E')} if t<55 else set()
        c.update(t)
        if 44<=t<55:assert c.senal_derecha()=='r'
    assert c.derecha=='N' and c.senal_derecha()=='g'


def test_no_hay_derechas_adicionales_durante_paso_peatonal():
    c=ControlLusitania('fijo')
    c.compatibles={('E','paso_N'):{1}}
    for t in range(65):
        c.detectar_pasos(t,{'paso_N':int(t<35)},{'paso_N':int(35<=t<60)})
        c.update(t)
        if c.stage in ('walk','ped_clear'):assert c.senal_derecha()=='r'
