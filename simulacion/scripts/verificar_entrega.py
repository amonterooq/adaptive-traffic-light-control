"""Auditoría de datos incluidos, sin modificar ni volver a simular."""
from pathlib import Path
import csv
import hashlib
import json
import math
from statistics import mean
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), (a, b)


def main():
    report = {"batteries": {}, "runs": 0, "vehicles": 0, "persons":0, "paired_demands": 0}
    expected = {"principal": 100, "sensibilidad_g20": 30,
                "sensibilidad_g40": 30, "fallo_muestras": 6, "peatones":80}
    for name, count in expected.items():
        directory = ROOT / 'datos/resultados' / name
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        for path, digest in manifest['source_sha256'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
        summaries = sorted(directory.glob('*/resumen.json'))
        assert len(summaries) == count, (name, len(summaries))
        pairs = {}
        for path in summaries:
            s = json.loads(path.read_text(encoding='utf-8'))
            assert s['completed'] and not s['cancelled'], path
            assert s['generated'] == s['arrived'], path
            assert s['cohort_expected'] == s['cohort_arrived'], path
            assert s['collisions'] == s['teleports'] == 0, path
            digest = hashlib.sha256((path.parent / 'demanda.csv').read_bytes()).hexdigest()
            assert digest == s['demand_sha256'], path
            pairs.setdefault((s['scenario'], s['seed'],s.get('pedestrian_profile')), []).append(digest)
            with (path.parent / 'demanda.csv').open(encoding='utf-8', newline='') as f:
                planned = {r['id']: r for r in csv.DictReader(f)}
            trips = ET.parse(path.parent / 'tripinfo.xml').getroot().findall('tripinfo')
            assert len(trips) == s['generated'], path
            cohort = [t for t in trips if s['warmup'] <= float(planned[t.attrib['id']]['scheduled']) < s['horizon']]
            wait = [float(t.attrib['waitingTime']) + float(t.attrib['departDelay']) for t in cohort]
            close(mean(wait), s['mean_wait_s'])
            assert s['model_version']=='1.6.0' and s['traffic']['emissions']
            fleet_digest=hashlib.sha256((path.parent/'flota.csv').read_bytes()).hexdigest()
            assert fleet_digest==s['fleet_sha256']
            pairs[(s['scenario'],s['seed'],s.get('pedestrian_profile'))][-1]+=fleet_digest
            emissions=[float(t.find('emissions').get('CO2_abs'))/1000 for t in cohort]
            close(sum(emissions),s['co2_cohort_g']);close(mean(emissions),s['co2_mean_g'])
            with (path.parent / 'serie.csv').open(encoding='utf-8', newline='') as f:
                rows = list(csv.DictReader(f))
            assert [int(r['t']) for r in rows] == list(range(len(rows))), path
            assert all(r['state'] in ('GrGr', 'rGrG', 'yryr', 'ryry', 'rrrr') for r in rows), path
            assert sum(int(r['arrived']) for r in rows) == s['arrived'], path
            assert sum(int(r['departed']) for r in rows) == s['generated'], path
            if name == 'peatones':
                assert s['ped_generated']==s['ped_arrived']==s['ped_crossed'],path
                assert s['ped_cohort_expected']==s['ped_cohort_arrived'],path
                assert s['ped_conflicts']==0 and s['ped_completed'],path
                pdigest=hashlib.sha256((path.parent/'demanda_peatones.csv').read_bytes()).hexdigest()
                assert pdigest==s['pedestrian_demand_sha256'],path
                pairs[(s['scenario'],s['seed'],s['pedestrian_profile'])][-1]+=pdigest
                with (path.parent/'demanda_peatones.csv').open(encoding='utf-8',newline='') as f:
                    planned_p={r['id']:r for r in csv.DictReader(f)}
                persons=ET.parse(path.parent/'tripinfo.xml').getroot().findall('personinfo')
                assert len(persons)==s['ped_generated'],path
                waits=[float(p.find('walk').attrib['waitingTime']) for p in persons
                       if s['warmup']<=float(planned_p[p.attrib['id']]['scheduled'])<s['horizon']]
                if waits:close(mean(waits),s['ped_mean_wait_s'])
                else:assert s['ped_mean_wait_s'] is None
                assert sum(int(r['ped_arrived']) for r in rows)==s['ped_arrived']
                for r in rows:
                    assert int(r['ped_conflict'])==0,path
                    if r['ped_signal']=='G':assert r['state']=='rrrr' and int(r['vehicles_crossing'])==0,path
                    if int(r['ped_crossing']):assert r['state']=='rrrr',path
                report['persons']+=s['ped_generated']
            if name == 'fallo_muestras' and s['mode'] == 'adaptativo':
                assert s['fallback_seconds'] == 25, path
            report['vehicles'] += s['generated']
        for key, values in pairs.items():
            assert len(values) == 2 and values[0] == values[1], key
        report['batteries'][name] = len(summaries)
        report['runs'] += len(summaries)
        report['paired_demands'] += len(pairs)
    report['passed'] = True
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    main()
