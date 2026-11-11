"""Demandas Poisson por tramos generadas antes de escoger el controlador."""
import csv
import random
import xml.etree.ElementTree as ET
from .config import ARMS, scenarios
from .network import write_xml


def generate(scenario, seed, horizon=1800):
    if scenario not in scenarios()['scenarios'] and scenario != 'escolar':
        raise ValueError('Escenario desconocido')
    rng=random.Random(seed)
    vehicles=[]
    segments = scenarios()['scenarios'][scenario]['segments'] if scenario != 'escolar' else [
        {'begin':0,'end':horizon/3,'rates':[120,120,120,120]},
        {'begin':horizon/3,'end':2*horizon/3,'rates':[700,300,700,300]},
        {'begin':2*horizon/3,'end':horizon,'rates':[120,120,120,120]}]
    for segment in segments:
        end=min(segment['end'],horizon)
        for arm, rate in zip(ARMS,segment['rates']):
            t=segment['begin']
            while rate>0:
                t += rng.expovariate(rate/3600)
                if t>=end:break
                vehicles.append({'arm':arm,'scheduled':round(t,3)})
    vehicles.sort(key=lambda x:(x['scheduled'],x['arm']))
    for i,v in enumerate(vehicles):v['id']=f'veh_{i:05d}'
    return vehicles


def save(vehicles, directory, pedestrians=False):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'demanda.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['id','arm','scheduled'])
        writer.writeheader();writer.writerows(vehicles)
    root=ET.Element('routes')
    ET.SubElement(root,'vType',id='car',carFollowModel='Krauss',accel='2.6',decel='4.5',
                  emergencyDecel='9',sigma='0',tau='1',length='5',minGap='2.5',
                  maxSpeed='13.89',speedFactor='1',speedDev='0')
    for i,arm in enumerate(ARMS):
        ET.SubElement(root,'route',id=arm,edges=f'{arm}_in {ARMS[(i+2)%4]}_out')
    for v in vehicles:
        ET.SubElement(root,'vehicle',id=v['id'],type='car',route=v['arm'],
                      depart=str(v['scheduled']),departLane='1' if pedestrians else '0',departSpeed='max')
    write_xml(root,directory/'demanda.rou.xml')
