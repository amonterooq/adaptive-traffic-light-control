import io
import json
from urllib.parse import urlparse
import pytest
import abrir


def respuesta(version, title='Mérida · Laboratorio de movilidad'):
    return io.BytesIO(json.dumps({'info':{'title':title,'version':version}}).encode())


@pytest.mark.parametrize('version,expected', [('1.6.0',True),('1.5.0',False),('1.4.0',False)])
def test_reutilizar_solo_la_version_actual(monkeypatch,version,expected):
    monkeypatch.setattr(abrir.urllib.request,'urlopen',lambda *a,**k:respuesta(version))
    assert abrir.existing_server(8765)==('http://127.0.0.1:8765' if expected else None)


@pytest.mark.parametrize('data', [[],{'info':None},{'info':{'title':'Otra aplicación','version':'1.6.0'}}])
def test_otro_servicio_no_se_confunde_con_el_simulador(monkeypatch,data):
    monkeypatch.setattr(abrir.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(json.dumps(data).encode()))
    assert abrir.existing_server(8765) is None


def servidores(monkeypatch,versiones):
    consultados=[]
    def abrir_url(url,**kwargs):
        port=urlparse(url).port
        consultados.append(port)
        if port not in versiones:raise OSError('Puerto sin servidor')
        return respuesta(versiones[port])
    monkeypatch.setattr(abrir.urllib.request,'urlopen',abrir_url)
    return consultados


@pytest.mark.parametrize('sin_navegador',[False,True])
def test_doble_clic_reutiliza_actual_detras_de_versiones_antiguas(monkeypatch,capsys,sin_navegador):
    consultados=servidores(monkeypatch,{8765:'1.4.0',8766:'1.5.0',8767:'1.6.0'})
    urls=[]
    monkeypatch.setattr(abrir.webbrowser,'open',urls.append)
    monkeypatch.setattr(abrir,'available_socket',lambda *_:pytest.fail('No debe abrir otro servidor'))
    monkeypatch.setattr('sys.argv',['abrir.py']+(['--no-browser'] if sin_navegador else []))
    abrir.main()
    assert consultados==[8765,8766,8767]
    assert urls==([] if sin_navegador else ['http://127.0.0.1:8767'])
    assert 'ya está abierta: http://127.0.0.1:8767' in capsys.readouterr().out


class SocketSimulado:
    def __init__(self,ocupados,intentos):
        self.ocupados=ocupados
        self.intentos=intentos
        self.cerrado=False
        self.puerto=None
        self.escuchando=False

    def bind(self,address):
        self.puerto=address[1]
        self.intentos.append(self.puerto)
        if self.puerto in self.ocupados:raise OSError('Puerto ocupado')

    def listen(self,backlog):self.escuchando=True
    def close(self):self.cerrado=True


@pytest.mark.parametrize('ocupados,libre', [({8765,8766},8767),(set(),8765)])
def test_abre_primer_puerto_libre_sin_tocar_los_servidores_antiguos(monkeypatch,capsys,ocupados,libre):
    consultados=servidores(monkeypatch,{p:'1.5.0' for p in ocupados})
    sockets=[];intentos=[];ejecutados=[]
    def socket_nuevo(*args):
        socket=SocketSimulado(ocupados,intentos)
        sockets.append(socket)
        return socket
    class ServidorSimulado:
        def __init__(self,config):self.config=config
        def run(self,*,sockets):ejecutados.append((self.config,sockets))
    monkeypatch.setattr(abrir.socket,'socket',socket_nuevo)
    monkeypatch.setattr(abrir.uvicorn,'Config',lambda app,**kwargs:{'app':app,**kwargs})
    monkeypatch.setattr(abrir.uvicorn,'Server',ServidorSimulado)
    monkeypatch.setattr(abrir,'create_app',lambda:'aplicación nueva')
    monkeypatch.setattr(abrir.webbrowser,'open',lambda *_:pytest.fail('Se pidió no abrir el navegador'))
    monkeypatch.setattr('sys.argv',['abrir.py','--no-browser'])
    abrir.main()
    assert consultados==list(range(8765,8775))
    assert intentos==list(range(8765,libre+1))
    assert len(ejecutados)==1 and ejecutados[0][0]['port']==libre
    assert ejecutados[0][1]==[sockets[-1]] and sockets[-1].escuchando
    assert all(s.cerrado for s in sockets)
    assert f'Laboratorio de movilidad: http://127.0.0.1:{libre}' in capsys.readouterr().out


def test_diez_puertos_ocupados_producen_mensaje_util(monkeypatch):
    intentos=[];sockets=[]
    def socket_nuevo(*args):
        socket=SocketSimulado(set(range(9000,9010)),intentos)
        sockets.append(socket)
        return socket
    monkeypatch.setattr(abrir.socket,'socket',socket_nuevo)
    with pytest.raises(RuntimeError,match='puertos locales están ocupados'):
        abrir.available_socket(9000)
    assert intentos==list(range(9000,9010))
    assert all(s.cerrado for s in sockets)


def test_busqueda_respeta_el_puerto_inicial(monkeypatch):
    consultados=servidores(monkeypatch,{9009:'1.6.0'})
    assert abrir.compatible_server(9000)=='http://127.0.0.1:9009'
    assert consultados==list(range(9000,9010))
