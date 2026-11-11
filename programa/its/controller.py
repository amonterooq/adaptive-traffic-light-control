"""Máquina de estados común a los experimentos y al panel web.

Cada llamada decide el estado del intervalo [t, t+1). La transición siempre
recorre verde -> amarillo -> todo-rojo -> verde del eje opuesto.
"""
from dataclasses import dataclass
from .config import Timing


@dataclass(frozen=True)
class Observation:
    time: int
    queues: tuple[int, int, int, int]
    approaching: tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def demand(self):
        return tuple(q+a for q,a in zip(self.queues,self.approaching))


class Controller:
    def __init__(self, mode='adaptativo', timing=None):
        if mode not in ('fijo', 'adaptativo'):
            raise ValueError('Modo de control desconocido')
        self.mode = mode
        self.timing = timing or Timing()
        self.axis = 0  # 0: N/S, 1: E/W
        self.stage = 'green'
        self.since = 0
        self.last_time = -1
        self.observation = None
        self.fallback = False
        self.reason = 'inicio'

    def observe(self, obs, now):
        if not isinstance(obs, Observation):
            raise ValueError('Observación inválida')
        if type(obs.time) is not int or obs.time > now or obs.time < 0:
            raise ValueError('Marca de tiempo inválida')
        if len(obs.queues) != 4 or any(type(q) is not int or q < 0 for q in obs.queues):
            raise ValueError('Las colas deben contener cuatro enteros no negativos')
        if len(obs.approaching) != 4 or any(type(q) is not int or q < 0 for q in obs.approaching):
            raise ValueError('Las aproximaciones deben contener cuatro enteros no negativos')
        if self.observation is not None and obs.time <= self.observation.time:
            raise ValueError('Muestra duplicada o fuera de orden')
        self.observation = obs

    def advance_clock(self, now):
        if type(now) is not int or now < 0 or (self.last_time >= 0 and now != self.last_time + 1):
            raise ValueError('El controlador requiere pasos consecutivos de un segundo')
        self.last_time = now
        p = self.timing
        age = None if self.observation is None else now - self.observation.time
        self.fallback = self.mode == 'adaptativo' and (age is None or age > p.stale_after)
        return now - self.since

    def update(self, now):
        elapsed = self.advance_clock(now)
        p = self.timing
        if self.stage == 'yellow' and elapsed >= p.yellow:
            self.stage, self.since, self.reason = 'red', now, 'despeje'
        elif self.stage == 'red' and elapsed >= p.all_red:
            self.axis = 1 - self.axis
            self.stage, self.since, self.reason = 'green', now, 'eje_alterno'
        elif self.stage == 'green':
            switch = False
            if self.mode == 'fijo' or self.fallback:
                switch = elapsed >= p.fixed_green
                reason = 'respaldo_temporizado' if self.fallback else 'temporizacion_fija'
            else:
                q = self.observation.demand
                current = q[self.axis] + q[self.axis + 2]
                other = q[1-self.axis] + q[3-self.axis]
                switch = elapsed >= p.max_green or (
                    elapsed >= p.min_green and other > 0 and
                    (current == 0 or other >= current + p.hysteresis)
                )
                reason = 'verde_maximo' if elapsed >= p.max_green else 'demanda_opuesta'
            if switch:
                self.stage, self.since, self.reason = 'yellow', now, reason
        return self.state()

    def state(self):
        signals = ['r'] * 4
        if self.stage != 'red':
            color = 'G' if self.stage == 'green' else 'y'
            signals[self.axis] = signals[self.axis + 2] = color
        return ''.join(signals)

    def snapshot(self, now):
        return {'state': self.state(), 'axis': 'NS' if self.axis == 0 else 'EW',
                'stage': self.stage, 'elapsed': now-self.since, 'fallback': self.fallback,
                'reason': self.reason, 'sample_age': None if self.observation is None else now-self.observation.time}
