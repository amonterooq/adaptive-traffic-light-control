"""Prepared geographic scenario. All assumptions are shipped with the source data."""
import csv
import json
import math
import random
import subprocess
import xml.etree.ElementTree as ET
from functools import lru_cache
from .config import ARMS, ROOT
from .network import binary, write_xml

GEOGRAPHIC_LOCATIONS = ('lusitania', 'santa_eulalia')

@lru_cache(maxsize=4)
def geographic(location='lusitania'):
    if location not in GEOGRAPHIC_LOCATIONS:raise ValueError('Ubicación no preparada')
    return json.loads((ROOT/f'datos/entrada/{location}.json').read_text(encoding='utf-8'))

def lusitania():
    return geographic('lusitania')

def project(position, location='lusitania'):
    lon,lat=geographic(location)['center']
    return [(position[0]-lon)*111320*math.cos(math.radians(lat)),(position[1]-lat)*111320]


def network_directory(location, pedestrians):
    if location=='laboratorio':
        return ROOT/'simulacion/escenarios'/('red_peatones' if pedestrians else 'red')
    if location not in GEOGRAPHIC_LOCATIONS:raise ValueError('Ubicación no preparada')
    return ROOT/'simulacion/escenarios'/(location+'_peatones' if pedestrians else location)


def build_lusitania(pedestrians=True):
    return build_geographic('lusitania', pedestrians)

def build_geographic(location, pedestrians=True):
    source=geographic(location)
    directory=network_directory(location,pedestrians)
    if location=='santa_eulalia':
        from .rotonda import construir
        return construir(directory,source,lambda p:project(p,location),pedestrians)
    directory.mkdir(parents=True,exist_ok=True)
    nodes=ET.Element('nodes');edges=ET.Element('edges');connections=ET.Element('connections')
    ET.SubElement(nodes,'node',id='J1',x='0',y='0',type='traffic_light')
    counts={a:d['lanes_per_direction'] for a,d in source['arms'].items()}
    offset=int(pedestrians)
    for arm,info in source['arms'].items():
        shape=[project(p,location) for p in info['centerline']]
        ET.SubElement(nodes,'node',id=arm,x=str(shape[-1][0]),y=str(shape[-1][1]),type='priority')
        for suffix,start,end,points in [('in',arm,'J1',list(reversed(shape))),('out','J1',arm,shape)]:
            edge=ET.SubElement(edges,'edge',{'id':arm+'_'+suffix,'from':start,'to':end,
                'numLanes':str(counts[arm]+offset),'speed':'8.33','name':info['name'],
                'shape':' '.join(f'{x:.4f},{y:.4f}' for x,y in points),'spreadType':'right'})
            if pedestrians:ET.SubElement(edge,'lane',index='0',allow='pedestrian',width='2',speed='1.4')
            for i in range(counts[arm]):ET.SubElement(edge,'lane',index=str(i+offset),disallow='pedestrian',width='3.2')
        index=ARMS.index(arm)
        for turn,delta in [('right',-1),('straight',2),('left',1)]:
            target=ARMS[(index+delta)%4]
            lanes=range(counts[arm]) if turn=='straight' else [0 if turn=='right' else counts[arm]-1]
            for lane in lanes:
                to_lane=min(lane,counts[target]-1) if turn=='straight' else (0 if turn=='right' else counts[target]-1)
                ET.SubElement(connections,'connection',{'from':arm+'_in','to':target+'_out',
                    'fromLane':str(lane+offset),'toLane':str(to_lane+offset),'tl':'J1'})
        if pedestrians:ET.SubElement(connections,'crossing',node='J1',edges=f'{arm}_in {arm}_out',width='4',priority='true')
    for element,name in [(nodes,'red.nod.xml'),(edges,'red.edg.xml'),(connections,'red.con.xml')]:write_xml(element,directory/name)
    result=subprocess.run([binary('netconvert'),'--node-files','red.nod.xml','--edge-files','red.edg.xml',
        '--connection-files','red.con.xml','--output-file','red.net.xml','--no-turnarounds','true',
        '--xml-validation','never','--tls.allred.time','2','--tls.yellow.time','3','--tls.left-green.time','0'],
        cwd=directory,check=True,capture_output=True,text=True)
    if pedestrians:
        # A cut boundary is not another crossing. SUMO creates sidewalk U-turns
        # there by default; on short arms those can bypass the controlled step.
        tree=ET.parse(directory/'red.net.xml');root=tree.getroot()
        boundary_areas={e.get('id') for e in root.findall('edge')
                        if e.get('function')=='walkingarea' and not e.get('id').startswith(':J1_')}
        for element in list(root):
            if (element.tag=='edge' and element.get('id') in boundary_areas) or (
                element.tag=='connection' and (element.get('from') in boundary_areas or element.get('to') in boundary_areas)):
                root.remove(element)
        write_xml(root,directory/'red.net.xml')
    additional=ET.Element('additional')
    for arm,count in counts.items():
        for lane in range(count):
            ET.SubElement(additional,'laneAreaDetector',id=f'det_{arm}_{lane}',lane=f'{arm}_in_{lane+offset}',
                pos='0',endPos='-0.1',timeThreshold='1',speedThreshold='0.1',jamThreshold='10',period='60',file='NUL')
    write_xml(additional,directory/'detectores.add.xml')
    return directory,result.stderr


def save_turning_demand(vehicles,directory,seed):
    """Independent turn draw; the established laboratory demand stays untouched."""
    rng=random.Random(seed+2000003)
    root=ET.Element('routes')
    ET.SubElement(root,'vType',id='car',carFollowModel='Krauss',accel='2.6',decel='4.5',
        emergencyDecel='9',sigma='0',tau='1',length='5',minGap='2.5',maxSpeed='8.33',speedFactor='1',speedDev='0')
    records=[]
    for v in vehicles:
        draw=rng.random();turn,delta=('straight',2) if draw<.6 else ('right',-1) if draw<.8 else ('left',1)
        target=ARMS[(ARMS.index(v['arm'])+delta)%4]
        vehicle=ET.SubElement(root,'vehicle',id=v['id'],type='car',depart=str(v['scheduled']),departLane='best',departSpeed='max')
        ET.SubElement(vehicle,'route',edges=f"{v['arm']}_in {target}_out")
        records.append({**v,'destination':target,'turn':turn})
    write_xml(root,directory/'demanda.rou.xml')
    with (directory/'giros.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['id','arm','scheduled','destination','turn']);writer.writeheader();writer.writerows(records)


def signal_states(net):
    """Keep netconvert's major/minor priorities when setting our two-axis phases."""
    phases=ET.parse(net/'red.net.xml').getroot().find("tlLogic[@id='J1']").findall('phase')
    greens=[p.get('state') for p in phases if 'G' in p.get('state') and 'y' not in p.get('state')]
    return greens


def catalog():
    return [{'id':key,'name':geographic(key)['name'],'description':geographic(key)['district'],
             'signal_status':geographic(key).get('signal_status','modelled'),
             'lat':geographic(key)['center'][1],'lon':geographic(key)['center'][0]}
            for key in GEOGRAPHIC_LOCATIONS]+[
            {'id':'laboratorio','name':'Cruce de laboratorio','description':'Modelo de referencia de la memoria',
             'signal_status':'synthetic','lat':38.9214575,'lon':-6.332157}]
