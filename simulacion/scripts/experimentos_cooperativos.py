"""18 ensayos de adquisición: laboratorio y Lusitania, tres semillas y perfiles."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import sys,json,hashlib,csv
from statistics import mean
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'programa'))
from its.runner import run
from its.estudios import cooperativo
from its.locations import catalog


def task(location,seed):
    result=[]
    for profile,penetration in [('sensores',0),('v2i50',50),('v2i100',100)]:
        specification=cooperativo(location,seed,penetration)
        config=specification.model_dump()
        folder=ROOT/f'datos/resultados/cooperativo/{location}_{profile}_{seed}'
        summary=run(config['scenario'],config['mode'],seed,folder,**specification.run_kwargs())
        (folder/'configuracion.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        if not summary['completed'] or summary['collisions'] or summary['ped_conflicts']:
            raise RuntimeError(f'Ensayo no válido: {folder.name}')
        result.append({'profile':profile,'config':config,'summary':summary,'directory':folder.relative_to(ROOT).as_posix()})
    assert len({r['summary']['demand_sha256'] for r in result})==1
    assert len({r['summary']['pedestrian_demand_sha256'] for r in result})==1
    if location!='laboratorio':assert len({r['summary']['turns_sha256'] for r in result})==1
    return result


def main():
    sites=[site for site in catalog() if site['id']!='santa_eulalia'];results=[]
    with ProcessPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(task,site['id'],seed) for site in sites for seed in (101,102,103)]
        for future in as_completed(jobs):
            group=future.result();results.extend(group)
            print(group[0]['config']['location'],group[0]['config']['seed'],'completo',flush=True)
    results.sort(key=lambda r:(r['config']['location'],r['profile'],r['config']['seed']))
    comparisons=[]
    for site in sites:
        for profile in ('sensores','v2i50','v2i100'):
            rows=[r for r in results if r['config']['location']==site['id'] and r['profile']==profile]
            comparisons.append({'location':site['id'],'name':site['name'],'profile':profile,'n':len(rows),
                **{key:mean(r['summary'][key] for r in rows) for key in ('mean_wait_s','ped_mean_wait_s','mean_queue','co2_mean_g')},
                'collisions':sum(r['summary']['collisions'] for r in rows),'ped_conflicts':sum(r['summary']['ped_conflicts'] for r in rows)})
    examples={site['id']:next(r for r in results if r['config']['location']==site['id'] and r['profile']=='v2i50' and r['config']['seed']==101) for site in sites}
    data={'date':'2026-09-25','scope':'Exploración sintética; tres semillas, sin calibración de campo ni inferencia poblacional.',
          'runs':len(results),'results':results,'comparisons':comparisons,'examples':examples}
    (ROOT/'datos/procesados/multicruce.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (ROOT/'datos/procesados/multicruce.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    source_paths=list((ROOT/'programa/its').glob('*.py'))+[Path(__file__)]+list((ROOT/'datos/entrada').glob('*.json'))
    source_paths+=list((ROOT/'simulacion/escenarios').glob('**/*.json'))
    manifest={'runs':len(results),'seeds':[101,102,103],'horizon':180,'warmup':30,'pedestrians':'frecuente',
              'sensing_profiles':['sensores','v2i50','v2i100'],'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}}
    (ROOT/'datos/resultados/cooperativo/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'runs':len(results),'paired_groups':len(sites)*3,'completed':True,'collisions':0,'ped_conflicts':0}))


if __name__=='__main__':main()
