"""Tablas de la memoria a partir de la batería mixta validada."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
NOMBRES={'coches':'Solo coches','mixto':'Mixto sin peatones','peatones':'Con peatones',
         'velocidades':'Velocidades distintas','exceso':'Ensayo 30/50/70','omisiones':r'Omisiones del 30\,\%',
         'sin_clasificar':'Sin clasificar','sin_camara':'Cámara sin detecciones','v2i50':r'Cámara y V2I 50\,\%','escolar':'Salida escolar'}
LUGARES={'laboratorio':'Laboratorio','lusitania':'Lusitania','santa_eulalia':'IES Santa Eulalia'}


def numero(v):return '--' if v is None else f'{v:.2f}'.replace('.',',')


def tabla(rows, escolar):
    lineas=[r'\begin{tabularx}{\linewidth}{@{}Xrr@{\hspace{1em}}rr@{\hspace{1em}}rr@{}}\toprule',
            r' & \multicolumn{2}{c}{Vehículo (s)} & \multicolumn{2}{c}{Peatón (s)} & \multicolumn{2}{c}{CO$_2$ (g/veh.)}\\',
            r'\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}',
            r'Caso & Fijo & Adapt. & Fijo & Adapt. & Fijo & Adapt.\\\midrule']
    for r in rows:
        nombre=LUGARES[r['location']] if escolar else NOMBRES[r['case']]
        valores=[r[f'{modo}_{key}'] for key in ('mean_wait_s','ped_mean_wait_s','co2_mean_g') for modo in ('fijo','adaptativo')]
        lineas.append(nombre+' & '+' & '.join(map(numero,valores))+r'\\')
    lineas += [r'\bottomrule\end{tabularx}']
    return '\n'.join(lineas)


if __name__=='__main__':
    data=json.loads((ROOT/'datos/procesados/mixto.json').read_text(encoding='utf-8'))
    laboratorio=[next(r for r in data['comparisons'] if r['case']==c and r['location']=='laboratorio') for c in NOMBRES if c!='escolar']
    escolar=[r for r in data['comparisons'] if r['case']=='escolar']
    (ROOT/'documentacion/resultados/mixto_tabla.tex').write_text(tabla(laboratorio,False),encoding='utf-8')
    (ROOT/'documentacion/resultados/escolar_tabla.tex').write_text(tabla(escolar,True),encoding='utf-8')
