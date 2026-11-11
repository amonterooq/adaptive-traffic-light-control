from pathlib import Path
import subprocess
import os
import xml.etree.ElementTree as ET
import sumolib
from .config import ARMS, ROOT


def native_path(path):
    path = str(Path(path).absolute())
    if os.name == 'nt' and not path.isascii():
        import ctypes
        parent = Path(path) if Path(path).exists() else Path(path).parent
        buf = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetShortPathNameW(str(parent), buf, len(buf)):
            return buf.value if Path(path).exists() else str(Path(buf.value)/Path(path).name)
        raise RuntimeError('SUMO necesita una ruta sin tildes en esta instalación de Windows.')
    return path


def binary(name):
    # The PyPI eclipse-sumo distribution is discovered by sumolib as well as SUMO_HOME.
    result = native_path(sumolib.checkBinary(name))
    if os.environ.get('SUMO_HOME'):
        os.environ['SUMO_HOME'] = native_path(os.environ['SUMO_HOME'])
    return result


def write_xml(root, path):
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def build_network(directory=None, pedestrians=False):
    directory = Path(directory or ROOT/('simulacion/escenarios/red_peatones' if pedestrians else 'simulacion/escenarios/red'))
    directory.mkdir(parents=True, exist_ok=True)
    nodes = ET.Element('nodes')
    ET.SubElement(nodes, 'node', id='J1', x='0', y='0', type='traffic_light')
    for name, x, y in [('N',0,300),('E',300,0),('S',0,-300),('W',-300,0)]:
        ET.SubElement(nodes, 'node', id=name, x=str(x), y=str(y), type='priority')
    edges = ET.Element('edges')
    connections = ET.Element('connections')
    for i, arm in enumerate(ARMS):
        for suffix, start, end in [('in', arm, 'J1'), ('out', 'J1', arm)]:
            edge = ET.SubElement(edges, 'edge', {'id': f'{arm}_{suffix}', 'from':start, 'to':end, 'numLanes':'2' if pedestrians else '1', 'speed':'13.89'})
            if pedestrians:
                ET.SubElement(edge, 'lane', index='0', allow='pedestrian', width='2', speed='1.4')
                ET.SubElement(edge, 'lane', index='1', disallow='pedestrian', width='3.2')
        lane = '1' if pedestrians else '0'
        ET.SubElement(connections, 'connection', {'from':f'{arm}_in', 'to':f'{ARMS[(i+2)%4]}_out', 'fromLane':lane, 'toLane':lane, 'tl':'J1', 'linkIndex':str(i)})
        if pedestrians:
            ET.SubElement(connections, 'crossing', node='J1', edges=f'{arm}_in {arm}_out', width='4', priority='true')
    for root, name in [(nodes,'red.nod.xml'),(edges,'red.edg.xml'),(connections,'red.con.xml')]:
        write_xml(root, directory/name)
    subprocess.run([binary('netconvert'), '--node-files','red.nod.xml',
                    '--edge-files','red.edg.xml','--connection-files','red.con.xml',
                    '--output-file','red.net.xml','--no-turnarounds','true',
                    '--xml-validation','never','--tls.allred.time','2','--tls.yellow.time','3'],
                   cwd=directory,check=True,capture_output=True)
    additional=ET.Element('additional')
    for arm in ARMS:
        ET.SubElement(additional,'laneAreaDetector', id=f'det_{arm}', lane=f'{arm}_in_{1 if pedestrians else 0}',
                      pos='0', endPos='-0.1', timeThreshold='1', speedThreshold='0.1',
                      jamThreshold='10', period='60', file='NUL')
    write_xml(additional, directory/'detectores.add.xml')
    return directory


if __name__ == '__main__':
    print(build_network())
