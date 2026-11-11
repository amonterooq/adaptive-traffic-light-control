# Material para CV, LinkedIn e entrevistas

Borradores basados en la implementación y evaluación del TFG. El repositorio
ya está disponible como [repositorio público](https://github.com/amonterooq/adaptive-traffic-light-control),
con licencia MIT para el código propio. El enlace puede compartirse en el CV,
la sección Proyectos y la publicación de LinkedIn.

## CV

**TFG · Sistema ITS de control semafórico adaptativo** — Universidad de Extremadura.
Desarrollo e integración de un prototipo en Python con SUMO/TraCI, API FastAPI,
interfaz web y persistencia SQLite. Evaluación de control fijo y adaptativo en
336 simulaciones con vehículos, peatones y detección V2I emulada, analizando
esperas y emisiones de escape estimadas bajo demanda sintética.

## LinkedIn · Proyectos

**Arquitectura y simulación de un sistema ITS de control semafórico adaptativo**

Trabajo Fin de Grado en Ingeniería Telemática en Telecomunicación. Diseñé un
prototipo que conecta simulación microscópica, adquisición de observaciones,
control semafórico y supervisión web mediante Python, SUMO, TraCI, FastAPI y
SQLite. Incluye un cruce de laboratorio y dos escenarios de Mérida, peatones,
tráfico mixto y comunicaciones V2I emuladas.

La evaluación comprende 336 ejecuciones. El análisis muestra mejoras en
determinadas demandas y también resultados desfavorables con demanda alta y
compromisos entre esperas peatonales y vehiculares. La demanda es sintética y
el prototipo no constituye un sistema validado para regular tráfico real.

## Publicación de LinkedIn · borrador para después de publicar

He preparado mi TFG de Ingeniería Telemática como proyecto de portfolio:
un sistema de simulación y control semafórico adaptativo con Python, SUMO,
TraCI, FastAPI y SQLite.

El trabajo conecta varias partes de un sistema ITS: adquisición de información,
comunicación entre procesos, decisiones de control, almacenamiento y supervisión.
La interfaz permite observar vehículos y peatones y comparar estrategias con
la misma configuración y semilla.

Una de las conclusiones más útiles llegó al analizar 336 ejecuciones: adaptar
el semáforo no mejora siempre el resultado. Con demanda alta, la estrategia
evaluada incrementó la espera vehicular; atender antes a peatones también puede
aumentar la espera de los vehículos. Documentar estos compromisos fue una parte
central de la evaluación.

El proyecto incluye instrucciones de reproducción, pruebas y una explicación
de sus límites. Los escenarios y las comunicaciones V2I son simulados, sin
validación de campo.

Repositorio: https://github.com/amonterooq/adaptive-traffic-light-control

#IngenieríaTelemática #Python #SUMO #ITS #Simulación #TFG

## Technical summary in English

Developed an academic intelligent transportation systems prototype integrating
Python, SUMO microscopic traffic simulation, TraCI over TCP, a FastAPI backend,
a web interface and SQLite session storage. The system supports fixed-time and
adaptive signal control, pedestrian phases, mixed traffic and emulated V2I sensing.

The evaluation comprises 336 comparative runs using synthetic demand across a
laboratory network and two Mérida locations. Results show benefits under several
demand conditions, degradation under high demand, and trade-offs between pedestrian
and vehicle waiting times. The project demonstrates systems integration,
interprocess communication and reproducible experimental evaluation; it is not
a field-validated traffic control product.

## Competencias que demostrar en entrevistas

- Integración de sistemas: separar simulación, adquisición, control y supervisión.
- Comunicación entre procesos: TraCI/TCP y API HTTP/JSON; límites de cada enlace.
- Python: máquinas de estados, validación de entradas, procesos e hilos.
- Persistencia: SQLite, transacciones, claves foráneas, WAL y recuperación de sesiones.
- Evaluación: semillas, comparaciones pareadas, calentamiento y vaciado de red.
- Calidad: pruebas unitarias, integración con SUMO y validación de API.
- Comunicación técnica: explicar limitaciones y resultados negativos con evidencia.

## Decisiones y resultados que conviene saber explicar

1. Por qué SUMO y TraCI permiten separar el simulador de la lógica de control.
2. Por qué hay una ejecución activa y cómo se sincroniza su consulta desde la web.
3. Cómo los tiempos mínimo/máximo, la histéresis y el despeje condicionan el control.
4. Qué sucede al caducar las observaciones y por qué hay respaldo temporizado.
5. Cómo se evita confundir el fin de llegadas con el fin de todos los viajes.
6. Por qué la espera incluye retraso de inserción además de detención.
7. Por qué se comparan la misma demanda y semilla y se separan baterías largas y cortas.
8. Cómo explicar 21,45 → 157,18 s/vehículo con demanda alta sin ocultar el deterioro.
9. Cómo interpretar 37,45 → 17,11 s/peatón junto a 26,30 → 67,21 s/vehículo.
10. Qué significa CO₂ de escape estimado y qué emisiones quedan fuera.
11. Qué está implementado y qué se estudió: no hay LoRaWAN, NB-IoT, 5G/RedCap,
    ITS-G5 o C-V2X desplegados ni procesamiento de vídeo real.
12. Qué datos y validaciones faltarían para trasladar el modelo a tráfico real.
