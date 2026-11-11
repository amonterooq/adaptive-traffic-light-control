"""Cruces reales SUMO y fase peatonal exclusiva; parámetros experimentales."""
import csv
import random
import xml.etree.ElementTree as ET
from statistics import mean
from .controller import Controller
from .config import ARMS
from .network import write_xml

WALK_SECONDS = 10
CLEAR_SECONDS = 15
REQUEST_SECONDS = 45  # trigger for ending vehicle green, not a person's delay bound
PROFILES = {'sin': 0, 'ocasional': 30, 'frecuente': 180, 'lento': 180, 'escolar': 720}


class PedestrianController(Controller):
    def __init__(self, mode='adaptativo', timing=None):
        super().__init__(mode, timing)
        self.request_since = None
        self.waiting = self.occupied = self.vehicles_crossing = 0

    def pedestrians(self, now, waiting, occupied, vehicles_crossing):
        if any(type(x) is not int or x < 0 for x in (now, waiting, occupied, vehicles_crossing)):
            raise ValueError('Detección peatonal inválida')
        self.waiting, self.occupied, self.vehicles_crossing = waiting, occupied, vehicles_crossing
        if waiting and self.stage != 'walk' and self.request_since is None:
            self.request_since = now

    def update(self, now):
        elapsed = now - self.since
        if self.stage in ('walk', 'ped_clear', 'red'):
            self.advance_clock(now)
            if self.stage == 'walk' and elapsed >= WALK_SECONDS:
                self.stage, self.since, self.reason = 'ped_clear', now, 'despeje_peatonal'
            elif self.stage == 'ped_clear' and elapsed >= CLEAR_SECONDS and not self.occupied:
                self.axis = 1-self.axis
                self.stage, self.since, self.reason = 'green', now, 'cruce_despejado'
            elif self.stage == 'red' and elapsed >= self.timing.all_red:
                age = 0 if self.request_since is None else now-self.request_since
                empty = self.observation is not None and not self.fallback and sum(self.observation.queues)==0
                serve = (self.axis == 1) if self.mode == 'fijo' else (
                    self.request_since is not None and (self.axis == 1 or age >= REQUEST_SECONDS or empty))
                if serve:
                    if not self.vehicles_crossing:
                        self.stage, self.since, self.reason = 'walk', now, 'servicio_peatonal'
                        self.request_since = None
                    else:
                        self.reason = 'espera_despeje_vehicular'
                else:
                    self.axis = 1-self.axis
                    self.stage, self.since, self.reason = 'green', now, 'eje_alterno'
        else:
            super().update(now)
            if (self.mode == 'adaptativo' and self.stage == 'green'
                    and self.request_since is not None and elapsed >= self.timing.min_green):
                q = self.observation.queues if self.observation else (0,0,0,0)
                if now-self.request_since >= REQUEST_SECONDS or (not self.fallback and sum(q) == 0):
                    self.stage, self.since, self.reason = 'yellow', now, 'solicitud_peatonal'
        return self.state()

    def state(self):
        return 'rrrr' if self.stage in ('walk','ped_clear') else super().state()

    def snapshot(self, now):
        return {**super().snapshot(now), 'ped_signal': 'G' if self.stage == 'walk' else 'r',
                'ped_waiting': self.waiting, 'ped_crossing': self.occupied,
                'ped_request_age': 0 if self.request_since is None else now-self.request_since}


def generate(profile, seed, horizon):
    if profile not in PROFILES:
        raise ValueError('Perfil peatonal desconocido')
    rng = random.Random(seed + 1000003)  # independent of vehicle demand
    persons = []
    for arm in ARMS:
        t = horizon/3 if profile == 'escolar' else 0
        end = 2*horizon/3 if profile == 'escolar' else horizon
        rate = (720 if arm in ('N','S') else 120) if profile == 'escolar' else PROFILES[profile]
        while PROFILES[profile]:
            t += rng.expovariate(rate/3600)
            if t >= end:
                break
            persons.append({'arm':arm, 'scheduled':round(t,3), 'speed':0.8 if profile == 'lento' else 1.4})
    persons.sort(key=lambda p:(p['scheduled'],p['arm']))
    for i,p in enumerate(persons):
        p['id'] = f'ped_{i:05d}'
    return persons


