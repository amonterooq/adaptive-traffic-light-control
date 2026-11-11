"""Casos de la memoria compartidos por los scripts y el formulario de la aplicación."""
from .experimento import ExperimentConfig
from .config import Timing
from .trafico import TrafficConfig
from .camaras import CameraConfig
from .cooperative import SensingConfig
from .locations import catalog

CASOS = {
    'coches': {'fleet': 'coches', 'speeds': 'uniforme', 'ped': 'desactivado', 'camera': False},
    'mixto': {'speeds': 'uniforme', 'ped': 'desactivado'},
    'peatones': {'speeds': 'uniforme'},
    'velocidades': {}, 'exceso': {'speeds': 'exceso'},
    'omisiones': {'missed_percent': 30}, 'sin_clasificar': {'unclassified_percent': 100},
    'sin_camara': {'missed_percent': 100}, 'v2i50': {'penetration': 50},
    'escolar': {'scenario': 'escolar', 'ped': 'escolar', 'penetration': 50},
}
NOMBRES = {'bajo': 'Pocos coches', 'medio': 'Tráfico moderado', 'alto': 'Muchos coches',
           'desequilibrado': 'Más coches en una dirección', 'dinamico': 'El tráfico cambia con el tiempo'}
NOMBRES_MIXTOS = {'coches': 'Solo coches', 'mixto': 'Tráfico mixto sin peatones',
    'peatones': 'Con peatones', 'velocidades': 'Distintas velocidades', 'exceso': 'Ensayo 30/50/70',
    'omisiones': 'Cámara omite 30 %', 'sin_clasificar': 'Sin clasificación',
    'sin_camara': 'Cámara sin detecciones', 'v2i50': 'Cámara y V2I 50 %', 'escolar': 'Salida escolar'}


def referencia(scenario, mode, seed, profile='desactivado', green=30, blackout=None):
    return ExperimentConfig(scenario=scenario, mode=mode, seed=seed, pedestrian_profile=profile,
                            timing=Timing(fixed_green=green), simulate_outage=blackout is not None,
                            outage_start=blackout[0] if blackout else 60,
                            outage_end=blackout[1] if blackout else 90)


def cooperativo(location, seed, penetration):
    return ExperimentConfig(location=location, seed=seed, scenario='medio', mode='adaptativo',
        horizon=180, pedestrian_profile='frecuente',
        sensing=SensingConfig(mode='hybrid' if penetration else 'sensors', penetration=penetration))


def mixto(location, caso, seed, mode):
    opciones = CASOS[caso]
    penetration = opciones.get('penetration', 0)
    return ExperimentConfig(location=location, scenario=opciones.get('scenario', 'medio'),
        mode=mode, seed=seed, horizon=180, pedestrian_profile=opciones.get('ped', 'frecuente'),
        traffic=TrafficConfig(fleet=opciones.get('fleet', 'mixto'), speeds=opciones.get('speeds', 'variable')),
        camera=CameraConfig(enabled=opciones.get('camera', True),
            missed_percent=opciones.get('missed_percent', 0), unclassified_percent=opciones.get('unclassified_percent', 0)),
        sensing=SensingConfig(mode='hybrid' if penetration else 'sensors', penetration=penetration))


def catalogo_estudios():
    casos = []
    def incluir(id, grupo, nombre, config, seeds, modes=('fijo', 'adaptativo')):
        casos.append(dict(id=id, group=grupo, label=nombre, config=config.model_dump(), seeds=list(seeds), modes=list(modes)))
    for escenario, nombre in NOMBRES.items():
        incluir('principal_' + escenario, '1. Vehículos y emisiones', nombre,
                referencia(escenario, 'fijo', 101), range(101, 111))
    for perfil, nombre in [('sin', 'Nadie cruza, pero hay pasos'), ('ocasional', 'Peatones ocasionales'),
                          ('frecuente', 'Peatones frecuentes'), ('lento', 'Peatones que caminan despacio')]:
        incluir('peatones_' + perfil, '2. Peatones', nombre,
                referencia('medio', 'fijo', 101, perfil), range(101, 111))
    for site in catalog():
        if site['id'] != 'santa_eulalia':
            for porcentaje in (0, 50, 100):
                incluir(f"cooperativo_{site['id']}_{porcentaje}", '3. Sensores y V2I',
                        site['name'] + f' · V2I {porcentaje} %', cooperativo(site['id'], 101, porcentaje), range(101, 104), ('adaptativo',))
    for caso, nombre in NOMBRES_MIXTOS.items():
        incluir('mixto_' + caso, '4. Tráfico mixto y cámaras', 'Laboratorio · ' + nombre,
                mixto('laboratorio', caso, 101, 'fijo'), range(101, 104))
    for site in catalog():
        if site['id'] != 'laboratorio':
            incluir('escolar_' + site['id'], '5. Salida escolar en Mérida', site['name'],
                    mixto(site['id'], 'escolar', 101, 'fijo'), range(101, 104))
    for green in (20, 40):
        for escenario, nombre in NOMBRES.items():
            incluir(f'sensibilidad_{green}_{escenario}', '6. Sensibilidad y respaldo',
                    nombre + f' · verde fijo {green} s', referencia(escenario, 'fijo', 101, green=green), range(101, 104))
    incluir('fallo_muestras', '6. Sensibilidad y respaldo', 'Tráfico cambiante · interrupción 600–630 s',
            referencia('dinamico', 'fijo', 101, blackout=(600, 630)), range(101, 104))
    return casos
