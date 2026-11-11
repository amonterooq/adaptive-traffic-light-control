"""Dibujo vectorial propio; .drawio, SVG y PDF parten de la misma especificación."""
from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape
import math
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT=Path(__file__).resolve().parent


def diagram(name,title,size,boxes,edges,notes=()):
    w,h=size
    xml=ET.Element('mxfile',host='app.diagrams.net')
    model=ET.SubElement(ET.SubElement(xml,'diagram',name=title,id=name),'mxGraphModel',pageWidth=str(w),pageHeight=str(h))
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#42675f"/></marker></defs>',
         f'<rect width="{w}" height="{h}" fill="white"/>']
    c=canvas.Canvas(str(ROOT/'pdf'/f'{name}.pdf'),pagesize=(w,h));c.setTitle(title);c.setAuthor('Ana Montero Preciado')
    def text(x,y,value,font=12,bold=False):
        svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial" font-size="{font}" fill="#23473e" font-weight="{"bold" if bold else "normal"}">{escape(value)}</text>')
        c.setFillColor(HexColor('#23473e'));c.setFont('Helvetica-Bold' if bold else 'Helvetica',font);c.drawCentredString(x,h-y,value)
    def vertex(id,x,y,bw,bh,lines,color):
        wrapped=[]
        for line in lines:
            current=''
            for word in line.split():
                candidate=(current+' '+word).strip()
                if current and stringWidth(candidate,'Helvetica-Bold',16)>bw-16:
                    wrapped.append(current);current=word
                else:current=candidate
            wrapped.append(current)
        font=min(16,(bh-12)/len(wrapped)-2)
        spacing=font+2
        cell=ET.SubElement(root,'mxCell',id=id,value='\n'.join(wrapped),style=f'rounded=1;whiteSpace=wrap;html=0;fillColor={color};strokeColor=#8aa99d;fontColor=#23473e;fontSize={font};',vertex='1',parent='1')
        ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(bw),height=str(bh),attrib={'as':'geometry'})
        svg.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{color}" stroke="#8aa99d"/>')
        c.setStrokeColor(HexColor('#8aa99d'));c.setFillColor(HexColor(color));c.roundRect(x,h-y-bh,bw,bh,8,stroke=1,fill=1)
        for i,line in enumerate(wrapped):text(x+bw/2,y+bh/2-(len(wrapped)-1)*spacing/2+i*spacing+font/3,line,font,i==0)
    vertex('title',12,8,w-24,35,[title],'#ffffff')
    lookup={b[0]:b for b in boxes}
    for b in boxes:vertex(*b)
    for idx,(a,b,label,waypoints) in enumerate(edges):
        ax,ay,aw,ah=lookup[a][1:5];bx,by,bw,bh=lookup[b][1:5]
        if waypoints:pts=waypoints
        elif abs((by+bh/2)-(ay+ah/2))<10:pts=[(ax+aw,ay+ah/2),(bx,by+bh/2)] if bx>ax else [(ax,ay+ah/2),(bx+bw,by+bh/2)]
        else:pts=[(ax+aw/2,ay+ah),(bx+bw/2,by)] if by>ay else [(ax+aw/2,ay),(bx+bw/2,by+bh)]
        d=' '.join(('M' if i==0 else 'L')+f'{x},{y}' for i,(x,y) in enumerate(pts))
        svg.append(f'<path d="{d}" fill="none" stroke="#42675f" stroke-width="1.6" marker-end="url(#arrow)"/>')
        c.setStrokeColor(HexColor('#42675f'));c.setLineWidth(1.2)
        for p,q in zip(pts,pts[1:]):c.line(p[0],h-p[1],q[0],h-q[1])
        p,q=pts[-2:];angle=math.atan2(q[1]-p[1],q[0]-p[0]);arr=c.beginPath();arr.moveTo(q[0],h-q[1]);arr.lineTo(q[0]-7*math.cos(angle-.4),h-(q[1]-7*math.sin(angle-.4)));arr.lineTo(q[0]-7*math.cos(angle+.4),h-(q[1]-7*math.sin(angle+.4)));arr.close();c.setFillColor(HexColor('#42675f'));c.drawPath(arr,fill=1,stroke=0)
        label_start,label_end=max(zip(pts,pts[1:]),key=lambda pair:math.dist(*pair))
        labelx=(label_start[0]+label_end[0])/2;labely=(label_start[1]+label_end[1])/2-7
        if label:text(labelx,labely,label,13)
        cell=ET.SubElement(root,'mxCell',id=f'e{idx}',value=label,style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;strokeColor=#42675f;',edge='1',parent='1',source=a,target=b)
        g=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if waypoints:
            points=ET.SubElement(g,'Array',attrib={'as':'points'})
            for x,y in pts[1:-1]:ET.SubElement(points,'mxPoint',x=str(x),y=str(y))
    for i,note in enumerate(notes):
        y=h-18-(len(notes)-i-1)*16
        text(w/2,y,note,12)
        cell=ET.SubElement(root,'mxCell',id=f'n{i}',value=note,style='text;html=0;align=center;fontSize=10;',vertex='1',parent='1')
        ET.SubElement(cell,'mxGeometry',x='15',y=str(y-12),width=str(w-30),height='18',attrib={'as':'geometry'})
    svg.append('</svg>');(ROOT/'svg'/f'{name}.svg').write_text('\n'.join(svg),encoding='utf-8')
    ET.indent(xml);ET.ElementTree(xml).write(ROOT/'drawio'/f'{name}.drawio',encoding='utf-8',xml_declaration=True)
    c.save()


def main():
    mint='#e8f2ec';gray='#f3f5f1';sand='#f8eedc'
    diagram('arquitectura','Arquitectura del prototipo ITS',(850,355),[
        ('sumo',25,80,180,75,['SUMO','Vehículos y peatones','E2 y ocupación de pasos'],mint),
        ('runner',320,80,210,75,['Adaptador Python','Adquisición y avance de 1 s'],mint),
        ('control',625,80,200,75,['Controlador','Fases y datos obsoletos'],mint),
        ('db',320,225,210,65,['SQLite','Ejecuciones y muestras'],gray),
        ('api',25,225,180,65,['FastAPI','Estado e histórico'],gray),
        ('web',625,225,200,65,['Navegador','Animación y resultados'],gray)],
        [('sumo','runner','TraCI / TCP',None),('runner','control','Observación',None),
         ('control','sumo','Orden de fase',[(725,80),(725,58),(115,58),(115,80)]),
         ('runner','db','Persistencia',None),('db','api','Consulta',None),
         ('api','web','HTTP / JSON',[(115,290),(115,332),(725,332),(725,290)])])
    diagram('estados','Secuencia de fases y condiciones de cambio',(850,370),[
        ('ng',30,85,190,65,['Verde N/S','10 a 50 s / fijo: 30 s'],mint),('ny',330,85,190,65,['Amarillo N/S','3 segundos'],sand),('r1',630,85,190,65,['Todo-rojo','2 segundos'],gray),
        ('eg',630,245,190,65,['Verde E/O','10 a 50 s / fijo: 30 s'],mint),('ey',330,245,190,65,['Amarillo E/O','3 segundos'],sand),('r2',30,245,190,65,['Todo-rojo','2 segundos'],gray)],
        [('ng','ny','Regla de cambio',None),('ny','r1','Fin de amarillo',None),('r1','eg','Fin de despeje',None),('eg','ey','Regla de cambio',None),('ey','r2','Fin de amarillo',None),('r2','ng','Fin de despeje',None)],
        ['Regla adaptativa: verde máximo, o mínimo cumplido y cola opuesta suficiente.', 'Una muestra con más de 5 s de antigüedad activa temporización de respaldo.'])
    diagram('datos','Modelo relacional implementado en SQLite, versión 4',(980,470),[
        ('runs',25,75,235,165,['runs','PK id','scenario, mode, seed','created_at, status','config_json, summary_json'],mint),
        ('samples',375,75,240,165,['samples','PK (run_id, t)','FK run_id -> runs.id','q_n, q_e, q_s, q_w','state, fallback','arrived, in_network'],gray),
        ('peds',720,75,235,165,['pedestrian_samples','PK/FK (run_id, t)','ped_signal, ped_waiting','ped_crossing, ped_stage'],sand),
        ('coop',375,310,240,95,['cooperative_samples','PK/FK (run_id, t)','payload_json: V2I y cámara'],mint)],
        [('runs','samples','1 a N',None),('samples','peds','1 a 0..1',None),('samples','coop','1 a 0..1',None)],
        ['Las tablas adicionales conservan las sesiones previas; los viajes completos quedan en CSV/XML.'])
    diagram('secuencia','Un paso de simulación y su consulta desde el navegador',(900,440),[
        ('a',20,75,250,65,['1. Leer detectores','E2 y personas mediante TraCI'],mint),
        ('b',325,75,250,65,['2. Validar observación','Colas + V2I + cámara'],mint),
        ('c',630,75,250,65,['3. Decidir fase','Reglas + máquina de estados'],mint),
        ('d',630,255,250,65,['4. Aplicar y avanzar','TraCI: estado y simulationStep'],mint),
        ('e',325,255,250,65,['5. Registrar muestra','CSV / SQLite en sesión web'],gray),
        ('f',20,255,250,65,['6. Actualizar pantalla','Estado: 500 ms reales','Escena activa: 100 ms reales'],gray)],
        [('a','b','',None),('b','c','',None),('c','d','',None),('d','e','',None),('e','f','HTTP',None),('d','a','Siguiente segundo simulado',[(755,320),(755,375),(8,375),(8,185),(145,185),(145,140)])],
        ['El reloj simulado y el reloj del navegador son distintos; las métricas usan tiempo simulado.'])
    diagram('escenario','Modelo de intersección usado en los experimentos',(620,530),[
        ('n',220,65,180,65,['Norte','Entrada y salida: 300 m'],gray),
        ('e',410,225,180,65,['Este','300 m'],gray),
        ('s',220,385,180,65,['Sur','Entrada y salida: 300 m'],gray),
        ('w',30,225,180,65,['Oeste','300 m'],gray),
        ('j',245,230,130,55,['J1','Dos ejes'],mint)],
        [('n','j','N/S',None),('j','s','',None),('w','j','E/O',None),('j','e','',None)],
        ['Un carril por sentido, movimientos rectos y detectores en los accesos.', 'La ubicación geográfica es real; esta geometría y sus parámetros son sintéticos.'])
    diagram('red_campo','Propuesta de campo: telemetría y control local',(940,460),[
        ('node',20,85,180,70,['Nodo de bajo consumo','Conteos agregados'],mint),
        ('gw',290,85,180,70,['Pasarela LoRaWAN','Transporte IP'],mint),
        ('lns',560,85,170,70,['Servidor de red','Integración de datos'],gray),
        ('app',560,290,170,80,['Backend / API','Históricos y alarmas'],gray),
        ('local',20,290,180,80,['Controlador local','Solicitud y ocupación','Temporización de fases'],sand),
        ('web',790,290,130,80,['Supervisión','Navegador'],gray)],
        [('node','gw','Radio LoRaWAN',None),('gw','lns','IP / TLS',None),('lns','app','Datos normalizados',None),
         ('local','app','Red municipal / acceso IP',None),('app','web','HTTP',None)],
        ['Arquitectura conceptual de campo: adquisición distribuida y control local.',
         'El control local no depende de recibir cada segundo un resumen remoto de telemetría.'])
    diagram('fase_peatonal','Fase peatonal exclusiva y despeje supervisado',(940,450),[
        ('g',20,80,240,65,['Verde vehicular','Respetar mínimo'],mint),
        ('y',350,80,240,65,['Amarillo vehicular','3 segundos'],sand),
        ('r',680,80,240,65,['Todo-rojo','Al menos 2 s'],gray),
        ('walk',680,260,240,75,['Admisión peatonal','10 s; vehículos en rojo'],mint),
        ('clear',350,260,240,75,['Despeje peatonal','Al menos 15 s; todo-rojo'],sand),
        ('next',20,260,240,75,['Verde del eje opuesto','Solo con pasos vacíos'],mint)],
        [('g','y','Fin / petición',None),('y','r','',None),('r','walk','Sin vehículos internos',None),
         ('walk','clear','Fin de admisión',None),('clear','next','Despeje cumplido',None)],
        ['El fijo reserva el servicio después de E/O. El adaptativo lo omite si no hay solicitud.',
         'Si queda una persona en un paso, el despeje se prolonga y no se autoriza verde vehicular.'])
    diagram('cooperacion','Adquisición híbrida: del coche y la acera al semáforo',(940,510),[
        ('cars',20,75,210,80,['Vehículos equipados','Posición, velocidad e instante','Informes emulados'],mint),
        ('rsu',345,75,240,80,['Receptor / RSU lógica','Retardo, pérdidas y caducidad','Estimación de llegada'],mint),
        ('det',20,245,210,80,['Sensores virtuales','Colas en accesos','Presencia peatonal'],sand),
        ('fusion',345,245,240,80,['Fusión por acceso','Cola + aproximaciones','Sin duplicar detenidos'],mint),
        ('control',695,245,225,80,['Controlador local','Fases y solicitudes','Comprobación del despeje'],mint),
        ('panel',345,395,240,65,['Panel y almacenamiento','Métricas por ubicación'],gray),
        ('future',695,395,225,65,['Evolución de campo','Una unidad por cruce','Supervisión conjunta'],gray)],
        [('cars','rsu','V2I',None),('rsu','fusion','Avisos vigentes',None),('det','fusion','Observaciones',None),
         ('fusion','control','Demanda',None),('fusion','panel','Registro',None),('control','future','Propuesta',None)],
        ['Prototipo: una simulación activa. No se emula radio ni se coordinan varios semáforos urbanos.'])


if __name__=='__main__':main()
