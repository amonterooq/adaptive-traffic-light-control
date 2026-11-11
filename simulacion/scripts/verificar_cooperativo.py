"""Auditar los 18 ensayos cooperativos sin ejecutar el controlador."""
from pathlib import Path
import csv
import hashlib
import json
import math
from statistics import mean
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]


def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9),(a,b)


def records(path):
    with path.open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def main():
    directory=ROOT/'datos/resultados/cooperativo'
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    for path,digest in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    data=json.loads((ROOT/'datos/procesados/multicruce.json').read_text(encoding='utf-8'))
    assert len(data['results'])==data['runs']==manifest['runs']==18
    assert len(list(directory.glob('*/resumen.json')))==18
    assert {r['config']['location'] for r in data['results']}=={'laboratorio','lusitania'}
    groups={};vehicles=persons=0
    for result in data['results']:
        folder=ROOT/result['directory'];s=json.loads((folder/'resumen.json').read_text(encoding='utf-8'))
        assert s==result['summary']
        assert s['completed'] and s['ped_completed'] and not s['cancelled']
        assert s['generated']==s['arrived'] and s['cohort_expected']==s['cohort_arrived']
        assert s['ped_generated']==s['ped_arrived']==s['ped_crossed']
        assert s['ped_cohort_expected']==s['ped_cohort_arrived']
        assert s['collisions']==s['teleports']==s['ped_conflicts']==0
        hashes=[]
        for name,key in [('demanda.csv','demand_sha256'),('demanda_peatones.csv','pedestrian_demand_sha256')]+([('giros.csv','turns_sha256')] if result['config']['location']!='laboratorio' else []):
            digest=hashlib.sha256((folder/name).read_bytes()).hexdigest()
            assert digest==s[key];hashes.append(digest)
        groups.setdefault((result['config']['location'],s['seed']),[]).append((result['profile'],hashes))
        planned={r['id']:r for r in records(folder/'demanda.csv')}
        planned_p={r['id']:r for r in records(folder/'demanda_peatones.csv')}
        root=ET.parse(folder/'tripinfo.xml').getroot()
        trips=root.findall('tripinfo');walks=root.findall('personinfo')
        assert len(trips)==s['generated'] and len(walks)==s['ped_generated']
        cohort=[t for t in trips if s['warmup']<=float(planned[t.get('id')]['scheduled'])<s['horizon']]
        close(mean(float(t.get('waitingTime'))+float(t.get('departDelay')) for t in cohort),s['mean_wait_s'])
        assert s['model_version']=='1.6.0' and s['traffic']['emissions']
        emissions=[float(t.find('emissions').get('CO2_abs'))/1000 for t in cohort]
        close(sum(emissions),s['co2_cohort_g']);close(mean(emissions),s['co2_mean_g'])
        pcohort=[p for p in walks if s['warmup']<=float(planned_p[p.get('id')]['scheduled'])<s['horizon']]
        close(mean(float(p.find('walk').get('waitingTime')) for p in pcohort),s['ped_mean_wait_s'])
        rows=records(folder/'serie.csv')
        assert [int(r['t']) for r in rows]==list(range(len(rows)))
        assert sum(int(r['arrived']) for r in rows)==s['arrived']
        assert sum(int(r['departed']) for r in rows)==s['generated']
        assert sum(int(r['ped_arrived']) for r in rows)==s['ped_arrived']
        close(mean(int(r['queue_total']) for r in rows if s['warmup']<=int(r['t'])<s['horizon']),s['mean_queue'])
        previous={key:0 for key in ('v2x_sent','v2x_received','v2x_lost','v2x_expired')}
        for r in rows:
            assert int(r['ped_conflict'])==0
            assert r['state'] in ('GrGr','rGrG','yryr','ryry','rrrr')
            if int(r['ped_crossing']) or r['ped_signal']=='G':assert r['state']=='rrrr'
            if r['ped_signal']=='G':assert int(r['vehicles_crossing'])==0
            if result['profile']!='sensores':
                assert int(r['v2x_approaching'])==sum(int(r['v2x_'+a]) for a in 'NESW')
                assert int(r['v2x_approaching'])<=int(r['v2x_fresh'])
                if r['v2x_age_max']:assert 0<=float(r['v2x_age_max'])<=3
                if r['v2x_eta_min']:assert float(r['v2x_eta_min'])>=0
                assert sum(int(r['ped_wait_'+a]) for a in 'NESW')==int(r['ped_waiting'])
                for key,value in previous.items():
                    assert int(r[key])>=value;previous[key]=int(r[key])
                assert int(r['v2x_received'])+int(r['v2x_lost'])<=int(r['v2x_sent'])
        if result['profile']!='sensores':
            for key,value in previous.items():assert value==s[key]
        vehicles+=s['generated'];persons+=s['ped_generated']
    assert len(groups)==6
    for group in groups.values():
        assert {p for p,_ in group}=={'sensores','v2i50','v2i100'}
        assert all(h==group[0][1] for _,h in group)
    csv_rows=records(ROOT/'datos/procesados/multicruce.csv')
    assert len(csv_rows)==len(data['comparisons'])==6
    for row,flat in zip(data['comparisons'],csv_rows):
        selected=[r for r in data['results'] if r['profile']==row['profile'] and r['config']['location']==row['location']]
        assert len(selected)==row['n']==3
        for key in ('mean_wait_s','ped_mean_wait_s','mean_queue','co2_mean_g'):
            close(mean(r['summary'][key] for r in selected),row[key]);close(float(flat[key]),row[key])
    for location,example in data['examples'].items():
        assert example in data['results'] and example['config']['location']==location
        assert example['profile']=='v2i50' and example['config']['seed']==101
    report={'passed':True,'runs':18,'paired_groups':6,'vehicles':vehicles,'persons':persons,
            'collisions':0,'teleports':0,'pedestrian_conflicts':0,'all_source_hashes_match':True}
    print(json.dumps(report,indent=2));return report


if __name__=='__main__':main()
