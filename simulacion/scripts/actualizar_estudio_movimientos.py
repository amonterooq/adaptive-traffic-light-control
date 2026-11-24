"""Recalcula la extensión urbana y conserva los resultados de la entrega."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'programa'))
from its.experimento import ExperimentConfig  # noqa: E402
from its.estudios import mixto  # noqa: E402
from its.runner import run  # noqa: E402

PROCESADOS=ROOT/'datos/procesados'
HISTORICO=PROCESADOS/'historico_v1_6'
SALIDA=ROOT/'datos/resultados/estudio_movimientos'
PLANES={'lusitania':'lusitania_movimientos_v3','santa_eulalia':'santa_eulalia_pasos_v2'}
METRICAS=('mean_wait_s','ped_mean_wait_s','co2_mean_g')
ARCHIVOS=('multicruce.json','multicruce.csv','mixto.json','mixto.csv','resumenes_336.json')


def leer(path):
    return json.loads(path.read_text(encoding='utf-8'))


def guardar(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def csv_guardar(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def comprobar(folder,s):
    assert s['completed'] and not s['cancelled'],folder
    assert s['generated']==s['arrived'] and s['cohort_expected']==s['cohort_arrived'],folder
    assert s['ped_generated']==s['ped_arrived']==s['ped_crossed'],folder
    assert s['ped_cohort_expected']==s['ped_cohort_arrived'],folder
    assert s['signal_plan']==PLANES[s['location']],folder
    assert not any(s[k] for k in ('collisions','teleports','ped_conflicts')),folder
    for file,key in [('demanda.csv','demand_sha256'),('flota.csv','fleet_sha256'),
                     ('giros.csv','turns_sha256'),('demanda_peatones.csv','pedestrian_demand_sha256')]:
        assert hashlib.sha256((folder/file).read_bytes()).hexdigest()==s[key],folder
    def rows(name):
        with (folder/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    planned={r['id']:r for r in rows('demanda.csv')}
    people={r['id']:r for r in rows('demanda_peatones.csv')}
    root=ET.parse(folder/'tripinfo.xml').getroot()
    cohort=[t for t in root.findall('tripinfo') if s['warmup']<=float(planned[t.get('id')]['scheduled'])<s['horizon']]
    pcohort=[p for p in root.findall('personinfo') if s['warmup']<=float(people[p.get('id')]['scheduled'])<s['horizon']]
    measured={'mean_wait_s':mean(float(t.get('waitingTime'))+float(t.get('departDelay')) for t in cohort),
              'co2_mean_g':mean(float(t.find('emissions').get('CO2_abs'))/1000 for t in cohort),
              'ped_mean_wait_s':mean(float(p.find('walk').get('waitingTime')) for p in pcohort)}
    for k,v in measured.items():assert math.isclose(v,s[k],rel_tol=1e-9,abs_tol=1e-8),(folder,k)
    series=rows('serie.csv')
    assert sum(int(r['arrived']) for r in series)==s['arrived']
    assert sum(int(r['departed']) for r in series)==s['generated']
    assert all(int(r['ped_conflict'])==0 for r in series)
    assert [int(r['t']) for r in series]==list(range(len(series)))


def tarea(job):
    revision,name,config,original=job
    specification=ExperimentConfig(**config)
    folder=SALIDA/revision/name
    if (folder/'configuracion.json').exists() and leer(folder/'configuracion.json')==config and (folder/'resumen.json').exists():
        summary=leer(folder/'resumen.json')
    else:
        if folder.exists():raise RuntimeError(f'Hay una ejecución incompleta o distinta en {folder}')
        summary=run(config['scenario'],config['mode'],config['seed'],folder,**specification.run_kwargs())
        guardar(folder/'configuracion.json',config)
    comprobar(folder,summary)
    if original:
        for key in ('demand_sha256','fleet_sha256','turns_sha256','pedestrian_demand_sha256'):
            assert summary[key]==original[key],(name,key)
    return name,{'config':config,'summary':summary,'directory':folder.relative_to(ROOT).as_posix()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=3,choices=range(1,5))
    args=parser.parse_args()
    HISTORICO.mkdir(exist_ok=True)
    for name in ARCHIVOS:
        dest=HISTORICO/name
        if not dest.exists():shutil.copy2(PROCESADOS/name,dest)
    base={name:leer(HISTORICO/name) for name in ARCHIVOS if name.endswith('.json')}
    jobs=[];names={}
    for dataset in ('multicruce.json','mixto.json'):
        for r in base[dataset]['results']:
            if r['config']['location'] not in PLANES:continue
            name=('cooperativo_' if dataset=='multicruce.json' else 'mixto_')+Path(r['directory']).name
            names[r['directory']]=name
            jobs.append((name,r['config'],r['summary']))
    assert len(jobs)==21
    for location in PLANES:
        for seed in (101,102,103):
            for mode in ('fijo','adaptativo'):
                config=mixto(location,'escolar',seed,mode).model_copy(update={'horizon':1800}).model_dump()
                jobs.append((f'largo_{location}_{mode}_{seed}',config,None))
    # Las ejecuciones de una lógica anterior no se reutilizan al revisar las fases.
    sources=[ROOT/'programa/its'/name for name in (
        'runner.py','controller.py','lusitania.py','movimientos.py','pedestrians.py',
        'rotonda.py','demand.py','trafico.py','cooperative.py','camaras.py','config.py')]
    sources+=sorted((ROOT/'simulacion/escenarios').glob('**/red.net.xml'))
    revision=hashlib.sha256(b''.join(p.read_bytes() for p in sources)).hexdigest()[:12]
    results={}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(tarea,(revision,*j)) for j in jobs]
        for future in as_completed(futures):
            name,row=future.result();results[name]=row
            print(f'{len(results)}/{len(jobs)} · {name} verificado',flush=True)
    for location in PLANES:
        for seed in (101,102,103):
            pair=[results[f'largo_{location}_{mode}_{seed}']['summary'] for mode in ('fijo','adaptativo')]
            for key in ('demand_sha256','fleet_sha256','turns_sha256','pedestrian_demand_sha256'):
                assert pair[0][key]==pair[1][key]
    date=datetime.now(timezone.utc).date().isoformat()
    changes=[];replacements={}
    for dataset in ('multicruce.json','mixto.json'):
        data=base[dataset]
        for r in data['results']:
            if r['directory'] not in names:continue
            revised=results[names[r['directory']]]
            changes.append({'dataset':dataset,'location':r['config']['location'],'seed':r['config']['seed'],
                'mode':r['config']['mode'],'case':r.get('case',r.get('profile')),
                **{prefix+k:summary[k] for prefix,summary in [('anterior_',r['summary']),('actual_',revised['summary'])] for k in METRICAS}})
            replacements[r['directory']+'/resumen.json']={'source':revised['directory']+'/resumen.json','summary':revised['summary']}
            r.update(revised)
        if dataset=='multicruce.json':
            for row in data['comparisons']:
                chosen=[r['summary'] for r in data['results'] if r['config']['location']==row['location'] and r['profile']==row['profile']]
                for k in (*METRICAS,'mean_queue'):row[k]=mean(s[k] for s in chosen)
            data['examples']={loc:next(r for r in data['results'] if r['config']['location']==loc and r['profile']=='v2i50' and r['config']['seed']==101) for loc in data['examples']}
        else:
            for row in data['comparisons']:
                for mode in ('fijo','adaptativo'):
                    chosen=[r['summary'] for r in data['results'] if r['config']['location']==row['location'] and r['case']==row['case'] and r['config']['mode']==mode]
                    for k in METRICAS:
                        values=[s[k] for s in chosen if s.get(k) is not None]
                        row[mode+'_'+k]=mean(values) if values else None
        data.update(revised_at=date,scope='Estudio sintético: extensión urbana recalculada con control por movimientos; laboratorio conservado. Tres semillas, 180 s de llegadas y 30 s de calentamiento.')
    summaries=[replacements.get(r['source'],r) for r in base['resumenes_336.json']]
    assert len(summaries)==336 and len(replacements)==21
    long=[results[n] for n in sorted(results) if n.startswith('largo_')]
    comparisons=[]
    for location in PLANES:
        row={'location':location,'case':'escolar','n':3}
        for mode in ('fijo','adaptativo'):
            selected=[r['summary'] for r in long if r['config']['location']==location and r['config']['mode']==mode]
            for k in METRICAS:
                row[mode+'_'+k]=mean(s[k] for s in selected)
                row[mode+'_min_'+k]=min(s[k] for s in selected)
                row[mode+'_max_'+k]=max(s[k] for s in selected)
        for k in METRICAS:row['delta_pct_'+k]=100*(row['adaptativo_'+k]/row['fijo_'+k]-1)
        comparisons.append(row)
    # Solo se actualizan los agregados una vez validados todos los ensayos.
    for dataset in ('multicruce.json','mixto.json'):
        guardar(PROCESADOS/dataset,base[dataset]);csv_guardar(PROCESADOS/dataset.replace('.json','.csv'),base[dataset]['comparisons'])
    guardar(PROCESADOS/'resumenes_336.json',summaries)
    data={'date':date,'runs':12,'seeds':[101,102,103],'horizon':1800,'warmup':300,
          'scope':'Salida escolar sintética. Comparación exploratoria de tres semillas; no estimación de tráfico real.',
          'results':long,'comparisons':comparisons}
    guardar(PROCESADOS/'movimientos_30min.json',data)
    csv_guardar(PROCESADOS/'movimientos_30min.csv',comparisons)
    csv_guardar(PROCESADOS/'cambios_control.csv',changes)
    guardar(PROCESADOS/'revision_estudio.json',{'date':date,'recomputed':21,'unchanged_laboratory':315,'additional_long_runs':12,
        'checked_from_tripinfo':True,'same_inputs_as_previous':True,'collisions':0,'teleports':0,'pedestrian_conflicts':0})
    print(json.dumps(comparisons,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
