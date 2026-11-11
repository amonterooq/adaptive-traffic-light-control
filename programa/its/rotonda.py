"""Rotonda escolar con prioridad interior y pasos peatonales coordinados."""
import csv
import random
import subprocess
import xml.etree.ElementTree as ET
from .config import ARMS
from .network import binary, write_xml
from .pedestrians import PedestrianController, WALK_SECONDS, CLEAR_SECONDS, REQUEST_SECONDS


def prioridades_vehiculares(directory, links):
    """Conserva la cesión definida por la red en las convergencias de carriles."""
    root = ET.parse(directory/'red.net.xml').getroot()
    fases = root.find("tlLogic[@id='J1']").findall('phase')
    prioridades = []
    for index, link in enumerate(links):
        if link[0][0].startswith(':'):
            prioridades.append('r')
            continue
        estados = {fase.get('state')[index] for fase in fases}
        if not estados.intersection({'G', 'g'}):
            raise RuntimeError('La red no define prioridad para una conexión vehicular.')
        prioridades.append('g' if 'g' in estados else 'G')
    return ''.join(prioridades)


def construir(directory, source, project, pedestrians):
    directory.mkdir(parents=True, exist_ok=True)
    nodos=ET.Element('nodes');edges=ET.Element('edges');connections=ET.Element('connections')
    offset=int(pedestrians)
    ring=source['ring'];indices={r['id']:i for i,r in enumerate(ring)}
    for i,r in enumerate(ring):
        x,y=project(r['position'])
        ET.SubElement(nodos,'node',id=f'R{i}',x=str(x),y=str(y),type='priority')
        ET.SubElement(edges,'edge',id=f'ring_{i}',attrib={'from':f'R{i}','to':f'R{(i+1)%len(ring)}',
            'priority':'10','numLanes':'1','speed':'5.56','disallow':'pedestrian','width':'4'})
    for a,info in source['arms'].items():
        for id,p in [(a,info['centerline'][-1]),('G_'+a,info['centerline'][1])]:
            x,y=project(p)
            attrs={'id':id,'x':str(x),'y':str(y),'type':'traffic_light' if id.startswith('G_') else 'priority'}
            if id.startswith('G_'):attrs['tl']='J1'
            ET.SubElement(nodos,'node',attrs)
        for suffix,start,end,lanes,sidewalk in [
            ('in',a,'G_'+a,info['lanes_per_direction'],pedestrians),
            ('out','G_'+a,a,info['lanes_per_direction'],pedestrians),
            ('link_in','G_'+a,'R'+str(indices[info['ring_in']]),1,pedestrians),
            ('link_out','R'+str(indices[info['ring_out']]),'G_'+a,1,pedestrians)]:
            edge=ET.SubElement(edges,'edge',{'id':a+'_'+suffix,'from':start,'to':end,'priority':'1',
                'numLanes':str(lanes+int(sidewalk)),'speed':'8.33','name':info['name']})
            if sidewalk:ET.SubElement(edge,'lane',index='0',allow='pedestrian',width='2',speed='1.4')
            for lane in range(lanes):ET.SubElement(edge,'lane',index=str(lane+int(sidewalk)),disallow='pedestrian',width='3.2')
        # Las dos entradas principales se estrechan antes del anillo simplificado.
        for lane in range(info['lanes_per_direction']):
            ET.SubElement(connections,'connection',{'from':a+'_in','to':a+'_link_in',
                'fromLane':str(lane+offset),'toLane':str(offset),'tl':'J1'})
        for lane in range(info['lanes_per_direction']):
            ET.SubElement(connections,'connection',{'from':a+'_link_out','to':a+'_out',
                'fromLane':str(offset),'toLane':str(lane+offset),'tl':'J1'})
        if pedestrians:ET.SubElement(connections,'crossing',node='G_'+a,edges=f'{a}_in {a}_out',width='4',priority='true')
    salida=source['exit_only'];x,y=project(salida['shape'][-1])
    ET.SubElement(nodos,'node',id='D',x=str(x),y=str(y),type='priority')
    ET.SubElement(edges,'edge',{'id':'D_out','from':'R'+str(indices[salida['ring_node']]),'to':'D',
        'numLanes':'1','speed':'8.33','disallow':'pedestrian','name':salida['name']})
    for root,name in [(nodos,'red.nod.xml'),(edges,'red.edg.xml'),(connections,'red.con.xml')]:write_xml(root,directory/name)
    result=subprocess.run([binary('netconvert'),'--node-files','red.nod.xml','--edge-files','red.edg.xml',
        '--connection-files','red.con.xml','--output-file','red.net.xml','--no-turnarounds','true',
        '--xml-validation','never','--tls.allred.time','2','--tls.yellow.time','3'],cwd=directory,
        check=True,capture_output=True,text=True)
    root=ET.parse(directory/'red.net.xml').getroot()
    # Los extremos recortados no ofrecen un cruce alternativo sin semáforo.
    zonas={e.get('id') for e in root.findall('edge') if e.get('function')=='walkingarea'
           and not e.get('id').startswith(':G_')}
    for e in list(root):
        if (e.tag=='edge' and e.get('id') in zonas) or (e.tag=='connection' and (e.get('from') in zonas or e.get('to') in zonas)):
            root.remove(e)
    write_xml(root,directory/'red.net.xml')
    additional=ET.Element('additional')
    for a,info in source['arms'].items():
        for lane in range(info['lanes_per_direction']):
            ET.SubElement(additional,'laneAreaDetector',id=f'det_{a}_{lane}',lane=f'{a}_in_{lane+offset}',
                pos='0',endPos='-0.1',timeThreshold='1',speedThreshold='0.1',jamThreshold='10',period='60',file='NUL')
    write_xml(additional,directory/'detectores.add.xml')
    return directory,result.stderr


