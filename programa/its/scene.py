"""Read-only SUMO positions for the live view; never drives the controller."""
from functools import lru_cache
import math
import xml.etree.ElementTree as ET
import traci.constants as tc
from .locations import network_directory, geographic, project


def points(value):
    return [[float(v) for v in pair.split(',')] for pair in value.split()]


@lru_cache(maxsize=10)
def geometry(pedestrians=True, location='laboratorio'):
    net = ET.parse(network_directory(location,pedestrians)/'red.net.xml').getroot()
    junction = net.find("junction[@id='J1']")
    if location=='santa_eulalia':
        offset=[float(v) for v in net.find('location').get('netOffset').split(',')]
        junction=ET.Element('junction',x=str(offset[0]),y=str(offset[1]),shape='')
    lanes = []
    for edge in net.findall('edge'):
        function = edge.get('function', '')
        for lane in edge.findall('lane'):
            kind = function or ('sidewalk' if lane.get('allow') == 'pedestrian' else 'road')
            lanes.append({'id': lane.get('id'), 'kind': kind, 'shape': points(lane.get('shape')),
                          'width': float(lane.get('width', '3.2'))})
    result={'center': [float(junction.get('x')), float(junction.get('y'))],
            'junction': points(junction.get('shape')), 'lanes': lanes, 'pedestrians': pedestrians,
            'bounds': [float(v) for v in net.find('location').get('convBoundary').split(',')],
            'location':location,'name':'Cruce de laboratorio','detail_radius':38,'wide_radius':315}
    if location!='laboratorio':
        source=geographic(location);cx,cy=result['center']
        def local(p):
            x,y=project(p,location);return [x+cx,y+cy]
        result.update(name=source['name'],detail_radius=65,wide_radius=170,
            attribution=source['attribution'],source='https://www.openstreetmap.org/node/'+source['osm_node'],
            district=source['district'],signal_status=source.get('signal_status','modelled'),
            geographic_center=source['center'],assumptions=source['assumptions'],
            context=[{'properties':f['properties'],'polygon':f['geometry']['type']=='Polygon',
                      'shape':[local(p) for p in (f['geometry']['coordinates'][0] if f['geometry']['type']=='Polygon' else f['geometry']['coordinates'])]}
                     for f in source['context']['features']],
            landmarks=[{'name':p['name'],'position':local(p['position'])} for p in source['landmarks']],
            arms={a:{'name':d['name'],'label':d.get('label',d['name']),'shape':[local(p) for p in d['centerline']]} for a,d in source['arms'].items()})
    return result


class SceneCollector:
    """Subscribe once per inserted agent; subsequent reads use the local results."""
    def __init__(self):
        self.known = {'vehicle': set(), 'person': set()}

    def collect(self, conn, sample, cooperative=None):
        agents = []
        for kind in ('vehicle', 'person'):
            domain = getattr(conn, kind)
            ids = set(domain.getIDList())
            variables = [tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED, tc.VAR_ROAD_ID, tc.VAR_WAITING_TIME]
            if kind == 'vehicle':
                variables += [tc.VAR_LENGTH, tc.VAR_WIDTH]
            for id in ids - self.known[kind]:
                domain.subscribe(id, variables)
            self.known[kind] = ids
            for id, values in domain.getAllSubscriptionResults().items():
                if id not in ids:
                    continue
                x, y = values[tc.VAR_POSITION]
                if not all(math.isfinite(v) and abs(v) < 100000 for v in (x, y)):
                    continue
                agents.append({'id': id, 'kind': kind, 'x': round(x, 4), 'y': round(y, 4),
                               'angle': values[tc.VAR_ANGLE], 'speed': round(values[tc.VAR_SPEED], 3),
                               'road': values[tc.VAR_ROAD_ID], 'waiting': values[tc.VAR_WAITING_TIME],
                               'length': values.get(tc.VAR_LENGTH, .6), 'width': values.get(tc.VAR_WIDTH, .6)})
                if kind=='vehicle':agents[-1]['vehicle_type']=conn.vehicle.getTypeID(id)
                if kind=='vehicle' and cooperative:
                    agents[-1].update(connected_vehicle=cooperative.equipped(id) and agents[-1]['vehicle_type'] not in ('bicicleta','patinete'),
                                     v2x_received=id in cooperative.fresh_ids)
        return {'time': conn.simulation.getTime(), 'agents': agents, 'sample': sample}
