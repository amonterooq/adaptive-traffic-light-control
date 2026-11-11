import csv
import pytest
from its.runner import run, summarize


@pytest.mark.integration
def test_sumo_paired_and_conservation(tmp_path):
    metrics=[]
    for mode in ['fijo','adaptativo']:
        result=run('medio',mode,101,tmp_path/mode,horizon=120,warmup=20,max_drain=300)
        metrics.append(result)
        assert result['completed']
        assert result['generated']==result['arrived']
        assert result['collisions']==result['teleports']==0
        assert result['mean_wait_s']>=0
        assert result['mean_wait_s']==pytest.approx(result['mean_stopped_s']+result['mean_insert_delay_s'])
        with (tmp_path/mode/'serie.csv').open() as f:rows=list(csv.DictReader(f))
        assert sum(int(r['departed']) for r in rows)==result['generated']
        assert sum(int(r['arrived']) for r in rows)==result['generated']
    assert metrics[0]['demand_sha256']==metrics[1]['demand_sha256']


@pytest.mark.integration
def test_sumo_outage_and_recovery(tmp_path):
    result=run('medio','adaptativo',102,tmp_path,horizon=120,warmup=20,max_drain=300,blackout=(40,70))
    assert result['completed'] and result['fallback_seconds']==25
    rows=list(csv.DictReader((tmp_path/'serie.csv').open()))
    assert rows[69]['fallback']=='1' and rows[70]['fallback']=='0'


def test_metric_cohort_excludes_warmup_and_preserves_censoring(tmp_path):
    (tmp_path/'tripinfo.xml').write_text('''<tripinfos>
      <tripinfo id="a" depart="0" arrival="40" waitingTime="8" departDelay="0" duration="40" timeLoss="10" waitingCount="1"/>
      <tripinfo id="b" depart="25" arrival="90" waitingTime="20" departDelay="5" duration="65" timeLoss="30" waitingCount="2"/>
    </tripinfos>''')
    vehicles=[{'id':'a','arm':'N','scheduled':0},{'id':'b','arm':'E','scheduled':20},{'id':'c','arm':'S','scheduled':30}]
    rows=[{'t':t,'queue_total':2,'teleports':0,'collisions':0,'fallback':0} for t in range(100)]
    r=summarize(tmp_path,vehicles,rows,10,60,{})
    assert r['mean_wait_s']==25
    assert r['cohort_expected']==2 and r['cohort_arrived']==1
    assert not r['completed']
