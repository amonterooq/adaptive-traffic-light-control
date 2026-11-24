"""Genera la figura y las tablas urbanas desde los resultados agregados."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analizar_mixto import tabla

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'datos/procesados'
NAMES={'lusitania':'Lusitania','santa_eulalia':'IES Santa Eulalia','laboratorio':'Laboratorio'}
METRICS=('mean_wait_s','ped_mean_wait_s','co2_mean_g')


def read(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def num(value):return f'{value:.2f}'.replace('.',',')


def main():
    long=read('movimientos_30min.json');mixed=read('mixto.json')
    co=read('multicruce.json')
    output=ROOT/'documentacion/resultados';output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,3,figsize=(11,6.7),layout='constrained')
    for row_index,row in enumerate(long['comparisons']):
        for col,(metric,label) in enumerate(zip(METRICS,('Espera vehicular (s)','Espera peatonal (s)','CO₂ de escape (g/veh.)'))):
            ax=axes[row_index,col];values=[row[m+'_'+metric] for m in ('fijo','adaptativo')]
            errors=[[values[i]-row[m+'_min_'+metric] for i,m in enumerate(('fijo','adaptativo'))],
                    [row[m+'_max_'+metric]-values[i] for i,m in enumerate(('fijo','adaptativo'))]]
            ax.bar(['Fijo','Adaptativo'],values,color=['#637d8e','#187565'],yerr=errors,capsize=4,width=.6)
            ax.set_title(NAMES[row['location']]+'\n'+label,fontsize=11)
            ax.spines[['top','right']].set_visible(False);ax.set_ylim(bottom=0)
            ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
            for i,value in enumerate(values):ax.text(i,value/2,num(value),ha='center',va='center',color='white',fontsize=10)
    fig.suptitle('Salida escolar · 30 minutos de llegadas\nMedia de tres semillas; barras de error: mínimo y máximo entre semillas',fontsize=13)
    fig.savefig(output/'comparacion_30min.png',dpi=170);fig.savefig(output/'comparacion_30min.svg');plt.close(fig)
    svg=output/'comparacion_30min.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    profiles={'sensores':'Sensores','v2i50':'V2I 50 %','v2i100':'V2I 100 %'}
    (ROOT/'documentacion/resultados/escolar_tabla.tex').write_text(tabla([r for r in mixed['comparisons'] if r['case']=='escolar'],True),encoding='utf-8')
    (ROOT/'documentacion/resultados/escolar_30min_tabla.tex').write_text(tabla(long['comparisons'],True),encoding='utf-8')
    table=[r'\begin{tabular}{llrrr}\toprule',r'Ubicación & Adquisición & Vehículo (s) & Peatón (s) & CO$_2$ (g/veh.)\\\midrule']
    for r in co['comparisons']:
        table.append(NAMES[r['location']]+' & '+profiles[r['profile']].replace('%',r'\%')+' & '+' & '.join(num(r[k]) for k in METRICS)+r'\\')
    table.append(r'\bottomrule\end{tabular}')
    (ROOT/'documentacion/resultados/multicruce_tabla.tex').write_text('\n'.join(table)+'\n',encoding='utf-8')


if __name__=='__main__':main()
