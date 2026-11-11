"""Repetir las 336 ejecuciones y actualizar las tablas de la memoria."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    trabajos = [
        ['experimentos.py'],
        ['experimentos.py', '--seeds', '101', '102', '103', '--green', '20', '--output', 'datos/resultados/sensibilidad_g20'],
        ['experimentos.py', '--seeds', '101', '102', '103', '--green', '40', '--output', 'datos/resultados/sensibilidad_g40'],
        ['experimentos.py', '--seeds', '101', '102', '103', '--scenarios', 'dinamico', '--blackout', '600', '630', '--output', 'datos/resultados/fallo_muestras'],
        ['experimentos.py', '--scenarios', 'medio', '--pedestrians', 'sin', 'ocasional', 'frecuente', 'lento', '--output', 'datos/resultados/peatones'],
        ['experimentos_cooperativos.py'], ['experimentos_mixtos.py'],
        ['verificar_entrega.py'], ['verificar_cooperativo.py'], ['verificar_mixto.py'],
        ['analizar.py'], ['analizar_peatones.py'], ['analizar_cooperativo.py'], ['analizar_mixto.py'],
    ]
    for numero, (script, *arguments) in enumerate(trabajos, 1):
        print(f'[{numero}/{len(trabajos)}] {script} {" ".join(arguments)}', flush=True)
        subprocess.run([sys.executable, str(ROOT/'simulacion/scripts'/script), *arguments], cwd=ROOT, check=True)
    print('Experimentos, auditorías y análisis completados.', flush=True)


if __name__ == '__main__':
    main()