def save(persons, directory):
    root = ET.Element('routes')
    ET.SubElement(root,'vType',id='walker',vClass='pedestrian',speedFactor='1',speedDev='0',
                  jmIgnoreFoeProb='0',jmIgnoreJunctionFoeProb='0')
    for p in persons:
        person = ET.SubElement(root,'person',id=p['id'],type='walker',depart=str(p['scheduled']),departPos='-12')
        ET.SubElement(person,'walk',edges=f"{p['arm']}_in {p['arm']}_out",arrivalPos='12',speed=str(p['speed']))
    write_xml(root,directory/'peatones.rou.xml')
    with (directory/'demanda_peatones.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['id','arm','scheduled','speed'])
        writer.writeheader();writer.writerows(persons)


class Monitor:
    def __init__(self, conn, persons=(), rotonda=False):
        net_edges = conn.edge.getIDList()
        self.internal_prefix=':G_' if rotonda else ':J1_'
        self.crossings = {e for e in net_edges if e.startswith(self.internal_prefix) and '_c' in e}
        self.walkingareas = {e for e in net_edges if e.startswith(self.internal_prefix) and '_w' in e}
        self.requests = {}
        self.entered = {}
        self.arm_by_person={p['id']:p['arm'] for p in persons}
        self.waiting_by_arm={a:0 for a in ARMS}

    def observe(self, conn, now):
        waiting = occupied = 0
        self.waiting_by_arm={a:0 for a in ARMS}
        for pid in conn.person.getIDList():
            edge = conn.person.getRoadID(pid)
            if edge in self.crossings:
                occupied += 1
                self.entered.setdefault(pid, now)
            elif edge in self.walkingareas and conn.person.getNextEdge(pid) in self.crossings and conn.person.getWaitingTime(pid) > 0:
                waiting += 1
                self.requests.setdefault(pid,now)
                arm=self.arm_by_person.get(pid)
                if arm:self.waiting_by_arm[arm]+=1
        vehicles = sum(conn.vehicle.getRoadID(v).startswith(self.internal_prefix) for v in conn.vehicle.getIDList())
        return waiting, occupied, vehicles


def summarize(directory, persons, monitor, warmup, horizon):
    planned={p['id']:p for p in persons}
    rows=[]
    for person in ET.parse(directory/'tripinfo.xml').getroot().findall('personinfo'):
        p=planned[person.attrib['id']]
        walk=person.find('walk')
        if walk is None or float(walk.attrib['arrival']) < 0:
            continue
        request=monitor.requests.get(p['id'])
        entry=monitor.entered.get(p['id'])
        rows.append({**p,'arrival':float(walk.attrib['arrival']),
                     'waiting_s':float(walk.attrib['waitingTime']),
                     'duration_s':float(walk.attrib['duration']),
                     'request_t':request, 'crossing_t':entry,
                     'request_wait_s':None if request is None or entry is None else entry-request,
                     'cohort':int(warmup <= p['scheduled'] < horizon)})
    with (directory/'peatones.csv').open('w',newline='',encoding='utf-8') as f:
        keys=['id','arm','scheduled','speed','arrival','waiting_s','duration_s','request_t','crossing_t','request_wait_s','cohort']
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    cohort=[p for p in rows if p['cohort']]
    waits=[p['waiting_s'] for p in cohort]
    requests=[p['request_wait_s'] for p in cohort if p['request_wait_s'] is not None]
    return {'ped_generated':len(persons),'ped_arrived':len(rows),
            'ped_cohort_expected':sum(warmup<=p['scheduled']<horizon for p in persons),
            'ped_cohort_arrived':len(cohort), 'ped_crossed':len(monitor.entered),
            'ped_mean_wait_s':mean(waits) if waits else None,
            'ped_max_wait_s':max(waits,default=0),
            'ped_mean_request_wait_s':mean(requests) if requests else None,
            'ped_max_request_wait_s':max(requests,default=0),
            'ped_completed':len(rows)==len(persons)==len(monitor.entered)}
