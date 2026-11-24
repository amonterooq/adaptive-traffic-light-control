"""Compara los controles revisados sin sobrescribir los datos de la memoria."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'programa'))
from its.estudios import mixto  # noqa: E402
from its.runner import run  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'datos/resultados/revision_movimientos')
    parser.add_argument('--seeds',type=int,nargs='+',default=[101,102,103])
    parser.add_argument('--horizon',type=int,default=1800)
    parser.add_argument('--locations',nargs='+',choices=['lusitania','santa_eulalia'],default=['lusitania','santa_eulalia'])
    args=parser.parse_args()
    if args.output.exists():parser.error('La carpeta de salida ya existe; elige otra con --output.')
    if not 120<=args.horizon<=1800:parser.error('Usa entre 120 y 1800 segundos de llegadas.')
    if len(set(args.seeds))!=len(args.seeds):parser.error('No repitas semillas en la misma comparación.')
    if len(set(args.locations))!=len(args.locations):parser.error('No repitas lugares en la misma comparación.')
    args.output.mkdir(parents=True)
    records=[]
    for location in args.locations:
        for seed in args.seeds:
            pair={}
            for mode in ('fijo','adaptativo'):
                config=mixto(location,'escolar',seed,mode).model_copy(update={'horizon':args.horizon})
                target=args.output/location/str(seed)/mode
                result=run(config.scenario,mode,seed,target,**config.run_kwargs())
                if not result['completed'] or any(result[k] for k in ('collisions','teleports','ped_conflicts')):
                    raise RuntimeError(f'Ensayo incompleto o con incidentes: {target}')
                pair[mode]=result
                records.append({'location':location,'seed':seed,'mode':mode,'signal_plan':result['signal_plan'],
                                **{k:result[k] for k in ('mean_wait_s','ped_mean_wait_s','co2_mean_g')}})
                print(f'{location} · {seed} · {mode}: completado',flush=True)
            for key in ('demand_sha256','turns_sha256','fleet_sha256'):
                if pair['fijo'][key]!=pair['adaptativo'][key]:raise RuntimeError('Las entradas de la pareja no coinciden.')
    comparisons=[]
    for location in args.locations:
        row={'location':location,'seeds':args.seeds,'horizon':args.horizon}
        for metric in ('mean_wait_s','ped_mean_wait_s','co2_mean_g'):
            for mode in ('fijo','adaptativo'):
                row[mode+'_'+metric]=mean(r[metric] for r in records if r['location']==location and r['mode']==mode)
            row['diferencia_'+metric]=row['adaptativo_'+metric]-row['fijo_'+metric]
        comparisons.append(row)
    (args.output/'comparacion.json').write_text(json.dumps(comparisons,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.output/'resultados.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    print(json.dumps(comparisons,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
