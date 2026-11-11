"""Salida de cámaras emulada desde SUMO, sin procesar imágenes reales."""
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field
from .config import ARMS
from .trafico import sorteo, TIPOS


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool = False
    range_m: int = Field(default=80, ge=20, le=150)
    missed_percent: int = Field(default=0, ge=0, le=100)
    unclassified_percent: int = Field(default=0, ge=0, le=100)


@dataclass(frozen=True)
class Deteccion:
    id: str
    arm: str
    distance: float
    speed: float
    tipo: str


class Camaras:
    def __init__(self, config, seed):
        self.config = config
        self.seed = seed
        self.detecciones = {}
        self.longitudes = {}

    def observar(self, now, candidatos):
        self.detecciones = {}
        conteos = dict.fromkeys([*TIPOS, 'desconocido'], 0)
        velocidades = []
        for dato in candidatos:
            if not 0 < dato.distance <= self.config.range_m:
                continue
            if sorteo(self.seed, f'omision:{dato.id}:{now}') * 100 < self.config.missed_percent:
                continue
            tipo = dato.tipo if dato.tipo in TIPOS else 'coche'
            if sorteo(self.seed, f'clasificacion:{dato.id}:{now}') * 100 < self.config.unclassified_percent:
                tipo = 'desconocido'
            self.detecciones[dato.id] = Deteccion(dato.id, dato.arm, dato.distance, dato.speed, tipo)
            conteos[tipo] += 1
            velocidades.append(dato.speed * 3.6)
        return {'camera_active': 1, 'camera_detected': len(self.detecciones),
                'camera_speed_max_kmh': max(velocidades, default=0),
                **{f'camera_{tipo}': n for tipo, n in conteos.items()}}

    def collect(self, conn, now):
        candidatos = []
        for id in conn.vehicle.getIDList():
            edge = conn.vehicle.getRoadID(id)
            if edge not in {a + '_in' for a in ARMS}:
                continue
            lane = conn.vehicle.getLaneID(id)
            if lane not in self.longitudes:
                self.longitudes[lane] = conn.lane.getLength(lane)
            candidatos.append(Deteccion(id, edge[0], self.longitudes[lane] - conn.vehicle.getLanePosition(id),
                                        conn.vehicle.getSpeed(id), conn.vehicle.getTypeID(id)))
        return self.observar(now, candidatos)

    def fusionar(self, now, cooperative, stopped):
        """Una aproximación por vehículo. La cámara actual prima sobre un aviso antiguo."""
        datos = {}
        if cooperative:
            for id, aviso in cooperative.latest.items():
                edad = now - aviso.time
                if 0 <= edad <= cooperative.ttl:
                    datos[id] = Deteccion(id, aviso.arm, aviso.distance - aviso.speed * edad, aviso.speed, '')
        datos.update(self.detecciones)
        proximos = dict.fromkeys(ARMS, 0)
        tiempos = []
        for id, dato in datos.items():
            if id in stopped or dato.distance <= 0 or dato.speed < 1:
                continue
            llegada = dato.distance / dato.speed
            tiempos.append(llegada)
            if llegada <= 8:
                proximos[dato.arm] += 1
        return tuple(proximos.values()), {'fusion_approaching': sum(proximos.values()),
                'fusion_eta_min': min(tiempos) if tiempos else None,
                **{f'fusion_{a}': n for a, n in proximos.items()}}
