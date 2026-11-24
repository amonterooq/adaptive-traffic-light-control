# Control semafórico adaptativo

Proyecto del TFG de Ingeniería Telemática de Ana Montero Preciado, Universidad
de Extremadura: **Arquitectura y simulación de un sistema ITS de control
semafórico adaptativo para la reducción de emisiones de CO₂**.

La aplicación permite observar vehículos y peatones en una simulación y comparar
un control semafórico fijo con uno adaptativo. Se estudian las esperas, las colas
y las emisiones de escape estimadas por SUMO. Incluye un cruce de laboratorio y
dos emplazamientos de Mérida: Lusitania con Antonio Hernández Gil y la rotonda
de Reina Sofía junto al IES Santa Eulalia.

![Simulación de Lusitania](documentacion/capturas/lusitania_movimientos.png)

## Instalación y ejecución

Se necesita **Windows y Python 3.12 de 64 bits**. La primera instalación requiere
conexión a Internet. SUMO se instala con las dependencias; no hace falta comprar
sensores ni otros dispositivos.

Descarga y extrae el proyecto. Puedes abrir **Iniciar aplicación.cmd**, que prepara
el entorno y abre el navegador. También puedes instalarlo desde PowerShell,
en la carpeta del proyecto:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe programa/abrir.py
```

La dirección habitual es `http://127.0.0.1:8765`. Si el puerto está ocupado,
el lanzador busca otro libre. Mantén abierta la ventana del servidor mientras
usas la aplicación y pulsa **Ctrl+C** para cerrarlo. Cerrar el navegador no detiene
el servidor. Si el archivo `.cmd` no encuentra Python, utiliza la instalación
manual anterior, comprobando que `python --version` indica 3.12.

Para iniciar sin abrir una pestaña o elegir otro puerto:

```powershell
.\.venv\Scripts\python.exe programa/abrir.py --no-browser
.\.venv\Scripts\python.exe programa/abrir.py --port 8766
```

## Cómo utilizar la aplicación

1. Elige el laboratorio, Lusitania o Santa Eulalia en las tarjetas.
2. Para una primera prueba, selecciona tráfico moderado, peatones frecuentes,
   dos minutos de llegadas y reproducción a 5×.
3. Elige el control fijo o adaptativo y pulsa **Iniciar simulación**.
4. Puedes pausar, ampliar el dibujo o seleccionar un vehículo o peatón para
   consultar sus datos. **Desfijar** cierra su ficha.
5. Espera a **Completada**. Tras terminar las llegadas, la simulación continúa
   hasta vaciar la red.
6. Repite con la misma semilla y las mismas opciones, cambiando solo el control,
   y compara ambas ejecuciones en el historial.

La velocidad de reproducción solo cambia lo rápido que ves la simulación.
Dos minutos sirven para observar el funcionamiento, pero no equivalen a los
ensayos de treinta minutos del estudio. El escenario de demanda cambiante
modifica sus llegadas en los minutos 10 y 20.

El selector de estudios carga las opciones y las semillas de los experimentos
incluidos. Para reproducir una media hay que ejecutar todas sus semillas.
**Comparar resultados** muestra las tablas incluidas, separando ensayos cortos
y largos. El historial guarda tus ejecuciones y permite descargar sus series
en CSV. Si un ensayo falla, **Abrir informe** muestra el motivo y sus opciones.

Las sesiones se guardan en `datos/sesiones/laboratorio.sqlite3`. La variable
`ITS_DATA_DIR` permite utilizar otra carpeta. Las sesiones y las salidas de
simulación se generan localmente y no se incluyen en el repositorio.

## Funcionamiento

Python controla SUMO mediante TraCI. Los detectores virtuales, la cámara emulada
y los mensajes V2I aportan observaciones al controlador. FastAPI sirve la interfaz
web y SQLite guarda el historial. La cámara y la comunicación con vehículos son
simuladas; se pueden variar la participación V2I, el alcance, el retardo y las pérdidas.
Las versiones utilizadas están en [requirements-lock.txt](requirements-lock.txt).

- **Fijo:** utiliza tiempos predefinidos.
- **Adaptativo:** decide según colas, aproximaciones y solicitudes peatonales,
  respetando tiempos mínimos, máximos y de despeje. No optimiza directamente el CO₂.

En el laboratorio se alternan los ejes norte-sur y este-oeste, con una fase
peatonal exclusiva. En Lusitania se alternan las entradas; cada una puede permitir
recto, izquierda y derecha. Los peatones cruzan junto a movimientos compatibles.
Durante el verde completo del este pueden abrirse por separado la derecha del
sur y la del norte; esta última cede al recto del este porque comparten salida.
Las aperturas auxiliares son de 6 s y no se habilitan durante el servicio peatonal.
En Santa Eulalia cada paso regula su acceso y salida de forma independiente.

