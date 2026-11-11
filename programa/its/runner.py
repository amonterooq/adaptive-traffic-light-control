import csv
import hashlib
import json
import platform
import subprocess
import time
import uuid
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean
import traci
from .config import ARMS, Timing
from .controller import Controller, Observation
from .demand import generate, save
from .network import binary, build_network, write_xml, native_path
from . import pedestrians as ped
from .scene import SceneCollector
from .locations import network_directory, build_geographic, save_turning_demand, signal_states, geographic
from .rotonda import ControlRotonda, guardar_rutas, prioridades_vehiculares
from .cooperative import CooperativeSensing, SensingConfig
from .camaras import Camaras, CameraConfig
from .trafico import TrafficConfig, configurar_flota, resumen_emisiones


def percentile(values, q):
    if not values:return None
    values=sorted(values)
    pos=(len(values)-1)*q
    lo=int(pos)
    return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(pos-lo)


def summarize(directory, vehicles, rows, warmup, horizon, metadata):
    planned={v['id']:v for v in vehicles}
    trips=[]
    for element in ET.parse(directory/'tripinfo.xml').getroot().findall('tripinfo'):
        a=element.attrib; v=planned[a['id']]
        if float(a['arrival']) < 0:continue
        wait=float(a['waitingTime']); depart_delay=float(a['departDelay'])
        trips.append({'id':a['id'],'arm':v['arm'],'scheduled':v['scheduled'],
                      'depart':float(a['depart']),'arrival':float(a['arrival']),
                      'waiting_s':wait,'depart_delay_s':depart_delay,'total_wait_s':wait+depart_delay,
                      'travel_s':float(a['duration'])+depart_delay,
                      'time_loss_s':float(a['timeLoss']),'stops':int(a['waitingCount']),
                      'cohort':int(warmup<=v['scheduled']<horizon)})
    keys=['id','arm','scheduled','depart','arrival','waiting_s','depart_delay_s','total_wait_s','travel_s','time_loss_s','stops','cohort']
    with (directory/'vehiculos.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(trips)
    cohort=[v for v in trips if v['cohort']]
    obs=[r for r in rows if warmup<=r['t']<horizon]
    expected=sum(warmup<=v['scheduled']<horizon for v in vehicles)
    valid=len(cohort)==expected and len(trips)==len(vehicles)
    metrics={**metadata,'completed':valid,'generated':len(vehicles),'arrived':len(trips),
             'cohort_expected':expected,'cohort_arrived':len(cohort),
             'mean_wait_s':mean(v['total_wait_s'] for v in cohort) if cohort else None,
             'mean_stopped_s':mean(v['waiting_s'] for v in cohort) if cohort else None,
             'mean_insert_delay_s':mean(v['depart_delay_s'] for v in cohort) if cohort else None,
             'p95_wait_s':percentile([v['total_wait_s'] for v in cohort],.95),
             'mean_travel_s':mean(v['travel_s'] for v in cohort) if cohort else None,
             'mean_stops':mean(v['stops'] for v in cohort) if cohort else None,
             'mean_queue':mean(r['queue_total'] for r in obs) if obs else None,
             'max_queue':max((r['queue_total'] for r in obs),default=0),
             'throughput_vph':sum(warmup<=v['arrival']<horizon for v in trips)*3600/(horizon-warmup),
             'teleports':sum(r['teleports'] for r in rows),'collisions':sum(r['collisions'] for r in rows),
             'fallback_seconds':sum(r['fallback'] for r in rows),
             'end_time':rows[-1]['t']+1 if rows else 0}
    for arm in ARMS:
        arm_trips=[v['total_wait_s'] for v in cohort if v['arm']==arm]
        metrics[f'wait_{arm}_s']=mean(arm_trips) if arm_trips else None
    if metrics['teleports'] or metrics['collisions']:metrics['completed']=False
    (directory/'resumen.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    return metrics


def run(scenario, mode, seed, directory, horizon=1800, warmup=300, max_drain=1800,
        timing=None, blackout=None, on_step=None, should_stop=None, pace=0,
        pedestrian_profile='desactivado', on_frame=None, playback=None, location='laboratorio', sensing=None,
        traffic=None, camera=None):
    directory=Path(directory).resolve()
    if horizon<=warmup:raise ValueError('La duración debe superar el calentamiento')
    timing=timing or Timing()
    sensing=sensing or SensingConfig()
    traffic=traffic or TrafficConfig()
    camera=camera or CameraConfig()
    if traffic.speeds=='exceso' and location!='laboratorio':
        raise ValueError('El ensayo de 70 km/h solo está disponible en el laboratorio.')
    camaras=Camaras(camera,seed) if camera.enabled else None
    cooperative=CooperativeSensing(sensing,seed) if sensing.mode=='hybrid' else None
    enabled=pedestrian_profile != 'desactivado'
    net=network_directory(location,enabled)
    if not (net/'red.net.xml').exists():
        if location!='laboratorio':build_geographic(location,enabled)
        else:build_network(net, pedestrians=enabled)
    vehicles=generate(scenario,seed,horizon); save(vehicles,directory,pedestrians=enabled)
    if location=='santa_eulalia':guardar_rutas(vehicles,directory,seed,geographic(location))
    elif location!='laboratorio':save_turning_demand(vehicles,directory,seed)
    configurar_flota(directory,traffic,seed,location)
    persons=ped.generate(pedestrian_profile,seed,horizon) if enabled else []
    if enabled:ped.save(persons,directory)
    route_names=['demanda.rou.xml']+(['peatones.rou.xml'] if enabled else [])
    demand_hash=hashlib.sha256((directory/'demanda.csv').read_bytes()).hexdigest()
    cfg=ET.Element('configuration'); inp=ET.SubElement(cfg,'input')
    ET.SubElement(inp,'net-file',value=os.path.relpath(net/'red.net.xml',directory).replace('\\','/'))
    ET.SubElement(inp,'route-files',value=','.join(route_names))
    ET.SubElement(inp,'additional-files',value=os.path.relpath(net/'detectores.add.xml',directory).replace('\\','/'))
    write_xml(cfg,directory/'ejecucion.sumocfg')
    # Keep the saved config portable, but override paths for Windows SUMO when
    # an output folder outside the project would put Unicode in relative paths.
    cmd=[binary('sumo'),'-c',native_path(directory/'ejecucion.sumocfg'),
         '--net-file',native_path(net/'red.net.xml'),
         '--route-files',','.join(native_path(directory/name) for name in route_names),
         '--additional-files',native_path(net/'detectores.add.xml'),'--seed',str(seed),
         '--xml-validation','never',
         '--step-length','1','--no-step-log','true','--duration-log.disable','true',
         '--time-to-teleport','-1','--collision.action','warn',
         '--tripinfo-output',native_path(directory/'tripinfo.xml'),'--tripinfo-output.write-unfinished','true',
         '--error-log',native_path(directory/'sumo.log')]
    if traffic.emissions:cmd += ['--device.emissions.probability','1']
    if enabled:
        cmd += ['--pedestrian.model','striping','--pedestrian.striping.dawdling','0',
                '--pedestrian.striping.jamtime','100000','--pedestrian.striping.jamtime.crossing','100000',
                '--pedestrian.striping.jamtime.narrow','100000','--collision.check-junctions','true']
    elif location!='laboratorio':cmd += ['--collision.check-junctions','true']
    label=uuid.uuid4().hex
    version=subprocess.check_output([binary('sumo'),'--version'],text=True).splitlines()[0]
    traci.start(cmd,label=label,doSwitch=False,stdout=subprocess.DEVNULL)
    conn=traci.getConnection(label)
    controller=ped.PedestrianController(mode,timing) if enabled else Controller(mode,timing)
    if location=='santa_eulalia':controller=ControlRotonda(mode,timing)
    monitor=ped.Monitor(conn,persons,rotonda=location=='santa_eulalia') if enabled else None
    scene=SceneCollector() if on_frame else None
    # Verify the signal-to-movement map instead of assuming netconvert retained indices.
    links=conn.trafficlight.getControlledLinks('J1')
    link_arms=[link[0][0].split('_')[0] if link[0][0][0]!=':' else None for link in links]
    if location=='laboratorio' and (sorted(a for a in link_arms if a is not None)!=sorted(ARMS) or len(links)!=(8 if enabled else 4)):
        conn.close();raise RuntimeError('Mapa semafórico incompatible con cuatro movimientos rectos')
    templates={}
    prioridad_rotonda=prioridades_vehiculares(net,links) if location=='santa_eulalia' else None
    if location not in ('laboratorio','santa_eulalia'):
        for axis in (('N','S'),('E','W')):
            template=next((p for p in signal_states(net)
                if {a for a,s in zip(link_arms,p) if a and s in 'Gg'}==set(axis)),None)
            if template is None or len(template)!=len(links):
                conn.close();raise RuntimeError('El plan de SUMO no contiene los dos ejes esperados')
            templates[axis[0]]=template
    detector_ids=conn.lanearea.getIDList()
    detector_groups={a:[d for d in detector_ids if d==f'det_{a}' or d.startswith(f'det_{a}_')] for a in ARMS}
    for detectors in detector_groups.values():
        for detector in detectors:conn.lanearea.subscribe(detector,[traci.constants.LAST_STEP_VEHICLE_HALTING_NUMBER])
    rows=[]; collision_events=[]; started=time.perf_counter();cancelled=False
    try:
        for t in range(horizon+max_drain):
            if playback:playback()
            if should_stop and should_stop():cancelled=True;break
            # Subscription results describe the state at the current simulation boundary.
            queues=tuple(sum(int((conn.lanearea.getSubscriptionResults(d) or {}).get(
                traci.constants.LAST_STEP_VEHICLE_HALTING_NUMBER,0)) for d in detector_groups[a]) for a in ARMS)
            approaching=(0,0,0,0);telemetry={}
            if cooperative:approaching,telemetry=cooperative.collect(conn,t,detector_groups)
            if camaras:
                telemetry.update(camaras.collect(conn,t))
                stopped={v for group in detector_groups.values() for d in group
                         for v in conn.lanearea.getLastStepVehicleIDs(d) if conn.vehicle.getSpeed(v)<.1}
                approaching,fusion=camaras.fusionar(t,cooperative,stopped)
                telemetry.update(fusion)
            if not blackout or not blackout[0]<=t<blackout[1]:
                controller.observe(Observation(t,queues,approaching),t)
            waiting=occupied=internal_vehicles=0
            if enabled:
                waiting,occupied,internal_vehicles=monitor.observe(conn,t)
                controller.pedestrians(t,waiting,occupied,internal_vehicles)
            signals=controller.update(t)
            if location=='santa_eulalia' and not enabled:
                controller.stage='green';controller.since=0;controller.reason='prioridad_anillo';signals='GGGG'
            ped_signal='G' if enabled and controller.stage=='walk' else 'r'
            applied=''.join(signals[ARMS.index(a)] if a is not None else ped_signal for a in link_arms)
            if location=='santa_eulalia':
                if not enabled:signals='GGGG'
                # G tiene prioridad; g conserva la cesión calculada al construir la red.
                applied=''.join((prioridad_rotonda[i] if signals[0]=='G' else signals[0])
                    if a is not None else ped_signal for i,a in enumerate(link_arms))
            elif location!='laboratorio' and 'G' in signals:
                template=templates['N' if signals[0]=='G' else 'E']
                applied=''.join(template[i] if a else ped_signal for i,a in enumerate(link_arms))
            conn.trafficlight.setRedYellowGreenState('J1',applied)
            conn.simulationStep()
            for evento in conn.simulation.getCollisions():
                collision_events.append({'t':t+1,'collider':evento.collider,'victim':evento.victim,
                    'lane':evento.lane,'position_m':evento.pos,'type':evento.type,
                    'collider_speed_m_s':evento.colliderSpeed,'victim_speed_m_s':evento.victimSpeed})
            row={'t':t,**{f'q_{a}':q for a,q in zip(ARMS,queues)},'queue_total':sum(queues),
                 'state':signals,'fallback':int(controller.fallback),'sample_age':controller.snapshot(t)['sample_age'],
                 'departed':conn.simulation.getDepartedNumber(),'arrived':conn.simulation.getArrivedNumber(),
                 'in_network':conn.vehicle.getIDCount(),'pending':conn.simulation.getMinExpectedNumber(),
                 'teleports':conn.simulation.getStartingTeleportNumber(),'collisions':conn.simulation.getCollidingVehiclesNumber()}
            if enabled:
                row.update(ped_signal=ped_signal,ped_waiting=waiting,ped_crossing=occupied,
                           vehicles_crossing=internal_vehicles,ped_stage=controller.stage,
                           ped_arrived=conn.simulation.getArrivedPersonNumber(),
                           ped_conflict=int((ped_signal=='G' and (signals!='rrrr' or internal_vehicles>0)) or (occupied>0 and 'G' in signals)))
            if location!='laboratorio':row.update(tls_state=applied,location=location)
            if cooperative:
                row.update(telemetry,sensing_mode='hybrid',
                           v2x_used=int(not blackout or not blackout[0]<=t<blackout[1]))
                if enabled:row.update({f'ped_wait_{a}':monitor.waiting_by_arm[a] for a in ARMS})
            if camaras:
                row.update(telemetry,sensing_mode=sensing.mode,
                           camera_used=int(not blackout or not blackout[0]<=t<blackout[1]))
                if enabled:row.update({f'ped_wait_{a}':monitor.waiting_by_arm[a] for a in ARMS})
            rows.append(row)
            if on_step or on_frame:
                sample={**row,**controller.snapshot(t),'scenario':scenario,'mode':mode,'seed':seed,
                         'horizon':horizon,'warmup':warmup,'draining':t>=horizon,
                         'arrived_total':sum(r['arrived'] for r in rows)}
                if on_step:on_step(sample)
                if on_frame:on_frame(scene.collect(conn,sample,cooperative))
            if t>=horizon and conn.simulation.getMinExpectedNumber()==0:break
            if pace>0 and not playback:time.sleep(1/pace)
    finally:
        conn.close()
    with (directory/'serie.csv').open('w',newline='',encoding='utf-8') as f:
        keys=list(rows[0]) if rows else ['t']
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    metadata={'scenario':scenario,'mode':mode,'seed':seed,'horizon':horizon,'warmup':warmup,
              'max_drain':max_drain,'timing':timing.model_dump(),'blackout':blackout,
              'demand_sha256':demand_hash,'sumo_version':version,'python':platform.python_version(),
              'wall_seconds':round(time.perf_counter()-started,3),'cancelled':cancelled,
              'collision_events':collision_events}
    if enabled:
        metadata.update(pedestrian_profile=pedestrian_profile,
                        pedestrian_demand_sha256=hashlib.sha256((directory/'demanda_peatones.csv').read_bytes()).hexdigest(),
                        pedestrian_timing={'walk':ped.WALK_SECONDS,'clear':ped.CLEAR_SECONDS,'request_trigger':ped.REQUEST_SECONDS})
    if location!='laboratorio':metadata.update(location=location,turns_sha256=hashlib.sha256((directory/'giros.csv').read_bytes()).hexdigest())
    if cooperative:metadata.update(sensing=sensing.model_dump(),v2x_protocol='application_emulation',
        v2x_sent=cooperative.sent,v2x_received=cooperative.received,v2x_lost=cooperative.lost,
        v2x_expired=cooperative.expired,v2x_ttl_s=cooperative.ttl,v2x_anticipation_s=cooperative.anticipation)
    metadata.update(traffic=traffic.model_dump(),fleet_sha256=hashlib.sha256((directory/'flota.csv').read_bytes()).hexdigest(),
                    model_version='1.6.0')
    if camaras:metadata.update(camera=camera.model_dump())
    if traffic.emissions:metadata.update(resumen_emisiones(directory,vehicles,warmup,horizon))
    metrics=summarize(directory,vehicles,rows,warmup,horizon,metadata)
    if enabled:
        metrics.update(ped.summarize(directory,persons,monitor,warmup,horizon))
        metrics['ped_conflicts']=sum(r['ped_conflict'] for r in rows)
        metrics['ped_phase_seconds']=sum(r['ped_stage'] in ('walk','ped_clear') for r in rows)
        metrics['completed']=metrics['completed'] and metrics['ped_completed'] and metrics['ped_conflicts']==0
        (directory/'resumen.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    if cancelled:
        metrics['completed']=False
        (directory/'resumen.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    return metrics
