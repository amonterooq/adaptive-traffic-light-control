import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version>4:raise RuntimeError('La base de datos es de una versión posterior')
            table=db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='samples'").fetchone()
            if table and "'GGGG'" not in table['sql']:
                # SQLite no permite ampliar un CHECK con ALTER COLUMN.
                # Se copia la tabla en una transacción y se conservan sus claves.
                schema=Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
                create=next(s for s in schema.split(';') if 'CREATE TABLE IF NOT EXISTS samples (' in s)
                db.execute('PRAGMA foreign_keys=OFF')
                db.execute('BEGIN IMMEDIATE')
                db.execute(create.replace('samples (','samples_v4 (',1))
                db.execute('INSERT INTO samples_v4 SELECT * FROM samples')
                db.execute('DROP TABLE samples')
                db.execute('ALTER TABLE samples_v4 RENAME TO samples')
                if db.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('La migración no conserva las relaciones de las muestras.')
                db.commit()
                db.execute('PRAGMA foreign_keys=ON')
            db.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
            db.execute('PRAGMA journal_mode=WAL')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:yield db
        finally:db.close()

    def start(self,id,config):
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,NULL)',
                       (id,config['scenario'],config['mode'],config['seed'],datetime.now(timezone.utc).isoformat(),'running',json.dumps(config)))

    def sample(self,id,s):
        with self.connect() as db:
            db.execute('INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (id,s['t'],s['q_N'],s['q_E'],s['q_S'],s['q_W'],s['state'],int(s['fallback']),s['arrived'],s['in_network']))
            if 'ped_signal' in s:
                db.execute('INSERT INTO pedestrian_samples VALUES (?,?,?,?,?,?)',
                           (id,s['t'],s['ped_signal'],s['ped_waiting'],s['ped_crossing'],s['ped_stage']))
            if 'sensing_mode' in s:
                payload={k:v for k,v in s.items() if k.startswith(('v2x_','ped_wait_','camera_','fusion_')) or k=='sensing_mode'}
                db.execute('INSERT INTO cooperative_samples VALUES (?,?,?)',(id,s['t'],json.dumps(payload)))

    def finish(self,id,status,summary):
        with self.connect() as db:
            db.execute('UPDATE runs SET status=?,summary_json=? WHERE id=?',(status,json.dumps(summary),id))

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE runs SET status='failed',summary_json=? WHERE status='running'",
                       (json.dumps({'error':'Ejecución interrumpida por el cierre anterior del servidor'}),))

    def runs(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY created_at DESC LIMIT 100')]

    def get_run(self,id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM runs WHERE id=?',(id,)).fetchone()
            return dict(row) if row else None

    def samples(self,id):
        with self.connect() as db:
            rows=[dict(r) for r in db.execute('''SELECT s.*,p.ped_signal,p.ped_waiting,p.ped_crossing,p.ped_stage,c.payload_json
                FROM samples s LEFT JOIN pedestrian_samples p ON s.run_id=p.run_id AND s.t=p.t
                LEFT JOIN cooperative_samples c ON s.run_id=c.run_id AND s.t=c.t
                WHERE s.run_id=? ORDER BY s.t''',(id,))]
            for row in rows:row.update(json.loads(row.pop('payload_json') or '{}'))
            return rows

    def latest_complete_by_location(self):
        with self.connect() as db:
            rows=db.execute("SELECT id,created_at,config_json,summary_json FROM runs WHERE status='complete' ORDER BY created_at DESC")
            result={}
            for row in rows:
                config=json.loads(row['config_json']);location=config.get('location','laboratorio')
                if location in result:continue
                result[location]={'id':row['id'],'created_at':row['created_at'],'config':config,'summary':json.loads(row['summary_json'] or 'null')}
            return result
