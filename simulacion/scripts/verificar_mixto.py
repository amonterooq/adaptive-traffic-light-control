"""Recalcula las medidas desde los viajes, sin ejecutar el controlador."""
from pathlib import Path
import csv, json, math, hashlib
import xml.etree.ElementTree as ET
from statistics import mean
ROOT=Path(__file__).resolve().parents[2]


def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-8),(a,b)


def records(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def main():
    data=json.loads((ROOT/'datos/procesados/mixto.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'datos/resultados/mixto/manifest.json').read_text(encoding='utf-8'))
    assert data['runs']==manifest['runs']==len(data['results'])==72
    assert len(list((ROOT/'datos/resultados/mixto').glob('*/resumen.json')))==72
    assert {r['config']['location'] for r in data['results']}=={'laboratorio','lusitania','santa_eulalia'}
    for path,digest in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    grupos={};vehiculos=peatones=0
    for result in data['results']:
        directory=ROOT/result['directory'];s=result['summary']
        assert s==json.loads((directory/'resumen.json').read_text(encoding='utf-8'))
        assert s['model_version']=='1.6.0' and s['traffic']['emissions']
        assert s['completed'] and not s['cancelled']
        assert s['generated']==s['arrived'] and s['cohort_expected']==s['cohort_arrived']
        assert s['collisions']==s['teleports']==s.get('ped_conflicts',0)==0
        pares=[('demanda.csv','demand_sha256'),('flota.csv','fleet_sha256')]
        if 'pedestrian_demand_sha256' in s:pares.append(('demanda_peatones.csv','pedestrian_demand_sha256'))
        if 'turns_sha256' in s:pares.append(('giros.csv','turns_sha256'))
        hashes=[]
        for archivo,key in pares:
            digest=hashlib.sha256((directory/archivo).read_bytes()).hexdigest();assert digest==s[key];hashes.append(digest)
        clave=(result['config']['location'],result['case'],s['seed'])
        grupos.setdefault(clave,[]).append(hashes)
        planned={r['id']:r for r in records(directory/'demanda.csv')}
        trips=ET.parse(directory/'tripinfo.xml').getroot()
        cohort=[t for t in trips.findall('tripinfo') if s['warmup']<=float(planned[t.get('id')]['scheduled'])<s['horizon']]
        assert len(cohort)==s['cohort_expected']
        close(mean(float(t.get('waitingTime'))+float(t.get('departDelay')) for t in cohort),s['mean_wait_s'])
        emisiones=[float(t.find('emissions').get('CO2_abs'))/1000 for t in cohort]
        close(sum(emisiones),s['co2_cohort_g']);close(mean(emisiones),s['co2_mean_g'])
        if 'ped_generated' in s:
            assert s['ped_generated']==s['ped_arrived']==s['ped_crossed']
            pp={r['id']:r for r in records(directory/'demanda_peatones.csv')}
            cohort_p=[t for t in trips.findall('personinfo') if s['warmup']<=float(pp[t.get('id')]['scheduled'])<s['horizon']]
            if cohort_p:close(mean(float(t.find('walk').get('waitingTime')) for t in cohort_p),s['ped_mean_wait_s'])
        rows=records(directory/'serie.csv')
        assert [int(r['t']) for r in rows]==list(range(len(rows)))
        assert sum(int(r['arrived']) for r in rows)==s['arrived']
        assert sum(int(r['departed']) for r in rows)==s['generated']
        close(mean(int(r['queue_total']) for r in rows if s['warmup']<=int(r['t'])<s['horizon']),s['mean_queue'])
        for r in rows:
            if r.get('ped_signal')=='G' or int(r.get('ped_crossing',0)):
                assert r['state']=='rrrr'
            if r.get('camera_active'):
                assert int(r['camera_detected'])==sum(int(r['camera_'+tipo]) for tipo in ['coche','moto','bicicleta','patinete','desconocido'])
                assert int(r['fusion_approaching'])==sum(int(r['fusion_'+a]) for a in 'NESW')
                assert float(r['camera_speed_max_kmh'])>=0
        vehiculos+=s['generated'];peatones+=s.get('ped_generated',0)
    assert len(grupos)==36
    for valores in grupos.values():assert len(valores)==2 and valores[0]==valores[1]
    for row in data['comparisons']:
        for modo in ('fijo','adaptativo'):
            resumenes=[r['summary'] for r in data['results'] if r['config']['location']==row['location'] and r['case']==row['case'] and r['config']['mode']==modo]
            assert len(resumenes)==3
            for key in ('mean_wait_s','ped_mean_wait_s','co2_mean_g'):
                valores=[s.get(key) for s in resumenes if s.get(key) is not None]
                if valores:close(mean(valores),row[f'{modo}_{key}'])
                else:assert row[f'{modo}_{key}'] is None
    for seed in (101,102,103):
        for modo in ('fijo','adaptativo'):
            pares=[r['summary'] for r in data['results'] if r['config']['location']=='laboratorio' and r['case'] in ('velocidades','sin_clasificar') and r['config']['seed']==seed and r['config']['mode']==modo]
            assert len(pares)==2
            for key in ('mean_wait_s','ped_mean_wait_s','co2_mean_g'):close(pares[0][key],pares[1][key])
    report={'passed':True,'runs':72,'paired_groups':36,'vehicles':vehiculos,'persons':peatones,
            'collisions':0,'teleports':0,'pedestrian_conflicts':0,'all_source_hashes_match':True}
    print(json.dumps(report,indent=2));return report


if __name__=='__main__':main()
