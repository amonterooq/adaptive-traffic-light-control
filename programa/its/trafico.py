"""Tipos de vehículo y velocidades de los ensayos complementarios."""
import csv
from hashlib import sha256
from typing import Literal
import xml.etree.ElementTree as ET
from pydantic import BaseModel, ConfigDict
from .network import write_xml


class TrafficConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    fleet: Literal['coches', 'mixto'] = 'coches'
    speeds: Literal['uniforme', 'variable', 'exceso'] = 'uniforme'
    emissions: bool = True


TIPOS = {
    'coche': dict(vClass='passenger', length='5', width='1.8', accel='2.6', decel='4.5',
                  minGap='2.5', maxSpeed='25', emissionClass='HBEFA4/PC_petrol_Euro-4'),
    'moto': dict(vClass='motorcycle', length='2.2', width='.9', accel='3', decel='4.5',
                 minGap='2.5', maxSpeed='25', emissionClass='HBEFA4/MC_4S_gt250cc_preEuro'),
    'bicicleta': dict(vClass='bicycle', length='1.6', width='.65', accel='1.2', decel='3',
                      minGap='.5', maxSpeed='5.56', desiredMaxSpeed='5.56', emissionClass='zero'),
    'patinete': dict(vClass='scooter', length='1.2', width='.5', accel='1.2', decel='3',
                     minGap='.5', maxSpeed='6.94', desiredMaxSpeed='6.94', emissionClass='zero'),
}


def sorteo(seed, clave):
    return int.from_bytes(sha256(f'{seed}:{clave}'.encode()).digest()[:8], 'big') / 2**64


def configurar_flota(directory, config, seed, location):
    """Conserva llegadas y giros; asigna tipos con un sorteo independiente."""
    if config.speeds == 'exceso' and location != 'laboratorio':
        raise ValueError('El ensayo de 70 km/h solo está disponible en el laboratorio.')
    ruta = directory / 'demanda.rou.xml'
    root = ET.parse(ruta).getroot()
    for tipo in list(root.findall('vType')):
        root.remove(tipo)
    for nombre, atributos in reversed(list(TIPOS.items())):
        root.insert(0, ET.Element('vType', id=nombre, carFollowModel='Krauss', sigma='0',
                                 tau='1', emergencyDecel='9', speedFactor='1', speedDev='0', **atributos))
    filas = []
    for vehiculo in root.findall('vehicle'):
        identificador = vehiculo.get('id')
        valor = sorteo(seed, 'tipo:' + identificador)
        tipo = 'coche' if config.fleet == 'coches' or valor < .7 else (
            'moto' if valor < .8 else 'bicicleta' if valor < .9 else 'patinete')
        factor = 1.0
        if tipo in ('coche', 'moto') and config.speeds != 'uniforme':
            valor = sorteo(seed, 'velocidad:' + identificador)
            factor = .6 if valor < .3 else (1.4 if config.speeds == 'exceso' and valor >= .8 else 1.0)
        vehiculo.set('type', tipo)
        vehiculo.set('speedFactor', str(factor))
        filas.append({'id': identificador, 'tipo': tipo, 'factor_velocidad': factor})
    write_xml(root, ruta)
    with (directory / 'flota.csv').open('w', newline='', encoding='utf-8') as archivo:
        tabla = csv.DictWriter(archivo, fieldnames=['id', 'tipo', 'factor_velocidad'])
        tabla.writeheader()
        tabla.writerows(filas)


def resumen_emisiones(directory, vehicles, warmup, horizon):
    """CO2 de escape por viaje; no incluye energía eléctrica ni ciclo de vida."""
    cohorte = {v['id'] for v in vehicles if warmup <= v['scheduled'] < horizon}
    cantidades = []
    por_tipo = {}
    for viaje in ET.parse(directory / 'tripinfo.xml').getroot().findall('tripinfo'):
        if viaje.get('id') not in cohorte or float(viaje.get('arrival')) < 0:
            continue
        emisiones = viaje.find('emissions')
        if emisiones is None:
            raise RuntimeError('Falta la salida de emisiones de SUMO.')
        gramos = float(emisiones.get('CO2_abs')) / 1000
        cantidades.append(gramos)
        tipo = viaje.get('vType')
        por_tipo[tipo] = por_tipo.get(tipo, 0) + gramos
    return {'co2_cohort_g': sum(cantidades),
            'co2_mean_g': sum(cantidades) / len(cantidades) if cantidades else None,
            'co2_by_type_g': por_tipo, 'co2_scope': 'escape_en_red_HBEFA4'}
