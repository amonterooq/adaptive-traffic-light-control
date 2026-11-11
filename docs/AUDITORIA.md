# Auditoría inicial y decisiones de preparación

Fecha: 11 de noviembre de 2026. Origen: carpeta `03_Proyecto` de la entrega
indicada por la autora; memoria de referencia: `01_Memoria/TFG_TELEMATICA_ANA_MONTERO_PRECIADO.pdf`.
La memoria se ha consultado, pero no se incorpora automáticamente a esta distribución.

## Diagnóstico anterior a la reorganización

El origen contiene 3.974 archivos y 247,6 MB. No contiene un repositorio `.git`.
El código Python y web coincide byte a byte con el de `trabajo_ana_montero_preciado/TRABAJO`.
La memoria tiene 147 páginas y describe 336 comparaciones: 246 de referencia,
18 cooperativas y 72 mixtas/escolares. Existen exactamente 336 `resumen.json`
en `datos/resultados`. Las copias anteriores de otros directorios no se usan.

| Responsabilidad | Implementación |
| --- | --- |
| Inicio | `Iniciar aplicación.cmd`, `programa/abrir.py`, `programa/iniciar.py` |
| API y ejecución en segundo plano | `programa/its/api.py`, FastAPI, hilo y bloqueo |
| Simulación | `programa/its/runner.py`, TraCI, procesos SUMO |
| Control | `controller.py`, `pedestrians.py`, `rotonda.py` |
| Detección emulada | `cooperative.py`, `camaras.py` |
| Configuración | `config.py`, `experimento.py`, `estudios.py`, JSON de escenarios |
| Redes y demanda | `network.py`, `locations.py`, `demand.py`, `trafico.py` |
| Interfaz | `programa/web`, JavaScript, HTML, CSS y canvas |
| Persistencia | `storage.py`, `schema.sql`, SQLite WAL y claves foráneas |
| Evaluación | `simulacion/scripts`, CSV/JSON, SciPy y Matplotlib |
| Pruebas | `programa/tests`, pytest y seis guiones Playwright |

La organización original ya separa responsabilidades. Se conserva para evitar
romper `ROOT`, rutas de recursos y huellas de los manifiestos. Se añaden `docs/`
y `examples/` para portfolio y reproducción breve. No se migra a un paquete
`src/` ni se añade Docker sin necesidad.

## Correspondencia con la memoria

La memoria y el catálogo de estudios coinciden en tres escenarios: laboratorio,
Lusitania y Santa Eulalia. Los 38 estudios cubren las 336 ejecuciones.
El control implementado es una regla local con estados y límites de tiempo;
no es aprendizaje automático ni coordinación de una red urbana.
Los detectores, cámara y V2I son emulados a partir de SUMO. LoRaWAN, NB-IoT,
5G/RedCap, ITS-G5 y C-V2X son tecnologías estudiadas, sin despliegue real.
Las métricas incluyen espera por detención y retraso de inserción. El CO₂ es
una estimación de escape del simulador, no una medición ambiental.

## Hallazgos por importancia

| Nivel | Hallazgo | Tratamiento |
| --- | --- | --- |
| Alto para publicación | Sesiones locales y resultados brutos no deben incorporarse por defecto | Exclusión por selección y `.gitignore` |
| Alto para publicación, resuelto | Procedencia de `acueducto-merida.png` no documentada | La autora confirmó que es propia y autorizó incluirla |
| Alto para publicación | No hay autorización para aplicar licencia de software | No se crea `LICENSE`; decisión pendiente |
| Medio | Pruebas e informes históricos no acreditan el estado actual | Se ejecuta una validación nueva y se identifica su alcance |
| Medio | El lanzador `py` del equipo no detecta Python aunque existe Python 3.12.9 | Se comprueba también la vía `python -m venv` |
| Medio | Las auditorías originales necesitan trazas excluidas | Se documenta regeneración; se conserva evidencia compacta |
| Medio | API sin autenticación, diseñada para localhost | Se mantiene la escucha en `127.0.0.1`; no se propone alojamiento público |
| Bajo | Falta una portada de repositorio y un ejemplo corto | README, diagrama Mermaid y ejemplo reproducible |

## Selección de contenido

Se conservan código, redes, cartografía con atribuciones, dependencias,
pruebas, agregados, diagramas y capturas. Se añaden los resúmenes de las 336
ejecuciones y sus manifiestos originales para mantener la trazabilidad.
Se excluyen sesiones, SQLite, resultados brutos, diagnósticos generados,
entornos, cachés e informes históricos de pruebas.
Documentos administrativos, solicitudes, firmas, memoria completa y ZIP de
entrega quedan fuera. Los originales no se eliminan ni se modifican.

Las listas exactas de publicación se generan al finalizar la validación.