Los valores predeterminados son 10–50 s de verde adaptativo, 30 s de verde fijo,
3 s de amarillo y al menos 2 s de todo-rojo. Si faltan observaciones durante más
de 5 s, se utiliza temporización de respaldo. Antes de abrir movimientos
incompatibles se comprueba el despeje. Los tiempos y la regulación urbana son
hipótesis del modelo, no una reproducción medida de los semáforos municipales.

## Estudio y resultados

El estudio incluye **348 ejecuciones**. La batería base contiene 336: cinco
demandas (100), sensibilidad a los tiempos de verde (60), pérdida de observaciones
(6), perfiles peatonales (80), detección cooperativa (18) y tráfico mixto (72).
Se añaden doce ensayos urbanos de treinta minutos.

Tras corregir los giros y los pasos peatonales, se repitieron los 21 ensayos
urbanos de la batería base. Los 315 resúmenes del laboratorio se mantienen.
Las 33 ejecuciones urbanas de la revisión terminaron sin colisiones,
teletransportes ni conflictos peatonales registrados. Se contrastaron las
esperas y emisiones con los viajes de SUMO, manteniendo las entradas de los
ensayos repetidos. Los datos anteriores quedan en
`datos/procesados/historico_v1_6` para poder comparar versiones.

### Laboratorio

Espera vehicular media con 30 minutos de llegadas, 5 minutos de calentamiento
y diez semillas por control:

| Demanda | Fijo (s/veh.) | Adaptativo (s/veh.) |
| --- | ---: | ---: |
| Baja | 11,17 | 4,93 |
| Media | 12,90 | 8,10 |
| Alta | 21,45 | 157,18 |
| Desigual | 19,13 | 11,75 |
| Cambiante | 14,21 | 10,18 |

El adaptativo reduce la espera en cuatro escenarios y la aumenta con demanda
alta. Los cambios frecuentes consumen tiempo de amarillo y despeje y reducen
el tiempo útil de verde. Los resultados e intervalos de confianza están en
[comparacion.json](datos/procesados/comparacion.json).

### Salida escolar en los cruces urbanos

Flota mixta, velocidades variables, cámara emulada y V2I al 50 %. Cada control
se ejecuta con las semillas 101, 102 y 103, 30 minutos de llegadas, 5 minutos de
calentamiento y vaciado de la red. La tabla muestra las medias de las tres semillas:

| Lugar y control | Espera vehículo (s) | Espera peatón (s) | CO₂ (g/veh.) |
| --- | ---: | ---: | ---: |
| Lusitania · fijo | 283,63 | 107,69 | 197,65 |
| Lusitania · adaptativo | 445,25 | 68,60 | 229,24 |
| Santa Eulalia · fijo | 64,15 | 20,76 | 112,45 |
| Santa Eulalia · adaptativo | 59,24 | 16,91 | 111,50 |

En Lusitania el adaptativo reduce la espera peatonal un 36,30 %, pero aumenta
la vehicular un 56,99 % y el CO₂ un 15,98 %. En Santa Eulalia disminuyen las tres
medias: 7,66 %, 18,55 % y 0,84 %, respectivamente. Por tanto, la demanda alta
no es el único caso desfavorable: el reparto de movimientos y la atención
peatonal también influyen. El control adaptativo no garantiza una mejora ambiental.
Tres semillas permiten explorar estos casos, sin demostrar una mejora general.

![Resultados escolares de treinta minutos](documentacion/resultados/comparacion_30min.png)

La espera vehicular incluye detención y retraso de inserción. El CO₂ mide escape
dentro de la red, sin emisiones previas a la inserción, fabricación ni electricidad.
La demanda es sintética y no está calibrada con aforos locales; estas cifras
no son mediciones del tráfico real de Mérida.

Los ensayos cooperativos y mixtos cortos utilizan 180 s de llegadas y 30 s de
calentamiento y se analizan por separado. Sus cambios respecto a la versión
anterior están en [cambios_control.csv](datos/procesados/cambios_control.csv).
Las configuraciones y resultados largos están en
[movimientos_30min.json](datos/procesados/movimientos_30min.json) y sus medias en
[movimientos_30min.csv](datos/procesados/movimientos_30min.csv).

## Repetir los experimentos

Para repetir los 33 ensayos urbanos de la revisión y generar sus tablas y figuras:

