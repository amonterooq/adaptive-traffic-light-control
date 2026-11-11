"""Métricas por modo de transporte; las cifras TeX proceden de los JSON."""
from pathlib import Path
import csv
import json
from statistics import mean, stdev
from scipy.stats import t as student
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
LABELS={'sin':'Sin llegadas','ocasional':'Ocasional','frecuente':'Frecuente','lento':'Marcha lenta'}


def paired(pairs,key):
    fixed=[f[key] for f,a in pairs];adaptive=[a[key] for f,a in pairs]
    if any(v is None for v in fixed+adaptive):
        assert all(v is None for v in fixed+adaptive)
        return dict(fixed_mean=None,adaptive_mean=None,delta_mean=None,ci_low=None,ci_high=None)
    delta=[a-f for a,f in zip(adaptive,fixed)]
    half=float(student.ppf(.975,len(delta)-1)*stdev(delta)/(len(delta)**.5))
    return dict(fixed_mean=mean(fixed),adaptive_mean=mean(adaptive),delta_mean=mean(delta),
                ci_low=mean(delta)-half,ci_high=mean(delta)+half)


def fmt(v):
    return '--' if v is None else f'{v:.2f}'.replace('.',',')


def main():
    records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'datos/resultados/peatones').glob('*/resumen.json'))]
    assert len(records)==80 and all(r['completed'] and r['ped_completed'] for r in records)
    profiles=[];flat=[]
    for profile,label in LABELS.items():
        pairs=[]
        for seed in range(101,111):
            pair=[]
            for mode in ['fijo','adaptativo']:
                found=[r for r in records if r['pedestrian_profile']==profile and r['mode']==mode and r['seed']==seed]
                assert len(found)==1
                pair.append(found[0])
            f,a=pair
            assert f['demand_sha256']==a['demand_sha256'] and f['pedestrian_demand_sha256']==a['pedestrian_demand_sha256']
            pairs.append(pair)
        entry=dict(profile=profile,label=label,n=10,vehicle=paired(pairs,'mean_wait_s'),pedestrian=paired(pairs,'ped_mean_wait_s'),co2=paired(pairs,'co2_mean_g'),
                   fixed_ped_max=max(f['ped_max_wait_s'] for f,a in pairs),adaptive_ped_max=max(a['ped_max_wait_s'] for f,a in pairs),
                   generated_persons_per_strategy=sum(f['ped_generated'] for f,a in pairs),
                   fixed_max_request_wait=max(f['ped_max_request_wait_s'] for f,a in pairs),
                   adaptive_max_request_wait=max(a['ped_max_request_wait_s'] for f,a in pairs))
        profiles.append(entry)
        for metric in ['vehicle','pedestrian','co2']:
            flat.append(dict(profile=profile,metric=metric,n=10,**entry[metric]))
    result={'profiles':profiles,'runs':len(records),'persons':sum(r['ped_generated'] for r in records),
            'conflicts':sum(r['ped_conflicts'] for r in records),'method':'Mean of paired run means; Student 95% CI, df=9; no multiplicity adjustment.'}
    output=ROOT/'datos/procesados'
    (output/'peatones.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,rows in [('peatones_comparacion',flat),('peatones_ejecuciones',records)]:
        with (output/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    for metric in ['vehicle','pedestrian','co2']:
        lines=[r'\begin{tabular}{lrrrr}',r'\toprule',r'Perfil & Fijo & Adaptativo & $\Delta$ & IC 95\,\% de $\Delta$\\\midrule']
        for p in profiles:
            r=p[metric];ci='--' if r['ci_low'] is None else '['+fmt(r['ci_low'])+'; '+fmt(r['ci_high'])+']'
            lines.append(p['label']+' & '+' & '.join(fmt(r[k]) for k in ['fixed_mean','adaptive_mean','delta_mean'])+' & '+ci+r'\\')
        lines.extend([r'\bottomrule',r'\end{tabular}'])
        (ROOT/'documentacion/resultados'/f'peatones_{metric}_tabla.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,4.1),layout='constrained')
    for ax,metric,title in zip(axes,['vehicle','pedestrian'],['Espera por vehículo','Espera por peatón']):
        for i,p in enumerate(profiles):
            for offset,key,color,label in [(-.18,'fixed_mean','#84968d','Fijo'),(.18,'adaptive_mean','#167266','Adaptativo')]:
                value=p[metric][key]
                if value is not None:ax.bar(i+offset,value,.34,color=color,label=label if i==(1 if metric=='pedestrian' else 0) else None)
            if p[metric]['fixed_mean'] is None:ax.text(i,3,'Sin\nllegadas',ha='center',color='#75877d',fontsize=9)
        ax.set_title(title);ax.set_ylabel('Segundos (media de diez semillas)')
        ax.set_xticks(range(4),['Sin\nllegadas','Ocasional','Frecuente','Marcha\nlenta'])
        ax.set_xlim(-.6,3.6)
        maximum=max(p[metric][k] for p in profiles for k in ['fixed_mean','adaptive_mean'] if p[metric][k] is not None)
        ax.set_ylim(0,maximum*1.25);ax.legend(frameon=False,loc='upper left')
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    for extension in ['pdf','svg']:
        fig.savefig(ROOT/'documentacion/resultados/imagenes'/f'espera_peatones.{extension}',bbox_inches='tight')
    plt.close(fig)
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
