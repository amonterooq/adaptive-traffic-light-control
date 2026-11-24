"""Turnos por entrada y pasos peatonales compatibles en Lusitania."""
from .config import ARMS
from .pedestrians import PedestrianController, WALK_SECONDS, CLEAR_SECONDS

PLAN = 'lusitania_movimientos_v3'
VERDE_DERECHA = 6


class ControlLusitania(PedestrianController):
    def __init__(self, mode='adaptativo', timing=None, peatones=True):
        super().__init__(mode, timing)
        self.peatones = peatones
        self.peticiones = {}
        self.paso = None
        self.ocupados = {}
        self.compatibles = {}
        self.derecha = None
        self.etapa_derecha = 'off'
        self.desde_derecha = 0
        self.rutas_dentro = set()

    def detectar_pasos(self, now, esperando, ocupados):
        self.ocupados = ocupados
        for paso, cantidad in esperando.items():
            if cantidad and not (self.stage == 'walk' and paso == self.paso):
                self.peticiones.setdefault(paso, now)

    def siguiente(self, now):
        self.axis = (self.axis + 1) % len(ARMS)
        self.derecha, self.etapa_derecha = None, 'off'
        entrada = ARMS[self.axis]
        candidatos = [p for p in self.peticiones if self.compatibles.get((entrada, p))]
        self.paso = min(candidatos, key=lambda p: (self.peticiones[p], p)) if candidatos and self.peatones else None
        self.stage = 'walk' if self.paso else 'green'
        self.since, self.reason = now, 'paso_compatible' if self.paso else 'entrada_siguiente'
        if self.paso:
            del self.peticiones[self.paso]

    def update(self, now):
        elapsed = self.advance_clock(now)
        p = self.timing
        if self.stage == 'walk':
            if elapsed >= WALK_SECONDS:
                self.stage, self.since, self.reason = 'ped_clear', now, 'despeje_peatonal'
        elif self.stage == 'ped_clear':
            if elapsed >= CLEAR_SECONDS and not any(self.ocupados.values()):
                self.stage, self.since, self.reason = 'green', now, 'cruce_despejado'
                self.paso = None
        elif self.stage == 'red':
            if elapsed >= p.all_red:
                # También se espera a los giros lentos antes de abrir otra entrada.
                if self.vehicles_crossing or self.occupied:
                    self.reason = 'espera_despeje_vehicular'
                else:
                    self.siguiente(now)
        elif self.stage == 'yellow':
            if elapsed >= p.yellow:
                self.stage, self.since, self.reason = 'red', now, 'despeje'
        elif self.stage == 'green':
            if self.mode == 'fijo' or self.fallback:
                switch = elapsed >= p.fixed_green
                reason = 'respaldo_temporizado' if self.fallback else 'temporizacion_fija'
            else:
                q = self.observation.demand
                other = max(q[i] for i in range(len(ARMS)) if i != self.axis)
                switch = elapsed >= p.max_green or (elapsed >= p.min_green and other > 0 and
                    (q[self.axis] == 0 or other >= q[self.axis] + p.hysteresis))
                reason = 'verde_maximo' if elapsed >= p.max_green else 'demanda_otras_entradas'
            if self.peatones and self.mode == 'adaptativo' and self.peticiones and elapsed >= p.min_green:
                switch, reason = True, 'solicitud_peatonal'
            if switch:
                self.stage, self.since, self.reason = 'yellow', now, reason
        self.actualizar_derecha(now)
        return self.state()

    def actualizar_derecha(self, now):
        if ARMS[self.axis]!='E':return
        age=now-self.desde_derecha
        if self.etapa_derecha=='off' and self.stage=='green':
            self.derecha,self.etapa_derecha,self.desde_derecha='S','green',now
        elif self.etapa_derecha=='green' and (age>=VERDE_DERECHA or self.stage!='green'):
            self.etapa_derecha,self.desde_derecha='yellow',now
        elif self.etapa_derecha=='yellow' and age>=self.timing.yellow:
            self.etapa_derecha,self.desde_derecha='clear',now
        elif self.etapa_derecha=='clear' and age>=self.timing.all_red:
            destination='E' if self.derecha=='S' else 'W'
            if (self.derecha,destination) not in self.rutas_dentro:
                if self.derecha=='S' and self.stage=='green':
                    self.derecha,self.etapa_derecha,self.desde_derecha='N','green',now
                else:self.etapa_derecha='done'

    def senal_derecha(self):
        if self.stage not in ('green','yellow'):return 'r'
        if self.etapa_derecha=='green':return 'g' if self.derecha=='N' else 'G'
        return 'y' if self.etapa_derecha=='yellow' else 'r'

    def state(self):
        signals = ['r'] * len(ARMS)
        if self.stage in ('green', 'walk', 'ped_clear', 'yellow'):
            signals[self.axis] = 'y' if self.stage == 'yellow' else 'G'
        return ''.join(signals)

    def snapshot(self, now):
        return {**super().snapshot(now), 'axis': ARMS[self.axis], 'signal_plan': PLAN,
                'right_turn_arm':self.derecha or '', 'right_turn_signal':self.senal_derecha(),
                'ped_request_age': now-min(self.peticiones.values()) if self.peticiones else 0}
