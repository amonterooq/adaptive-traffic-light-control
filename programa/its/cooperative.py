"""Application-level V2I emulation; no radio, ASN.1 CAM or real vehicle feed.

Detector queues remain the baseline. Only fresh, moving, approaching vehicles
outside the stopped set can add demand. ETA assumes unchanged speed.
"""
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .config import ARMS


class SensingConfig(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    mode: Literal['sensors','hybrid']='sensors'
    penetration: int=Field(default=50,ge=0,le=100)
    range_m: int=Field(default=120,ge=20,le=300)
    latency_s: int=Field(default=1,ge=0,le=5)
    loss_percent: int=Field(default=0,ge=0,le=100)


@dataclass(frozen=True)
class VehicleReport:
    id: str
    arm: str
    time: int
    distance: float
    speed: float


class CooperativeSensing:
    ttl=3
    anticipation=8

    def __init__(self, config, seed):
        self.config=config
        self.seed=seed
        self.pending=[]
        self.latest={}
        self.fresh_ids=set()
        self.sent=self.received=self.lost=self.expired=0
        self.lane_lengths={}

    def fraction(self, key):
        return int.from_bytes(sha256(f'{self.seed}:{key}'.encode()).digest()[:8],'big')/2**64

    def equipped(self, id):
        return self.fraction('equipment:'+id)*100<self.config.penetration

    def observe(self, now, reports, stopped_ids):
        """Explicit input boundary supports deterministic replay and unit tests."""
        for report in reports:
            if not self.equipped(report.id) or not 0<report.distance<=self.config.range_m:continue
            self.sent+=1
            if self.fraction(f'loss:{report.id}:{now}')*100<self.config.loss_percent:
                self.lost+=1;continue
            self.pending.append((now+self.config.latency_s,report))
        delivered=[r for delivery,r in self.pending if delivery<=now]
        self.pending=[(delivery,r) for delivery,r in self.pending if delivery>now]
        for report in delivered:
            self.received+=1
            previous=self.latest.get(report.id)
            if now-report.time>self.ttl:
                self.expired+=1;continue
            if previous is None or report.time>previous.time:self.latest[report.id]=report
        self.latest={key:r for key,r in self.latest.items() if 0<=now-r.time<=self.ttl}
        upcoming=[0]*4;etas=[];ages=[];self.fresh_ids=set()
        for report in self.latest.values():
            age=now-report.time
            remaining=report.distance-report.speed*age
            if remaining<=0:continue
            self.fresh_ids.add(report.id);ages.append(age)
            if report.id in stopped_ids or report.speed<1:continue
            eta=remaining/report.speed
            etas.append(eta)
            if eta<=self.anticipation:upcoming[ARMS.index(report.arm)]+=1
        telemetry={'v2x_fresh':len(self.fresh_ids),'v2x_eta_min':round(min(etas),2) if etas else None,
                   'v2x_age_max':max(ages) if ages else None,'v2x_sent':self.sent,
                   'v2x_received':self.received,'v2x_lost':self.lost,'v2x_expired':self.expired,
                   'v2x_approaching':sum(upcoming),**{f'v2x_{a}':n for a,n in zip(ARMS,upcoming)}}
        return tuple(upcoming),telemetry

    def collect(self, conn, now, detector_groups):
        reports=[];stopped=set();active_equipped=0
        for detectors in detector_groups.values():
            for detector in detectors:
                stopped.update(v for v in conn.lanearea.getLastStepVehicleIDs(detector) if conn.vehicle.getSpeed(v)<.1)
        for id in conn.vehicle.getIDList():
            if not self.equipped(id):continue
            if conn.vehicle.getTypeID(id) in ('bicicleta','patinete'):continue
            active_equipped+=1
            edge=conn.vehicle.getRoadID(id)
            if edge not in {a+'_in' for a in ARMS}:continue
            lane=conn.vehicle.getLaneID(id)
            if lane not in self.lane_lengths:self.lane_lengths[lane]=conn.lane.getLength(lane)
            distance=max(0,self.lane_lengths[lane]-conn.vehicle.getLanePosition(id))
            reports.append(VehicleReport(id,edge[0],now,distance,conn.vehicle.getSpeed(id)))
        upcoming,telemetry=self.observe(now,reports,stopped)
        telemetry['v2x_equipped_active']=active_equipped
        return upcoming,telemetry