def guardar_rutas(vehicles,directory,seed,source):
    rng=random.Random(seed+2000003)
    root=ET.parse(directory/'demanda.rou.xml').getroot()
    for route in list(root.findall('route')):root.remove(route)
    for vehicle in list(root.findall('vehicle')):root.remove(vehicle)
    ring=source['ring'];indices={r['id']:i for i,r in enumerate(ring)}
    filas=[]
    for v in vehicles:
        origen=v['arm'];destino=rng.choice([a for a in (*ARMS,'D') if a!=origen])
        inicio=indices[source['arms'][origen]['ring_in']]
        fin=indices[source['exit_only']['ring_node'] if destino=='D' else source['arms'][destino]['ring_out']]
        recorrido=[];i=inicio
        while i!=fin:
            recorrido.append(f'ring_{i}');i=(i+1)%len(ring)
        pasos=[origen+'_in',origen+'_link_in',*recorrido]+(['D_out'] if destino=='D' else [destino+'_link_out',destino+'_out'])
        vehicle=ET.SubElement(root,'vehicle',id=v['id'],type='car',depart=str(v['scheduled']),departLane='best',departSpeed='max')
        ET.SubElement(vehicle,'route',edges=' '.join(pasos))
        filas.append({**v,'destination':destino,'turn':'rotonda'})
    write_xml(root,directory/'demanda.rou.xml')
    with (directory/'giros.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['id','arm','scheduled','destination','turn']);writer.writeheader();writer.writerows(filas)


class ControlRotonda(PedestrianController):
    """Alterna circulación con cesión en el anillo y cruce peatonal exclusivo."""
    def update(self, now):
        elapsed=self.advance_clock(now)
        if self.stage=='green':
            temporal=self.mode=='fijo' or self.fallback
            llegada=sum(self.observation.approaching) if self.observation and not self.fallback else 0
            edad=0 if self.request_since is None else now-self.request_since
            terminar=elapsed>=self.timing.fixed_green if temporal else (
                self.request_since is not None and elapsed>=self.timing.min_green
                and (llegada==0 or edad>=REQUEST_SECONDS or elapsed>=self.timing.max_green))
            if terminar:self.stage,self.since,self.reason='yellow',now,'solicitud_peatonal' if not temporal else 'temporizacion_fija'
        elif self.stage=='yellow' and elapsed>=self.timing.yellow:
            self.stage,self.since,self.reason='red',now,'despeje'
        elif self.stage=='red' and elapsed>=self.timing.all_red:
            if not self.vehicles_crossing:
                self.stage,self.since,self.reason='walk',now,'servicio_peatonal';self.request_since=None
            else:self.reason='espera_despeje_vehicular'
        elif self.stage=='walk' and elapsed>=WALK_SECONDS:
            self.stage,self.since,self.reason='ped_clear',now,'despeje_peatonal'
        elif self.stage=='ped_clear' and elapsed>=CLEAR_SECONDS and not self.occupied:
            self.stage,self.since,self.reason='green',now,'cruce_despejado'
        return self.state()

    def state(self):
        return 'GGGG' if self.stage=='green' else 'yyyy' if self.stage=='yellow' else 'rrrr'
