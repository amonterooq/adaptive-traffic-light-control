"""Agregación pareada; ninguna cifra se define a mano."""
from pathlib import Path
import sys, csv, json
from statistics import mean, stdev
import numpy as np
from scipy.stats import t as student
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'programa'))
from its.config import scenarios

NAMES={'bajo':'Baja','medio':'Media','alto':'Alta','desequilibrado':'Desigual','dinamico':'Cambiante'}
COLORS=['#84968d','#167266']
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,
                     'axes.labelcolor':'#263e36','text.color':'#263e36','savefig.facecolor':'white','pdf.fonttype':42})


def csv_write(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def aggregates(folder):
    records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*/resumen.json'))]
    if not records:return [],[]
    if any(not r['completed'] for r in records):raise ValueError('No se agregan experimentos incompletos')
    results=[]
    for scenario in scenarios()['scenarios']:
        subset=[r for r in records if r['scenario']==scenario]
        if not subset:continue
        seeds=sorted({r['seed'] for r in subset})
        pairs=[]
        for seed in seeds:
            a=[r for r in subset if r['seed']==seed and r['mode']=='adaptativo']
            f=[r for r in subset if r['seed']==seed and r['mode']=='fijo']
            if len(a)!=1 or len(f)!=1:raise ValueError('Pareja de semillas ausente o duplicada')
            if a[0]['demand_sha256']!=f[0]['demand_sha256']:raise ValueError('Demanda no pareada')
            pairs.append((f[0],a[0]))
        fixed=[f['mean_wait_s'] for f,a in pairs];adaptive=[a['mean_wait_s'] for f,a in pairs]
        delta=[a-f for a,f in zip(adaptive,fixed)]
        half=float(student.ppf(.975,len(delta)-1)*stdev(delta)/len(delta)**.5) if len(delta)>1 else 0
        results.append({'scenario':scenario,'n':len(pairs),'fixed_mean':mean(fixed),'adaptive_mean':mean(adaptive),
                        'delta_mean':mean(delta),'ci_low':mean(delta)-half,'ci_high':mean(delta)+half,
                        'relative_change_pct':100*(mean(adaptive)-mean(fixed))/mean(fixed),
                        'fixed_queue':mean(f['mean_queue'] for f,a in pairs),
                        'adaptive_queue':mean(a['mean_queue'] for f,a in pairs),
                        'fixed_throughput':mean(f['throughput_vph'] for f,a in pairs),
                        'adaptive_throughput':mean(a['throughput_vph'] for f,a in pairs),
                        'fixed_p95':mean(f['p95_wait_s'] for f,a in pairs),
                        'adaptive_p95':mean(a['p95_wait_s'] for f,a in pairs)})
        cf=[f['co2_mean_g'] for f,a in pairs];ca=[a['co2_mean_g'] for f,a in pairs]
        cd=[a-f for f,a in zip(cf,ca)]
        ch=float(student.ppf(.975,len(cd)-1)*stdev(cd)/len(cd)**.5) if len(cd)>1 else 0
        results[-1].update(fixed_co2=mean(cf),adaptive_co2=mean(ca),co2_delta_mean=mean(cd),
                           co2_ci_low=mean(cd)-ch,co2_ci_high=mean(cd)+ch,
                           co2_relative_change_pct=100*(mean(ca)-mean(cf))/mean(cf))
    return records,results


def savefig(fig,name):
    path=ROOT/'documentacion/resultados/imagenes'
    fig.savefig(path/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(path/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def main():
    processed=ROOT/'datos/procesados';processed.mkdir(exist_ok=True)
    records,results=aggregates(ROOT/'datos/resultados/principal')
    csv_write(processed/'comparacion.csv',results)
    fields=['scenario','mode','seed','generated','arrived','cohort_expected','mean_wait_s','mean_stopped_s','mean_insert_delay_s','p95_wait_s','mean_travel_s','mean_stops','mean_queue','max_queue','throughput_vph','fallback_seconds','collisions','teleports','co2_mean_g','co2_cohort_g','fleet_sha256','model_version']
    csv_write(processed/'ejecuciones.csv',[{k:r[k] for k in fields} for r in records])
    (processed/'comparacion.json').write_text(json.dumps({'definition':'Diferencia adaptativo menos fijo; medias de ejecuciones con igual peso; IC Student pareado 95%; n=10, sin corrección múltiple.','scenarios':results,'executions':records},ensure_ascii=False,indent=2),encoding='utf-8')
    phase_rows=[]
    for r in records:
        folder=ROOT/'datos/resultados/principal'/f"{r['scenario']}_{r['mode']}_{r['seed']}"
        rows=list(csv.DictReader((folder/'serie.csv').open(encoding='utf-8')))
        measure=[s for s in rows if r['warmup']<=int(s['t'])<r['horizon']]
        phase_rows.append({'scenario':r['scenario'],'mode':r['mode'],'seed':r['seed'],
                           'green_fraction':sum('G' in s['state'] for s in measure)/len(measure),
                           'transitions':sum(rows[i]['state']!=rows[i-1]['state'] for i in range(1,len(rows)) if r['warmup']<=int(rows[i]['t'])<r['horizon']),
                           'mean_insert_delay_s':r['mean_insert_delay_s']})
    csv_write(processed/'fases.csv',phase_rows)
    additional=[]
    for name in ['sensibilidad_g20','sensibilidad_g40','fallo_muestras']:
        _,stats=aggregates(ROOT/'datos/resultados'/name)
        additional.extend([{'experiment':name,**r} for r in stats])
    csv_write(processed/'complementarios.csv',additional)
    (processed/'complementarios.json').write_text(json.dumps(additional,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,5,figsize=(11,3.2),layout='constrained')
    for ax,r in zip(axes,results):
        for mode,x,color in [('fijo',0,COLORS[0]),('adaptativo',1,COLORS[1])]:
            vals=[v['mean_wait_s'] for v in records if v['scenario']==r['scenario'] and v['mode']==mode]
            ax.bar(x,mean(vals),width=.6,color=color,zorder=2)
            ax.scatter(np.linspace(x-.15,x+.15,len(vals)),vals,s=12,color='#243d35',zorder=3)
        ax.set_title(NAMES[r['scenario']]);ax.set_xticks([0,1],['Fijo','Adapt.']);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.15,zorder=0)
    axes[0].set_ylabel('Espera media (s/vehículo)')
    fig.suptitle('Misma demanda; diez semillas por escenario. Escalas verticales independientes.',fontsize=11)
    savefig(fig,'espera_escenarios')
    fig,axes=plt.subplots(2,1,figsize=(9,5.6),sharex=True,layout='constrained')
    trace_rows=[]
    for mode,color in zip(['fijo','adaptativo'],COLORS):
        folder=ROOT/'datos/resultados/principal'/f'alto_{mode}_101'
        rows=list(csv.DictReader((folder/'serie.csv').open()))
        rows=[s for s in rows if int(s['t'])<1800]
        axes[0].plot([int(s['t'])/60 for s in rows],[int(s['queue_total']) for s in rows],color=color,label=mode.title(),lw=1.2)
        ns=[int(s['q_N'])+int(s['q_S']) for s in rows]
        axes[1].plot([int(s['t'])/60 for s in rows],ns,color=color,label=mode.title(),lw=1.2)
        trace_rows.extend([{'mode':mode,'t':s['t'],'queue_total':s['queue_total'],'queue_NS':q} for s,q in zip(rows,ns)])
    for ax in axes:ax.axvspan(0,5,color='#d7e2d2',alpha=.5);ax.legend();ax.grid(alpha=.15)
    axes[0].set_ylabel('Cola total (vehículos)');axes[1].set_ylabel('Cola N/S (vehículos)');axes[1].set_xlabel('Tiempo simulado (min)')
    axes[0].set_title('Demanda alta, semilla 101. Sombreado: calentamiento.')
    savefig(fig,'colas_alta');csv_write(processed/'grafica_colas_alta.csv',trace_rows)
    fig,ax=plt.subplots(figsize=(8.3,3.4),layout='constrained')
    x=np.arange(len(results));width=.35
    for mode,offset,color in [('fijo',-.175,COLORS[0]),('adaptativo',.175,COLORS[1])]:
        vals=[mean(r['green_fraction'] for r in phase_rows if r['scenario']==s['scenario'] and r['mode']==mode)*100 for s in results]
        ax.bar(x+offset,vals,width,label=mode.title(),color=color)
    ax.set_xticks(x,[NAMES[r['scenario']] for r in results]);ax.set_ylim(0,100);ax.set_ylabel('Tiempo con algún eje en verde (%)');ax.legend();ax.grid(axis='y',alpha=.15)
    savefig(fig,'fraccion_verde')
    tex=[]
    for r in results:
        f=lambda x:f'{x:.2f}'.replace('.',',')
        tex.append(f"{NAMES[r['scenario']]} & {f(r['fixed_mean'])} & {f(r['adaptive_mean'])} & {f(r['delta_mean'])} & [{f(r['ci_low'])}; {f(r['ci_high'])}] \\\\")
    table = ('\\begin{tabular}{lrrrr}\\toprule\n'
             'Escenario & Fijo & Adaptativo & Diferencia & IC 95\\,\\% diferencia\\\\\\midrule\n'
             + '\n'.join(tex) + '\n\\bottomrule\n\\end{tabular}\n')
    (ROOT/'documentacion/resultados/resultados_tabla.tex').write_text(table,encoding='utf-8')
    macros=[]
    for r in results:
        key=r['scenario'].capitalize()
        for label,col in [('Fijo','fixed_mean'),('Adaptativo','adaptive_mean'),('Cambio','relative_change_pct')]:
            macros.append('\\newcommand{\\'+key+label+'}{'+f'{r[col]:.2f}'.replace('.',',')+'}')
    (ROOT/'documentacion/resultados/resultados_macros.tex').write_text('\n'.join(macros),encoding='utf-8')

    def number(value):return f'{value:.2f}'.replace('.',',')
    def table(name,header,rows,columns):
        lines=[r'\begin{tabular}{'+columns+r'}\toprule',header+r'\\\midrule']
        lines.extend(' & '.join(str(v) for v in row)+r'\\' for row in rows)
        lines.append(r'\bottomrule\end{tabular}')
        (ROOT/'documentacion/resultados'/name).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    table('emisiones_tabla.tex',r'Escenario & Fijo & Adaptativo & $\Delta$ & IC 95\,\% de $\Delta$',
          [[NAMES[r['scenario']],number(r['fixed_co2']),number(r['adaptive_co2']),number(r['co2_delta_mean']),
            '['+number(r['co2_ci_low'])+'; '+number(r['co2_ci_high'])+']'] for r in results],'lrrrr')
    table('colas_flujo_tabla.tex',r'Escenario & Cola F & Cola A & Flujo F & Flujo A',
          [[NAMES[r['scenario']]]+[number(r[k]) for k in ('fixed_queue','adaptive_queue','fixed_throughput','adaptive_throughput')] for r in results],'lrrrr')
    table('sensibilidad_tabla.tex',r'Verde fijo & Escenario & Espera F & Espera A & CO$_2$ F & CO$_2$ A',
          [[r['experiment'].replace('sensibilidad_g','')+' s',NAMES[r['scenario']]]+
           [number(r[k]) for k in ('fixed_mean','adaptive_mean','fixed_co2','adaptive_co2')]
           for r in additional if r['experiment'].startswith('sensibilidad')],'llrrrr')
    fig,ax=plt.subplots(figsize=(8.3,3.6),layout='constrained')
    for key,offset,color,label in [('fixed_co2',-.18,COLORS[0],'Fijo'),('adaptive_co2',.18,COLORS[1],'Adaptativo')]:
        ax.bar(np.arange(len(results))+offset,[r[key] for r in results],.36,color=color,label=label)
    ax.set_xticks(range(len(results)),[NAMES[r['scenario']] for r in results])
    ax.set_ylabel('CO₂ de escape (g/vehículo)');ax.set_ylim(bottom=0);ax.legend();ax.grid(axis='y',alpha=.15)
    savefig(fig,'emisiones_escenarios')

    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
