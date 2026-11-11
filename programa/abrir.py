"""Abre la aplicación local o reutiliza un servidor de la misma versión."""
import argparse
import json
import socket
import threading
import time
import urllib.request
import webbrowser
import uvicorn
from its.api import create_app


def existing_server(port):
    url=f'http://127.0.0.1:{port}'
    try:
        with urllib.request.urlopen(url+'/openapi.json',timeout=.5) as response:
            data=json.load(response)
    except (OSError,ValueError):return None
    info=data.get('info',{}) if isinstance(data,dict) else {}
    if isinstance(info,dict) and info.get('title')=='Mérida · Laboratorio de movilidad' and info.get('version')=='1.6.0':
        return url
    return None


def compatible_server(first_port=8765):
    for port in range(first_port,first_port+10):
        url=existing_server(port)
        if url:return url
    return None


def available_socket(first_port=8765):
    for port in range(first_port,first_port+10):
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1',port))
            sock.listen(128)
            return sock,port
        except OSError:sock.close()
    raise RuntimeError('Los puertos locales están ocupados. Cierra una instancia anterior e inténtalo de nuevo.')


def open_when_ready(url):
    for _ in range(50):
        try:
            with urllib.request.urlopen(url+'/api/health',timeout=.3) as response:
                if response.status==200:
                    webbrowser.open(url)
                    return
        except OSError:time.sleep(.1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    existing=compatible_server(args.port)
    if existing:
        print('La aplicación ya está abierta: '+existing,flush=True)
        if not args.no_browser:webbrowser.open(existing)
        return
    sock,port=available_socket(args.port)
    url=f'http://127.0.0.1:{port}'
    print(f'Laboratorio de movilidad: {url}\nDeja esta ventana abierta. Pulsa Ctrl+C para cerrar.',flush=True)
    if not args.no_browser:threading.Thread(target=open_when_ready,args=(url,),daemon=True).start()
    try:uvicorn.Server(uvicorn.Config(create_app(),host='127.0.0.1',port=port)).run(sockets=[sock])
    finally:sock.close()


if __name__=='__main__':main()
