from contextlib import asynccontextmanager
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import csv
import io
import json
import logging
import os
import threading
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .config import ROOT, Timing, scenarios
from .runner import run
from .experimento import ExperimentConfig
from .estudios import catalogo_estudios
from .storage import Store
from .scene import geometry
from .locations import catalog, geographic
from .diagnostico import error_publico, resumen_publico, informe

Location=Literal['laboratorio','lusitania','santa_eulalia']


class RunRequest(ExperimentConfig):
    speed: int=Field(default=20,ge=1,le=100)


class Manager:
    def __init__(self,store,run_function=run):
        self.store=store
        self.run_function=run_function
        self.lock=threading.Lock()
        self.stop_event=threading.Event()
        self.thread=None
        self.current={'status':'idle','sample':None}
        self.frames=deque(maxlen=240)
        self.store.recover()

    def start(self,config):
        with self.lock:
            if self.thread and self.thread.is_alive():raise HTTPException(409,'Ya hay una ejecución activa')
            id=uuid.uuid4().hex
            data=config.model_dump()
            self.store.start(id,data)
            self.current={'id':id,'status':'running','sample':None,'config':data,'updated_at':None,
                          'paused':False,'speed':config.speed}
            self.frames.clear()
            self.stop_event.clear()
            self.thread=threading.Thread(target=self.worker,args=(id,config),daemon=True)
            self.thread.start()
            return {'id':id,'status':'running'}

    def worker(self,id,config):
        last_step=0
        def playback():
            nonlocal last_step
            while not self.stop_event.is_set():
                with self.lock:
                    paused=self.current['paused']; speed=self.current['speed']
                delay=last_step+1/speed-time.monotonic()
                if not paused and delay<=0:
                    last_step=time.monotonic()
                    return
                self.stop_event.wait(.03 if paused else min(.03,max(0,delay)))
        def frame(value):
            with self.lock:self.frames.append(value)
        def update(sample):
            self.store.sample(id,sample)
            with self.lock:
                self.current['sample']=sample
                self.current['updated_at']=datetime.now(timezone.utc).isoformat()
                self.current['monotonic']=time.monotonic()
        try:
            result=self.run_function(config.scenario,config.mode,config.seed,
                self.store.path.parent/'runs'/id, **config.run_kwargs(),
                on_step=update,should_stop=self.stop_event.is_set,pace=0,
                on_frame=frame,playback=playback)
            status='cancelled' if result['cancelled'] else ('complete' if result['completed'] else 'failed')
            self.store.finish(id,status,result)
            with self.lock:self.current.update(status=status,summary=result)
        except Exception as exc:
            logging.exception('Fallo de simulación')
            error=error_publico(exc)
            with self.lock:self.current.update(status='failed',summary=error)
            try:self.store.finish(id,'failed',error)
            except Exception:logging.exception('No se ha podido guardar el estado final en el historial')

    def snapshot(self):
        with self.lock:
            data={k:v for k,v in self.current.items() if k!='monotonic'}
            data['transport_age_s']=round(time.monotonic()-self.current['monotonic'],2) if 'monotonic' in self.current else None
            return data

    def scene(self,after,run_id):
        with self.lock:
            frames=list(self.frames)
            reset=run_id!=self.current.get('id') or (frames and after<frames[0]['time']-1)
            selected=frames[-2:] if reset else [f for f in frames if f['time']>after]
            if len(selected)>60:
                selected=selected[-2:]; reset=True
            return {'id':self.current.get('id'),'status':self.current['status'],
                    'paused':self.current.get('paused',False),'speed':self.current.get('speed',1),
                    'pedestrians':self.current.get('config',{}).get('pedestrian_profile','ocasional')!='desactivado',
                    'location':self.current.get('config',{}).get('location','laboratorio'),
                    'frames':selected,'reset':bool(reset)}

    def control(self,command):
        with self.lock:
            if self.current['status']!='running' or self.stop_event.is_set():
                raise HTTPException(409,'No hay una simulación activa')
            for key,value in command.model_dump(exclude_none=True).items():self.current[key]=value
            return {'paused':self.current['paused'],'speed':self.current['speed']}


class PlaybackRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    paused: bool | None=None
    speed: int | None=Field(default=None,ge=1,le=100)


