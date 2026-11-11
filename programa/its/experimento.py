"""Configuración común para las sesiones de la aplicación y los ensayos por lotes."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .config import Timing
from .trafico import TrafficConfig
from .camaras import CameraConfig
from .cooperative import SensingConfig


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    scenario: Literal['bajo', 'medio', 'alto', 'desequilibrado', 'dinamico', 'escolar'] = 'medio'
    mode: Literal['fijo', 'adaptativo'] = 'adaptativo'
    seed: int = Field(default=101, ge=0, le=2147483647)
    horizon: int = Field(default=1800, ge=60, le=1800)
    timing: Timing = Field(default_factory=Timing)
    simulate_outage: bool = False
    outage_start: int = Field(default=60, ge=0, le=1799)
    outage_end: int = Field(default=90, ge=1, le=1800)
    pedestrian_profile: Literal['desactivado', 'sin', 'ocasional', 'frecuente', 'lento', 'escolar'] = 'ocasional'
    location: Literal['laboratorio', 'lusitania', 'santa_eulalia'] = 'laboratorio'
    sensing: SensingConfig = Field(default_factory=SensingConfig)
    traffic: TrafficConfig = Field(default_factory=TrafficConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)

    @model_validator(mode='after')
    def validate_scope(self):
        if self.traffic.speeds == 'exceso' and self.location != 'laboratorio':
            raise ValueError('El ensayo de 70 km/h solo está disponible en el laboratorio.')
        if self.simulate_outage and not self.outage_start < self.outage_end <= self.horizon:
            raise ValueError('La interrupción debe empezar antes de terminar y estar dentro del periodo de llegadas.')
        return self

    def run_kwargs(self):
        return dict(horizon=self.horizon, warmup=min(300, self.horizon // 6), max_drain=1800,
                    timing=self.timing, blackout=(self.outage_start, self.outage_end) if self.simulate_outage else None,
                    pedestrian_profile=self.pedestrian_profile, location=self.location,
                    sensing=self.sensing, traffic=self.traffic, camera=self.camera)
