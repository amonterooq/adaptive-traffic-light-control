"""Ejecutar desde la raíz: python simulacion/scripts/experimentos.py."""
from pathlib import Path
import sys, argparse, json, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'programa'))
from its.config import scenarios
from its.estudios import referencia
from its.network import build_network
from its.runner import run


def pair(task):
    scenario,seed,profile,output,green,blackout=task
    results=[]
    for mode in ['fijo','adaptativo']:
        prefix='' if profile=='desactivado' else profile+'_'
        path=Path(output)/f'{prefix}{scenario}_{mode}_{seed}'
        config=referencia(scenario,mode,seed,profile,green,blackout)
        result=run(scenario,mode,seed,path,**config.run_kwargs())
        (path/'configuracion.json').write_text(json.dumps(config.model_dump(),indent=2),encoding='utf-8')
        if not result['completed']:raise RuntimeError(f'Ejecución incompleta: {path}')
        results.append(result)
    assert results[0]['demand_sha256']==results[1]['demand_sha256']
    assert results[0]['fleet_sha256']==results[1]['fleet_sha256']
    if profile!='desactivado':
        assert results[0]['pedestrian_demand_sha256']==results[1]['pedestrian_demand_sha256']
    return scenario,seed,profile,[(r['mode'],round(r['mean_wait_s'],2),r.get('ped_mean_wait_s')) for r in results]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',type=int,nargs='+')
    parser.add_argument('--scenarios',nargs='+')
    parser.add_argument('--output',type=Path,default=ROOT/'datos/resultados/principal')
    parser.add_argument('--green',type=int,default=30,help='Verde fijo y de respaldo; sensibilidad al referente')
    parser.add_argument('--blackout',type=int,nargs=2)
    parser.add_argument('--pedestrians',nargs='+',choices=['desactivado','sin','ocasional','frecuente','lento'],default=['desactivado'])
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    config=scenarios()
    build_network()
    if any(p!='desactivado' for p in args.pedestrians):build_network(pedestrians=True)
    args.output.mkdir(parents=True,exist_ok=True)
    sources={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
             for folder,pattern in [('programa/its','*.py'),('simulacion/escenarios','*.json')]
             for p in (ROOT/folder).rglob(pattern)}
    manifest={'seeds':args.seeds or config['seeds'],'scenarios':args.scenarios or list(config['scenarios']),
              'config':config,'source_sha256':sources,'fixed_green':args.green,'blackout':args.blackout,
              'pedestrian_profiles':args.pedestrians}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    tasks=[(s,n,p,str(args.output.resolve()),args.green,args.blackout)
           for s in manifest['scenarios'] for n in manifest['seeds'] for p in args.pedestrians]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in as_completed([pool.submit(pair,task) for task in tasks]):
            print(result.result(),flush=True)


if __name__=='__main__':main()
