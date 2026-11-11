"""Reconstruir las redes de Mérida con las coordenadas de OSM incluidas."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'programa'))
from its.locations import GEOGRAPHIC_LOCATIONS,build_geographic

if __name__=='__main__':
    for location in GEOGRAPHIC_LOCATIONS:
        for pedestrians in (False,True):
            directory,notices=build_geographic(location,pedestrians)
            print(directory.name,notices.strip())