```powershell
.\.venv\Scripts\python.exe simulacion/scripts/actualizar_estudio_movimientos.py --workers 3
.\.venv\Scripts\python.exe simulacion/scripts/analizar_movimientos.py
```

El primer script ejecuta los ensayos que faltan o valida los resultados existentes
para esa versión del motor. Si encuentra una ejecución incompleta, informa del
problema. Los datos brutos se guardan en `datos/resultados`.

Para reconstruir toda la batería base de 336 ejecuciones:

```powershell
.\.venv\Scripts\python.exe simulacion/scripts/reproducir_todo.py
```

Este proceso tarda más y actualiza los agregados. Para completar después los
resultados urbanos largos, ejecuta las dos órdenes anteriores. Los scripts
`verificar_*.py` necesitan las trazas generadas, no solo los resúmenes incluidos.

Como ejemplo breve, `examples/simulacion_breve.py` compara ambos controles en el
laboratorio durante 120 s. `examples/comparar_movimientos.py` ejecuta las doce
comparaciones escolares largas en una carpeta nueva. Ambos aceptan `--output`
para elegir dónde guardar los resultados sin sobrescribir una ejecución anterior.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest programa/tests
.\.venv\Scripts\python.exe -m ruff check programa simulacion documentacion/diagramas examples --select F
```

La última ejecución completa terminó con **128 pruebas aprobadas**. Incluye
controladores, API, almacenamiento, coherencia de resultados e integración con
SUMO. Los casos de integración llevan la marca `integration` de pytest.

Las pruebas del navegador necesitan Node.js, Edge y la aplicación en marcha.
Utiliza una carpeta de sesiones distinta para no mezclar pruebas y ensayos:

```powershell
$env:ITS_DATA_DIR = Join-Path $env:TEMP 'tfg-pruebas'
.\.venv\Scripts\python.exe programa/abrir.py --port 8795 --no-browser
```

En otra ventana de PowerShell, desde la misma carpeta del proyecto:

```powershell
npm install --prefix programa/tests
$env:ITS_BROWSER = 'msedge'
$env:ITS_URL = 'http://127.0.0.1:8795'
$env:ITS_SCREENSHOTS = Join-Path $env:TEMP 'tfg-capturas'
node programa/tests/browser_derechas.cjs
node programa/tests/browser_estudios.cjs
```

Usa en `ITS_URL` el puerto que indique el servidor. Estos guiones comprueban
las derechas independientes, las 40 configuraciones de estudio, la coincidencia
entre formulario y lote, las tablas, las incidencias y la vista móvil. El resto
de guiones `browser*.cjs` está en la misma carpeta y se ejecuta de forma secuencial.

## Carpetas

| Carpeta | Contenido |
| --- | --- |
| `programa/its` | Controladores, adquisición, simulación, API y SQLite |
| `programa/web` | Interfaz, dibujo y recursos visuales |
| `programa/tests` | Pruebas Python y de navegador |
| `simulacion` | Redes SUMO y scripts de experimentación |
| `datos/entrada` | Geometrías y contexto de los emplazamientos |
| `datos/procesados` | Resúmenes, agregados e histórico de resultados |
| `documentacion` | Capturas, diagramas editables, tablas y gráficos |
| `examples` | Ejemplos de ejecución desde consola |

## Licencia y recursos

El código y su documentación de software se distribuyen bajo [MIT](LICENSE).
Las dependencias mantienen sus propias licencias y se instalan mediante pip;
no se incluyen sus binarios. La imagen del acueducto es propia.

La cartografía y las redes derivadas corresponden a **© OpenStreetMap contributors**,
bajo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
Consulta las [condiciones de atribución de OpenStreetMap](https://www.openstreetmap.org/copyright).
Los extractos utilizados son el [entorno de Mérida](https://api.openstreetmap.org/api/0.6/map?bbox=-6.350,38.912,-6.328,38.927),
[Lusitania](https://api.openstreetmap.org/api/0.6/map?bbox=-6.344,38.906,-6.329,38.914)
y [Santa Eulalia](https://api.openstreetmap.org/api/0.6/map?bbox=-6.344,38.906,-6.329,38.916).
Sus geometrías están simplificadas y los parámetros operativos son supuestos.
Los datos de tráfico simulados no proceden de OpenStreetMap. El contexto municipal
de `contexto_merida.json` procede del INE y del PMUS y no genera las llegadas.

MIT no sustituye la licencia cartográfica ni concede una licencia general sobre
los recursos visuales. Las capturas muestran la aplicación; las imágenes de
informes de incidencias proceden de pruebas que simulan respuestas de fallo.
Los resultados experimentales se incluyen para consulta y reproducción.