def create_app(db_path=None,run_function=run):
    store=Store(db_path or Path(os.environ.get('ITS_DATA_DIR',ROOT/'datos/sesiones'))/'laboratorio.sqlite3')
    manager=Manager(store,run_function)

    @asynccontextmanager
    async def lifespan(app):
        yield
        manager.stop_event.set()
        if manager.thread:manager.thread.join(timeout=10)

    app=FastAPI(title='Mérida · Laboratorio de movilidad',version='1.6.0',lifespan=lifespan)
    app.state.manager=manager

    @app.middleware('http')
    async def local_origin(request: Request,call_next):
        # Local prototype: reject browser writes originating at another website.
        origin=request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS') and origin and origin != str(request.base_url).rstrip('/'):
            return Response('Origen no permitido',status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response

    @app.get('/api/studies')
    def studies():return catalogo_estudios()

    @app.get('/api/health')
    def health():return {'status':'ok','scope':'prototipo local','traffic':'simulado'}

    @app.get('/api/config')
    def config():
        return {'scenarios':scenarios(),'timing':Timing().model_dump(),
                'location':json.loads((ROOT/'datos/entrada/ubicacion.json').read_text(encoding='utf-8')),'locations':catalog()}

    @app.get('/api/state')
    def state():return manager.snapshot()

    @app.get('/api/scene')
    def scene(after:float=-1,run_id:str=''):return manager.scene(after,run_id)

    @app.get('/api/scene/network')
    def network(pedestrians:bool=True,location:Location='laboratorio'):return geometry(pedestrians,location)

    @app.get('/api/locations/metrics')
    def location_metrics():
        current=manager.snapshot()
        examples_path=ROOT/'datos/procesados/multicruce.json'
        examples=json.loads(examples_path.read_text(encoding='utf-8')).get('examples',{}) if examples_path.exists() else {}
        mixed_path=ROOT/'datos/procesados/mixto.json'
        if mixed_path.exists():
            mixed=json.loads(mixed_path.read_text(encoding='utf-8'))
            examples.update({r['config']['location']:r for r in mixed['results']
                if r['config']['location']=='santa_eulalia' and r['config']['mode']=='adaptativo' and r['config']['seed']==101})
        latest=store.latest_complete_by_location()
        points=[]
        for point in catalog():
            id=point['id'];row=latest.get(id)
            active=current.get('config',{}).get('location')==id and current['status']=='running'
            sample=current.get('sample') if active else None
            example=examples.get(id)
            points.append({**point,'active':active,'paused':active and current.get('paused',False),
                'sample':sample,'origin':'session' if row else 'example' if example else 'none',
                'last_run':row,'example':example})
        return {'traffic':'synthetic','concurrent_runs':1,'points':points}

    @app.post('/api/playback')
    def playback(command:PlaybackRequest):return manager.control(command)

    @app.post('/api/runs',status_code=201)
    def start(config:RunRequest):return manager.start(config)

    @app.post('/api/stop')
    def stop():
        manager.stop_event.set()
        return {'status':'stop_requested'}

    @app.get('/api/runs')
    def history():
        rows=store.runs()
        for row in rows:
            row['config']=json.loads(row.pop('config_json'))
            row['summary']=resumen_publico(json.loads(row.pop('summary_json') or 'null'))
        return rows

    @app.get('/api/runs/{id}/diagnostico')
    def diagnosis(id:str,descargar:bool=False):
        row=store.get_run(id)
        if row is None:raise HTTPException(404,'No existe esta ejecución en el historial')
        actual=manager.snapshot()
        if actual.get('id')==id and actual['status'] in ('failed','cancelled'):
            row.update(status=actual['status'],summary_json=json.dumps(actual.get('summary')))
        headers={'Content-Disposition':'attachment; filename="informe_simulacion.json"'} if descargar else None
        return Response(json.dumps(informe(row),ensure_ascii=False,indent=2),
                        media_type='application/json',headers=headers)

    @app.get('/api/runs/{id}/samples')
    def samples(id:str):return store.samples(id)

    @app.get('/api/runs/{id}/export')
    def export(id:str):
        rows=store.samples(id)
        if not rows:raise HTTPException(404,'No hay muestras para esta ejecución')
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
        return Response(stream.getvalue(),media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition':'attachment; filename="muestras.csv"'})

    @app.get('/api/results')
    def results():
        path=ROOT/'datos/procesados/comparacion.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'scenarios':[]}

    @app.get('/api/results/pedestrians')
    def pedestrian_results():
        path=ROOT/'datos/procesados/peatones.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'profiles':[]}

    @app.get('/api/results/mixed')
    def mixed_results():
        path=ROOT/'datos/procesados/mixto.json'
        if not path.exists():return {'comparisons':[]}
        data=json.loads(path.read_text(encoding='utf-8'))
        return {key:data[key] for key in ('runs','paired_groups','horizon','warmup','scope','comparisons')}

    @app.get('/api/map')
    def map_data(location:Location='laboratorio'):
        if location!='laboratorio':return geographic(location)['context']
        return FileResponse(ROOT/'datos/entrada/merida.geojson')

    @app.get('/')
    def index():return FileResponse(ROOT/'programa/web/index.html')

    app.mount('/web',StaticFiles(directory=ROOT/'programa/web'),name='web')
    return app
