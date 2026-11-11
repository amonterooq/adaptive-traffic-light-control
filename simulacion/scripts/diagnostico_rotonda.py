"""Comprobar ambos controles de la rotonda con treinta minutos de llegadas."""
from pathlib import Path
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'programa'))
from its.estudios import mixto
from its.runner import run


OUTPUT = ROOT/'datos/diagnostico/rotonda_escolar_30min'


def ejecutar(case):
    mode, seed = case
    config = mixto('santa_eulalia', 'escolar', seed, mode).model_copy(update={'horizon':1800})
    directory = OUTPUT/f'{mode}_{seed}'
    result = run(config.scenario, config.mode, config.seed, directory, **config.run_kwargs())
    (directory/'configuracion.json').write_text(json.dumps(config.model_dump(),indent=2),encoding='utf-8')
    return {'directory':directory.relative_to(ROOT).as_posix(), 'mode':mode, 'seed':seed,
            'completed':result['completed'], 'colliding_vehicle_count':result['collisions'],
            'teleports':result['teleports'], 'pedestrian_conflicts':result['ped_conflicts']}


def main():
    cases=[(mode,seed) for seed in (101,102,103) for mode in ('fijo','adaptativo')]
    with ProcessPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(ejecutar,cases))
    sources = list((ROOT/'programa/its').glob('*.py')) + [Path(__file__)]
    sources += [ROOT/'datos/entrada/santa_eulalia.json']
    passed=all(r['completed'] and not any(r[k] for k in ('colliding_vehicle_count','teleports','pedestrian_conflicts')) for r in results)
    report = {'runs':len(results), 'passed':passed, 'horizon':1800, 'warmup':300,
              'purpose':'Regresión del modelo de la rotonda con demanda escolar prolongada.',
              'included_in_comparisons':False, 'results':results,
              'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (OUTPUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    if not passed:raise RuntimeError('La regresión de la rotonda contiene ejecuciones no válidas.')


if __name__ == '__main__':
    main()
