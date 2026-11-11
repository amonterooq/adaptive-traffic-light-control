"""Servidor local. Ejecutar desde cualquier carpeta con Python del entorno virtual."""
import argparse
import uvicorn

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    uvicorn.run('its.api:create_app',factory=True,host='127.0.0.1',port=args.port,log_level='info')
