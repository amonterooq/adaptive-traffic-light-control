"""Regenerar la tabla de adquisición a partir de los ensayos auditados."""
from pathlib import Path
import json
from verificar_cooperativo import main as audit

ROOT=Path(__file__).resolve().parents[2]


def main():
    audit()
    data=json.loads((ROOT/'datos/procesados/multicruce.json').read_text(encoding='utf-8'))
    lines=[r'\begin{tabular}{llrrr}\toprule',r'Ubicación & Adquisición & Vehículo (s) & Peatón (s) & CO$_2$ (g/veh.)\\\midrule']
    names={'lusitania':'Lusitania','laboratorio':'Laboratorio'}
    profiles={'sensores':'Sensores','v2i50':r'V2I 50\,\%','v2i100':r'V2I 100\,\%'}
    for row in data['comparisons']:
        lines.append(f"{names[row['location']]} & {profiles[row['profile']]} & {row['mean_wait_s']:.2f} & {row['ped_mean_wait_s']:.2f} & {row['co2_mean_g']:.2f}".replace('.',',')+r'\\')
    lines.append(r'\bottomrule\end{tabular}')
    (ROOT/'documentacion/resultados/multicruce_tabla.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':main()
