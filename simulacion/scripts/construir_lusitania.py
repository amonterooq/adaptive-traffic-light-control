"""Rebuild both local networks from the supplied OSM-derived geography, offline."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'programa'))
from its.locations import build_lusitania

if __name__=='__main__':
    for pedestrians in (False,True):
        folder,warnings=build_lusitania(pedestrians)
        print(folder)
        if warnings:print(warnings)
