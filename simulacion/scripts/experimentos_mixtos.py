"""Ensayos pareados de tráfico mixto, cámaras, velocidades y salida escolar."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import mean
import sys, json, hashlib, csv
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'programa'))
from its.runner import run
from its.estudios import CASOS, mixto


def pareja(location,caso,seed):
    resultados=[]
    for modo in ('fijo','adaptativo'):
        specification=mixto(location,caso,seed,modo)
        config=specification.model_dump()
        carpeta=ROOT/f'datos/resultados/mixto/{location}_{caso}_{modo}_{seed}'
        resumen=run(config['scenario'],modo,seed,carpeta,**specification.run_kwargs())
        (carpeta/'configuracion.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        if not resumen['completed']:raise RuntimeError(f'Ensayo incompleto: {carpeta.name}')
        resultados.append({'case':caso,'config':config,'summary':resumen,'directory':carpeta.relative_to(ROOT).as_posix()})
    for clave in ('demand_sha256','fleet_sha256','pedestrian_demand_sha256','turns_sha256'):
        assert resultados[0]['summary'].get(clave)==resultados[1]['summary'].get(clave)
    return resultados


def main():
    tareas=[('laboratorio',c,s) for c in CASOS for s in (101,102,103)]
    tareas += [(l,'escolar',s) for l in ('lusitania','santa_eulalia') for s in (101,102,103)]
    resultados=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        trabajos={pool.submit(pareja,*t):t for t in tareas}
        for f in as_completed(trabajos):
            resultados.extend(f.result());print(*trabajos[f],'completo',flush=True)
    resultados.sort(key=lambda r:(r['config']['location'],r['case'],r['config']['seed'],r['config']['mode']))
    comparaciones=[]
    for location,caso in sorted({(r['config']['location'],r['case']) for r in resultados}):
        fila={'location':location,'case':caso,'n':3}
        for modo in ('fijo','adaptativo'):
            grupo=[r['summary'] for r in resultados if r['config']['location']==location and r['case']==caso and r['config']['mode']==modo]
            for key in ('mean_wait_s','ped_mean_wait_s','co2_mean_g'):
                valores=[r.get(key) for r in grupo if r.get(key) is not None]
                fila[f'{modo}_{key}']=mean(valores) if valores else None
        comparaciones.append(fila)
    data={'runs':len(resultados),'paired_groups':len(tareas),'horizon':180,'warmup':30,'seeds':[101,102,103],
        'scope':'Exploración sintética. Medias de tres semillas, sin calibración de campo.',
        'results':resultados,'comparisons':comparaciones}
    (ROOT/'datos/procesados/mixto.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (ROOT/'datos/procesados/mixto.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(comparaciones[0]));w.writeheader();w.writerows(comparaciones)
    fuentes=list((ROOT/'programa/its').glob('*.py'))+[Path(__file__)]+list((ROOT/'datos/entrada').glob('*.json'))
    manifest={'runs':len(resultados),'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in fuentes}}
    (ROOT/'datos/resultados/mixto/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'runs':len(resultados),'completed':True}))


if __name__=='__main__':main()
