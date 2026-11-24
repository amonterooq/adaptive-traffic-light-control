"""Correspondencia entre movimientos, pasos y conflictos de la red SUMO."""
import xml.etree.ElementTree as ET
import subprocess
from .config import ARMS
from .network import binary, write_xml


def preparar_prioridades(directory):
    """Netconvert recalcula la cesión del giro N→O frente al movimiento E→O."""
    root=ET.parse(directory/'red.net.xml').getroot()
    conexiones=[c for c in root.findall('connection') if c.get('tl')=='J1']
    size=max(int(c.get('linkIndex')) for c in conexiones)+1
    logic=ET.Element('additional')
    program=ET.SubElement(logic,'tlLogic',id='J1',type='static',programID='0',offset='0')
    for arm in ARMS:
        variants=(None,'S','N') if arm=='E' else (None,)
        for extra in variants:
            state=['r']*size
            for c in conexiones:
                origin=c.get('from').split('_')[0]
                if origin==arm:state[int(c.get('linkIndex'))]='G'
                elif origin==extra and c.get('dir')=='r':state[int(c.get('linkIndex'))]='g' if extra=='N' else 'G'
            ET.SubElement(program,'phase',duration='30',state=''.join(state))
            ET.SubElement(program,'phase',duration='3',state=''.join('y' if s in 'Gg' else s for s in state))
            ET.SubElement(program,'phase',duration='2',state='r'*size)
    if any(c.get('from').startswith(':') for c in conexiones):
        state=['r']*size
        for c in conexiones:
            if c.get('from').startswith(':'):state[int(c.get('linkIndex'))]='G'
        ET.SubElement(program,'phase',duration='10',state=''.join(state))
        ET.SubElement(program,'phase',duration='15',state='r'*size)
    write_xml(logic,directory/'prioridades.tll.xml')
    subprocess.run([binary('netconvert'),'--sumo-net-file','red.net.xml','--tllogic-files','prioridades.tll.xml',
                    '--output-file','red_prioridades.net.xml','--xml-validation','never'],
                   cwd=directory,check=True,capture_output=True,text=True)
    converted=ET.parse(directory/'red_prioridades.net.xml').getroot()
    ET.SubElement(converted.find("tlLogic[@id='J1']"),'param',key='plan_revision',value='lusitania_movimientos_v3')
    write_xml(converted,directory/'red.net.xml')
    (directory/'red_prioridades.net.xml').unlink()


class Movimientos:
    def __init__(self, directory, links):
        root = ET.parse(directory/'red.net.xml').getroot()
        self.pasos = {e.get('id'): e.get('crossingEdges').split()[0].split('_')[0]
                      for e in root.findall('edge') if e.get('function') == 'crossing'}
        self.links = links
        self.vehiculos, self.peatones, self.conflictos = {}, {}, {}
        conexiones = {int(c.get('linkIndex')): c for c in root.findall('connection') if c.get('tl') == 'J1'}
        junction = root.find("junction[@id='J1']")
        requests = {} if junction is None else {int(r.get('index')): r.get('foes')[::-1] for r in junction.findall('request')}
        internos = [] if junction is None else junction.get('intLanes').split()
        continuaciones={c.get('from')+'_'+c.get('fromLane'):c.get('via') for c in root.findall('connection') if c.get('via') and c.get('from').startswith(':')}
        indices={}
        for i,c in conexiones.items():
            via=c.get('via');seen=set()
            while via and via not in internos and via not in seen:
                seen.add(via);via=continuaciones.get(via)
            if via in internos:indices[i]=internos.index(via)
        for i, link in enumerate(links):
            origen, destino, _ = link[0]
            if origen.startswith(':'):
                paso = destino.rsplit('_', 1)[0]
                if paso not in self.pasos:
                    raise ValueError('Conexión peatonal sin paso identificado')
                self.peatones[i] = paso
            else:
                self.vehiculos[i] = (origen.split('_')[0], destino.split('_')[0], conexiones[i].get('dir'))
        for i, (origen, destino, _) in self.vehiculos.items():
            conflictos = {p for p, a in self.pasos.items() if a in (origen, destino)}
            for j, paso in self.peatones.items():
                if i in indices and j in indices:
                    x, y = indices[i], indices[j]
                    if requests[x][y] == '1' or requests[y][x] == '1':
                        conflictos.add(paso)
            self.conflictos[i] = conflictos

    def compatibles(self):
        return {(a, p): {i for i, (origen, _, _) in self.vehiculos.items()
                         if origen == a and p not in self.conflictos[i]}
                for a in ARMS for p in self.pasos}

    def aplicar(self, controller):
        state = controller.state()
        permitidos = controller.compatibles.get((ARMS[controller.axis], controller.paso)) if controller.paso else None
        signals = ['r'] * len(self.links)
        for i, (origen, _, _) in self.vehiculos.items():
            signals[i] = state[ARMS.index(origen)] if permitidos is None or i in permitidos else 'r'
        for i, paso in self.peatones.items():
            signals[i] = 'G' if paso == controller.paso and controller.stage == 'walk' else 'r'
        for i,(origen,_,giro) in self.vehiculos.items():
            if origen==controller.derecha and giro=='r' and ARMS[controller.axis]=='E':
                signals[i]=controller.senal_derecha()
        return ''.join(signals)

    def detalle(self, applied):
        movimientos = {a: {} for a in ARMS}
        for i, (origen, _, giro) in self.vehiculos.items():
            movimientos[origen][giro] = applied[i]
        return {'movement_signals': movimientos,
                'ped_signals': {paso: applied[i] for i, paso in self.peatones.items()}}

    def aplicar_rotonda(self, controller, prioridades):
        signals=['r']*len(self.links)
        for i,(origen,_,_) in self.vehiculos.items():
            color=controller.pasos[origen].state()[0]
            signals[i]=prioridades[i] if color=='G' else color
        for i,paso in self.peatones.items():
            signals[i]='G' if controller.pasos[self.pasos[paso]].stage=='walk' else 'r'
        return ''.join(signals)

    def conflicto(self, applied, ocupados, vehiculos):
        abiertos = {p for i, p in self.peatones.items() if applied[i] == 'G'}
        protegidos = abiertos | {p for p, n in ocupados.items() if n}
        if any(applied[i] in 'Ggy' and self.conflictos[i] & protegidos for i in self.vehiculos):
            return True
        return any(self.conflictos[i] & abiertos for i in vehiculos)
