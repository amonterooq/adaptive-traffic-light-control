# Reproducción de experimentos y pruebas

> Edición para GitHub: ejecutar los comandos desde la raíz del repositorio,
> aunque la guía original la denomine `Proyecto`. Esta distribución incluye
> agregados, resúmenes y manifiestos, pero excluye las trazas masivas de
> `datos/resultados`. Las auditorías y los análisis que leen esas trazas
> requieren regenerarlas primero. Los recuentos históricos de pruebas de esta
> guía se distinguen de la [validación actual](../docs/VALIDACION.md).
> Si el lanzador `py -3.12` no detecta la instalación, utilizar `python`
> después de comprobar que corresponde a Python 3.12.

Todos los comandos se ejecutan en PowerShell desde la carpeta `Proyecto`.
La aplicación se puede usar con el lanzador; esta guía recoge las órdenes
para instalarla manualmente, repetir los experimentos y comprobar el código.

## 1. Preparar el entorno

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

El entorno solo se crea una vez. El archivo `requirements-lock.txt` fija las
versiones de las dependencias, incluido SUMO. Para abreviar los comandos
siguientes, definir esta variable en cada ventana de PowerShell:

```powershell
$pythonProyecto = '.\.venv\Scripts\python.exe'
```

Arranque normal y opciones del lanzador:

```powershell
& $pythonProyecto programa/abrir.py
& $pythonProyecto programa/abrir.py --port 8766
& $pythonProyecto programa/abrir.py --no-browser
```

Son tres alternativas. `--port` establece el primer puerto que se comprobará;
el lanzador busca entre ese puerto y los nueve siguientes. `--no-browser`
inicia el servidor sin abrir una pestaña. Si encuentra esta versión ya abierta,
reutiliza su dirección.

## 2. Repetir un estudio desde la aplicación

1. Abrir el selector de estudios, situado encima de las tarjetas de los cruces.
2. Elegir un estudio, una semilla y el control fijo.
3. Pulsar **Cargar opciones del estudio** e iniciar la simulación.
4. Esperar al estado **Completada**, incluido el vaciado de la red.
5. Elegir el control adaptativo para ese mismo estudio y semilla, cargar de nuevo
   las opciones e iniciar.
6. Comparar ambas filas del historial. Repetir las demás semillas del estudio
   para obtener su media.

El catálogo contiene 38 configuraciones. Los cinco estudios principales usan
las semillas 101–110; los ensayos de sensibilidad, cooperación y tráfico mixto
usan 101–103. Los estudios cooperativos comparan tres formas de detección
(sensores, V2I al 50 % y V2I al 100 %) con el control adaptativo.

El selector carga duración, peatones, sensores, vehículos y tiempos. Cambiar
alguno de esos parámetros produce otro experimento. La velocidad de reproducción
solo modifica el tiempo necesario para verlo: 5x y 100x dan el mismo resultado.
Dos minutos y treinta minutos de llegadas sí son experimentos diferentes.

## 3. Repetir las baterías desde la consola

Los resultados incluidos permiten consultar y auditar las comparaciones sin
volver a simular. Las órdenes de este apartado **sustituyen los archivos de
resultados correspondientes**. Para conservarlos, trabajar en una copia del
proyecto. El programa `experimentos.py` también admite `--output` para elegir
otra carpeta; los análisis incluidos leen las rutas predeterminadas.

### Batería completa

```powershell
& $pythonProyecto simulacion/scripts/reproducir_todo.py
```

Este script encadena las 336 ejecuciones, las comprobaciones de sus datos y
los análisis. Si falla una etapa, se detiene. Los lotes de consola no añaden
filas al historial de la aplicación.

| Grupo | Ejecuciones | Llegadas | Semillas |
| --- | ---: | ---: | --- |
| Comparación principal: cinco demandas y dos controles | 100 | 1800 s | 101–110 |
| Verde fijo de 20 s | 30 | 1800 s | 101–103 |
| Verde fijo de 40 s | 30 | 1800 s | 101–103 |
| Interrupción de observaciones | 6 | 1800 s | 101–103 |
| Cuatro perfiles peatonales y dos controles | 80 | 1800 s | 101–110 |
| Detección cooperativa | 18 | 180 s | 101–103 |
| Tráfico mixto y salida escolar | 72 | 180 s | 101–103 |

Los ensayos de 1800 s calculan las métricas sobre las llegadas programadas
entre los segundos 300 y 1800. Los ensayos de 180 s utilizan el intervalo
de 30 a 180 s. En ambos casos se espera a que terminen los recorridos.
Los resultados de las dos duraciones se analizan por separado.

### Ejecutar solo un grupo

Comparación principal:

```powershell
& $pythonProyecto simulacion/scripts/experimentos.py
```

Sensibilidad al verde fijo:

```powershell
& $pythonProyecto simulacion/scripts/experimentos.py --seeds 101 102 103 --green 20 --output datos/resultados/sensibilidad_g20
& $pythonProyecto simulacion/scripts/experimentos.py --seeds 101 102 103 --green 40 --output datos/resultados/sensibilidad_g40
```

Interrupción de observaciones entre los segundos 600 y 630:

```powershell
& $pythonProyecto simulacion/scripts/experimentos.py --seeds 101 102 103 --scenarios dinamico --blackout 600 630 --output datos/resultados/fallo_muestras
```

Perfiles peatonales:

```powershell
& $pythonProyecto simulacion/scripts/experimentos.py --scenarios medio --pedestrians sin ocasional frecuente lento --output datos/resultados/peatones
```

