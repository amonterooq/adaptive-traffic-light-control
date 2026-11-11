"""Compara fijo y adaptativo con la misma demanda en un laboratorio pequeño."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'programa'))
from its.runner import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'datos/resultados/ejemplo_breve')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('La carpeta de salida ya existe. Usa --output con una carpeta nueva.')
    results = {}
    for mode in ('fijo', 'adaptativo'):
        result = run('medio', mode, 101, args.output / mode,
                     horizon=120, warmup=20, max_drain=300)
        if not result['completed'] or result['collisions'] or result['teleports']:
            raise RuntimeError(f'La ejecución {mode} no cumple los criterios de finalización.')
        results[mode] = result
    if results['fijo']['demand_sha256'] != results['adaptativo']['demand_sha256']:
        raise RuntimeError('Las demandas no coinciden.')
    print(json.dumps({mode: {key: result[key] for key in
          ('generated', 'arrived', 'mean_wait_s', 'collisions', 'teleports')}
          for mode, result in results.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