Detección cooperativa y tráfico mixto:

```powershell
& $pythonProyecto simulacion/scripts/experimentos_cooperativos.py
& $pythonProyecto simulacion/scripts/experimentos_mixtos.py
```

### Ensayos largos de la rotonda

```powershell
& $pythonProyecto simulacion/scripts/diagnostico_rotonda.py
```

Comprueba la salida escolar durante treinta minutos con dos controles y tres
semillas: seis ejecuciones. Se guardan en
`datos/diagnostico/rotonda_escolar_30min`. Este grupo comprueba que los viajes
terminan sin colisiones, teletransportes ni conflictos peatonales registrados;
se conserva separado de las 336 ejecuciones comparativas.

## 4. Comprobar los resultados guardados

Las auditorías recalculan métricas desde los viajes y las series, comprueban
las mismas demandas en las comparaciones y verifican las huellas del código
y los parámetros utilizados. No vuelven a ejecutar SUMO.

```powershell
& $pythonProyecto simulacion/scripts/verificar_entrega.py
& $pythonProyecto simulacion/scripts/verificar_cooperativo.py
& $pythonProyecto simulacion/scripts/verificar_mixto.py
```

La espera de los vehículos suma detención y retraso de inserción; la espera
peatonal se calcula aparte. El CO2 es la estimación de escape de SUMO durante
los recorridos dentro de la red. Se expresa en gramos por vehículo de la
cohorte y excluye electricidad, fabricación y emisiones antes de la inserción.
Una reducción de espera no implica necesariamente una reducción de CO2.

Cada ejecución conserva su configuración, demanda, flota, viajes, serie temporal
y resumen. Los archivos `manifest.json` identifican los parámetros y las fuentes
de cada batería. Por eso hay numerosos archivos en `datos/resultados`: se
generan al ejecutar los lotes.

## 5. Regenerar tablas, gráficos y diagramas

Después de repetir un grupo, actualizar sus agregados:

```powershell
& $pythonProyecto simulacion/scripts/analizar.py
& $pythonProyecto simulacion/scripts/analizar_peatones.py
& $pythonProyecto simulacion/scripts/analizar_cooperativo.py
& $pythonProyecto simulacion/scripts/analizar_mixto.py
```

Los agregados de `datos/procesados` alimentan **Comparar resultados**. Las tablas
y gráficos se escriben en `documentacion/resultados`.

Para reconstruir las redes geográficas y los diagramas editables:

```powershell
& $pythonProyecto simulacion/scripts/construir_cruces.py
& $pythonProyecto documentacion/diagramas/generar.py
& $pythonProyecto documentacion/diagramas/generar_camara.py
```

Las redes se generan en `simulacion/escenarios`. Los diagramas se guardan en
las subcarpetas `drawio`, `svg` y `pdf` de `documentacion/diagramas`.

## 6. Pruebas del programa

```powershell
& $pythonProyecto -m pytest programa/tests
& $pythonProyecto -m ruff check programa simulacion documentacion/diagramas --select F
```

Pytest recoge **111 casos a partir de 65 funciones de prueba**. La diferencia
son 46 casos adicionales obtenidos al repetir funciones con varias entradas.
Por ejemplo, una función valida ocho peticiones incorrectas y otra comprueba
la rotonda con dos controles y tres semillas.

De los 111 casos, 30 ejecutan SUMO y están marcados como `integration`. Los
otros 81 comprueban controladores, API, almacenamiento, geometría y arranque.
Se pueden ejecutar por separado:

```powershell
& $pythonProyecto -m pytest programa/tests -m "not integration"
& $pythonProyecto -m pytest programa/tests -m integration
```

Estas pruebas verifican el funcionamiento del programa. Las 336 simulaciones
del apartado 3 estudian los resultados de los controles bajo distintas demandas.

### Pruebas de navegador

Requieren Node.js, Microsoft Edge y un servidor activo. Los seis guiones
comprueban la interacción, las vistas, los informes y la carga de los estudios.
El informe incluido reúne 102 comprobaciones entre esos guiones.

Las pruebas crean sesiones. Para separarlas del historial habitual, cerrar
el servidor y abrir uno con otra carpeta de datos. En una ventana de PowerShell,
desde `Proyecto`:

```powershell
$pythonProyecto = '.\.venv\Scripts\python.exe'
$env:ITS_DATA_DIR = Join-Path $env:TEMP 'tfg-pruebas'
& $pythonProyecto programa/abrir.py --port 8795 --no-browser
```

Mantener esa ventana abierta. En una segunda ventana, también desde `Proyecto`:

```powershell
npm install --prefix programa/tests
$env:ITS_BROWSER = 'msedge'
$env:ITS_URL = 'http://127.0.0.1:8795'
$env:ITS_SCREENSHOTS = Join-Path $env:TEMP 'tfg-capturas'
node programa/tests/browser.cjs
node programa/tests/browser_lusitania.cjs
node programa/tests/browser_cooperative.cjs
node programa/tests/browser_mixto.cjs
node programa/tests/browser_estudios.cjs
node programa/tests/browser_interfaz.cjs
```

En `ITS_URL`, utilizar el puerto mostrado por el servidor si difiere de 8795.
Ejecutar los guiones uno detrás de otro. Las capturas y sus informes JSON
quedarán en la carpeta temporal indicada; sin `ITS_SCREENSHOTS` se escriben en
`documentacion/capturas`. Al terminar, cerrar el servidor con Ctrl+C.
